"""Tests for the m62 alarm kit: the aggregator and the trigger templates.

Run from the kit root:  python3 -m pytest 02-alarms/tests
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
TOOL = KIT / "02-alarms" / "tools" / "aggregate_metrics.py"
SAMPLE = KIT / "sample-data" / "metrics-db-sessions.csv"
TEMPLATES = KIT / "02-alarms" / "templates"

spec = importlib.util.spec_from_file_location("aggregate_metrics", TOOL)
agg = importlib.util.module_from_spec(spec)
sys.modules["aggregate_metrics"] = agg
spec.loader.exec_module(agg)


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, check=False)


@pytest.fixture
def tiny_csv(tmp_path: Path) -> Path:
    path = tmp_path / "m.csv"
    rows = ["timestamp,host,metric,value"]
    # 6 hours of 30-minute samples; value rises 0..11
    for i in range(12):
        hour, minute = divmod(i * 30, 60)
        rows.append(f"2026-01-01T{hour:02d}:{minute:02d}:00Z,h1.example.internal,load,{i}")
    rows.append("2026-01-01T00:00:00Z,h2.example.internal,other,5")
    path.write_text("\n".join(rows) + "\n")
    return path


def test_bucketise_hourly(tiny_csv: Path):
    data = agg.load(str(tiny_csv), "load", "*", None, None)
    rows = agg.bucketise(data[("h1.example.internal", "load")].points, 3600)
    assert len(rows) == 6
    assert rows[0] == {"bucket_start": "2026-01-01T00:00:00Z", "count": 2, "min": 0.0, "avg": 0.5, "max": 1.0, "last": 1.0}


def test_slope_per_day_positive(tiny_csv: Path):
    data = agg.load(str(tiny_csv), "load", "*", None, None)
    # one unit per 30 minutes = 48 per day
    assert agg.slope_per_day(data[("h1.example.internal", "load")].points) == pytest.approx(48.0)


def test_filters_and_missing_columns(tiny_csv: Path, tmp_path: Path):
    assert set(agg.load(str(tiny_csv), "*", "h2*", None, None)) == {("h2.example.internal", "other")}
    bad = tmp_path / "bad.csv"
    bad.write_text("time,value\n1,2\n")
    result = run(str(bad))
    assert result.returncode != 0 and "missing column" in result.stderr


def test_backtest_requires_sustained_condition(tiny_csv: Path):
    data = agg.load(str(tiny_csv), "load", "*", None, None)
    series = data[("h1.example.internal", "load")]
    # value > 8 holds for samples 9, 10, 11 -> 04:30 to 05:30, i.e. 60 minutes
    assert len(agg.backtest(series, ">", 8, 3600)) == 1
    assert agg.backtest(series, ">", 8, 3601) == []
    episode = agg.backtest(series, ">", 8, 1800)[0]
    assert episode["condition_from"] == "2026-01-01T04:30:00Z"
    assert episode["fired_at"] == "2026-01-01T05:00:00Z"


def test_max_rows_guard_prints_summary_only():
    result = run(str(SAMPLE), "--bucket", "1h")
    assert result.returncode == 0
    assert "exceeds --max-rows" in result.stderr
    assert "## Summary" in result.stdout
    assert "## pgsql" not in result.stdout  # no per-bucket tables


def test_sample_story_slow_signal_leads_by_days():
    result = run(str(SAMPLE), "--backtest", "pgsql.connections.idle_in_transaction>20", "--for", "30m", "--json")
    episodes = json.loads(result.stdout)["episodes"]["db01.example.internal pgsql.connections.idle_in_transaction"]
    assert episodes[0]["fired_at"].startswith("2026-10-07")


def test_sample_story_existing_alarm_fires_late():
    result = run(str(SAMPLE), "--backtest", "pgsql.connections.total>=285", "--for", "30m", "--json")
    episodes = json.loads(result.stdout)["episodes"]["db01.example.internal pgsql.connections.total"]
    assert [e["fired_at"] for e in episodes] == ["2026-10-14T13:45:00Z"]


def test_sample_retransmit_red_herring_is_on_another_day():
    result = run(str(SAMPLE), "--metric", "net.tcp.*", "--summary-only", "--json")
    summary = json.loads(result.stdout)["summary"][0]
    assert summary["first_departure"].startswith("2026-10-12")


def test_bad_backtest_expression_rejected():
    result = run(str(SAMPLE), "--backtest", "no operator here")
    assert result.returncode == 2


# --- templates -------------------------------------------------------------

yaml = pytest.importorskip("yaml")


def test_zabbix_template_structure():
    doc = yaml.safe_load((TEMPLATES / "zabbix-template-db-sessions.yaml").read_text())
    template = doc["zabbix_export"]["templates"][0]
    name = template["template"]
    uuids, macros_used = [], set()
    for item in template["items"]:
        uuids.append(item["uuid"])
        assert item["type"] == "CALCULATED" and item["params"].startswith(("last(//", "max(//"))
        for trigger in item["triggers"]:
            uuids.append(trigger["uuid"])
            assert trigger["priority"] in {"INFO", "WARNING", "AVERAGE", "HIGH", "DISASTER"}
            # every function in the expression points at this template and this item
            refs = re.findall(r"\(/([^/]+)/([^,)]+)", trigger["expression"])
            assert refs and all(ref == (name, item["key"]) for ref in refs), trigger["expression"]
            tags = {t["tag"]: t["value"] for t in trigger["tags"]}
            assert tags["audience"] in {"human", "agent"}
            macros_used |= set(re.findall(r"\{\$[A-Z0-9_.]+\}", trigger["expression"] + trigger["name"]))
    uuids += [g["uuid"] for g in doc["zabbix_export"]["template_groups"]] + [template["uuid"]]
    assert all(re.fullmatch(r"[0-9a-f]{32}", u) for u in uuids)
    assert len(uuids) == len(set(uuids))
    defined = {m["macro"] for m in template["macros"]}
    assert macros_used <= defined, macros_used - defined


def test_ansible_task_imports_the_sibling_template():
    tasks = yaml.safe_load((TEMPLATES / "ansible-zabbix-template.yml").read_text())
    module = tasks[0]["community.zabbix.zabbix_template"]
    assert "zabbix-template-db-sessions.yaml" in module["template_yaml"]
    assert (TEMPLATES / "zabbix-template-db-sessions.yaml").exists()


def test_grafana_rules_shape():
    doc = json.loads((TEMPLATES / "grafana-alert-rule-db-sessions.json").read_text())
    assert doc["apiVersion"] == 1
    rules = doc["groups"][0]["rules"]
    assert len({r["uid"] for r in rules}) == len(rules)
    for rule in rules:
        assert len(rule["uid"]) <= 40
        ref_ids = {d["refId"] for d in rule["data"]}
        assert rule["condition"] in ref_ids
        for node in rule["data"]:
            if node["datasourceUid"] == "__expr__":
                assert node["model"]["expression"] in ref_ids
        assert rule["labels"]["audience"] in {"human", "agent"}
