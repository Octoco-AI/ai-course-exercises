#!/usr/bin/env python3
"""Aggregate a long-format metrics CSV before anyone (human or agent) reads it.

Input is a CSV export with the columns ``timestamp,host,metric,value`` —
the shape you get from a Zabbix history/trend export, a Grafana "inspect →
data" download, or ``sample-data/metrics-db-sessions.csv`` in this kit.
Timestamps are ISO 8601 (``2026-10-14T13:05:00Z``) or Unix seconds.

Output is small on purpose: one row per series per bucket, plus a per-series
summary (overall min/avg/max, slope per day, and the first bucket that left
the baseline). Use ``--backtest`` to count how often a proposed threshold
would have fired over the same window — the noise estimate an alarm proposal
needs before anyone reviews it.

Standard library only. Read-only: it never writes anything except stdout.

Examples:
    aggregate_metrics.py metrics.csv --bucket 1d
    aggregate_metrics.py metrics.csv --bucket 1h --metric 'pgsql.*' --since 2026-10-13
    aggregate_metrics.py metrics.csv --summary-only
    aggregate_metrics.py metrics.csv --backtest 'pgsql.connections.idle_in_transaction>20' --for 30m
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

DURATION_RE = re.compile(r"^(\d+)([smhd])$")
BACKTEST_RE = re.compile(r"^\s*([^<>=!\s]+)\s*(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)\s*$")
UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
DEFAULT_MAX_ROWS = 200


def parse_duration(text: str) -> int:
    match = DURATION_RE.match(text.strip())
    if not match:
        raise argparse.ArgumentTypeError(f"not a duration like 5m, 1h, 1d: {text!r}")
    return int(match.group(1)) * UNIT_SECONDS[match.group(2)]


def parse_time(text: str) -> float:
    text = text.strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Series:
    host: str
    metric: str
    points: list[tuple[float, float]] = field(default_factory=list)


def load(path: str, metric_glob: str, host_glob: str, since: float | None, until: float | None) -> dict[tuple[str, str], Series]:
    series: dict[tuple[str, str], Series] = {}
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"timestamp", "host", "metric", "value"} - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"error: CSV is missing column(s): {', '.join(sorted(missing))}")
        for line_no, row in enumerate(reader, start=2):
            if not fnmatch.fnmatch(row["metric"], metric_glob) or not fnmatch.fnmatch(row["host"], host_glob):
                continue
            try:
                ts = parse_time(row["timestamp"])
                value = float(row["value"])
            except ValueError as exc:
                raise SystemExit(f"error: line {line_no}: {exc}") from exc
            if since is not None and ts < since:
                continue
            if until is not None and ts > until:
                continue
            key = (row["host"], row["metric"])
            series.setdefault(key, Series(*key)).points.append((ts, value))
    for item in series.values():
        item.points.sort()
    return series


def bucketise(points: list[tuple[float, float]], bucket: int) -> list[dict]:
    groups: dict[int, list[float]] = defaultdict(list)
    for ts, value in points:
        groups[int(ts // bucket) * bucket].append(value)
    rows = []
    for start in sorted(groups):
        values = groups[start]
        rows.append({
            "bucket_start": iso(start),
            "count": len(values),
            "min": min(values),
            "avg": round(statistics.fmean(values), 2),
            "max": max(values),
            "last": values[-1],
        })
    return rows


def slope_per_day(points: list[tuple[float, float]]) -> float:
    """Least-squares slope, in value units per day."""
    if len(points) < 2:
        return 0.0
    xs = [ts / 86400 for ts, _ in points]
    ys = [value for _, value in points]
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom


def first_departure(rows: list[dict], baseline_buckets: int) -> str | None:
    """First bucket whose max exceeds baseline mean + 3 sigma (sigma floored at 1)."""
    if len(rows) <= baseline_buckets:
        return None
    baseline = [row["avg"] for row in rows[:baseline_buckets]]
    mean = statistics.fmean(baseline)
    sigma = statistics.pstdev(baseline) if len(baseline) > 1 else 0.0
    limit = mean + 3 * max(sigma, 1.0)
    for row in rows[baseline_buckets:]:
        if row["max"] > limit:
            return row["bucket_start"]
    return None


def summarise(item: Series, rows: list[dict], baseline_buckets: int) -> dict:
    values = [value for _, value in item.points]
    return {
        "host": item.host,
        "metric": item.metric,
        "points": len(values),
        "from": iso(item.points[0][0]),
        "to": iso(item.points[-1][0]),
        "min": min(values),
        "avg": round(statistics.fmean(values), 2),
        "max": max(values),
        "slope_per_day": round(slope_per_day(item.points), 3),
        "first_departure": first_departure(rows, baseline_buckets),
    }


def backtest(item: Series, op: str, threshold: float, hold: int) -> list[dict]:
    """Episodes where the condition held continuously for at least ``hold`` seconds."""
    compare = {">": lambda v: v > threshold, ">=": lambda v: v >= threshold,
               "<": lambda v: v < threshold, "<=": lambda v: v <= threshold}[op]
    episodes, start, last_true = [], None, None
    for ts, value in item.points:
        if compare(value):
            start = ts if start is None else start
            last_true = ts
        else:
            if start is not None and last_true - start >= hold:
                episodes.append({"fired_at": iso(start + hold), "condition_from": iso(start), "condition_to": iso(last_true)})
            start = last_true = None
    if start is not None and last_true - start >= hold:
        episodes.append({"fired_at": iso(start + hold), "condition_from": iso(start), "condition_to": iso(last_true)})
    return episodes


def markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "_(no rows)_\n"
    headers = list(rows[0])
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join("" if row[h] is None else str(row[h]) for h in headers) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("csv", help="long-format CSV: timestamp,host,metric,value")
    parser.add_argument("--bucket", type=parse_duration, default=parse_duration("1h"), help="bucket size, e.g. 5m, 1h, 1d (default 1h)")
    parser.add_argument("--metric", default="*", help="glob on the metric name (default *)")
    parser.add_argument("--host", default="*", help="glob on the host name (default *)")
    parser.add_argument("--since", type=parse_time, help="ISO 8601 or Unix seconds")
    parser.add_argument("--until", type=parse_time, help="ISO 8601 or Unix seconds")
    parser.add_argument("--baseline-buckets", type=int, default=24, help="leading buckets that define 'normal' (default 24)")
    parser.add_argument("--summary-only", action="store_true", help="print only the per-series summary")
    parser.add_argument("--backtest", help="condition to replay, e.g. 'pgsql.connections.total>270'")
    parser.add_argument("--for", dest="hold", type=parse_duration, default=0, help="how long the condition must hold, e.g. 30m")
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS, help=f"refuse to print more bucket rows than this (default {DEFAULT_MAX_ROWS})")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    args = parser.parse_args(argv)

    if args.backtest:
        match = BACKTEST_RE.match(args.backtest)
        if not match:
            parser.error("--backtest must look like METRIC>VALUE (operators: > >= < <=)")
        metric, op, threshold = match.group(1), match.group(2), float(match.group(3))
        data = load(args.csv, metric, args.host, args.since, args.until)
        if not data:
            print(f"error: no series match metric {metric!r}", file=sys.stderr)
            return 1
        result = {f"{host} {name}": backtest(item, op, threshold, args.hold) for (host, name), item in sorted(data.items())}
        if args.json:
            print(json.dumps({"condition": args.backtest, "for_seconds": args.hold, "episodes": result}, indent=2))
        else:
            for name, episodes in result.items():
                print(f"## Backtest `{args.backtest}` for {args.hold}s — {name}: {len(episodes)} episode(s)\n")
                print(markdown_table(episodes))
        return 0

    data = load(args.csv, args.metric, args.host, args.since, args.until)
    if not data:
        print("error: no series match the filters", file=sys.stderr)
        return 1

    summaries, buckets = [], {}
    for key, item in sorted(data.items()):
        rows = bucketise(item.points, args.bucket)
        buckets[key] = rows
        summaries.append(summarise(item, rows, args.baseline_buckets))

    total_rows = sum(len(rows) for rows in buckets.values())
    too_many = not args.summary_only and total_rows > args.max_rows
    if too_many:
        print(
            f"warning: {total_rows} bucket rows exceeds --max-rows {args.max_rows}; printing the summary only. "
            "Use a larger --bucket, a narrower --since/--until, or a tighter --metric/--host filter.",
            file=sys.stderr,
        )

    if args.json:
        payload = {"bucket_seconds": args.bucket, "summary": summaries}
        if not args.summary_only and not too_many:
            payload["buckets"] = {f"{h} {m}": rows for (h, m), rows in buckets.items()}
        print(json.dumps(payload, indent=2))
        return 0

    print(f"## Summary (bucket {args.bucket}s, baseline = first {args.baseline_buckets} buckets)\n")
    print(markdown_table(summaries))
    if not args.summary_only and not too_many:
        for (host, metric), rows in buckets.items():
            print(f"## {metric} on {host}\n")
            print(markdown_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
