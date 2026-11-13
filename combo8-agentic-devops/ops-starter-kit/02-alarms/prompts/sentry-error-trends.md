# Prompt — Sentry error trends per release, never event dumps

Use with the read-only `sentry` MCP server (`--skills inspect`, read-scoped token; see `01-access/`). Replace every `<PLACEHOLDER>`.

---

I am investigating **<INCIDENT_OR_ALARM_CLASS>** for Sentry project **<ORG>/<PROJECT>**, environment **<ENVIRONMENT>**. Impact began at **<IMPACT_START_UTC>**. The releases in play are **<PREVIOUS_RELEASE>** and **<LIVE_RELEASE>** (or: find them).

Rules for every query in this session:

- Read issues, counts and tag distributions. Never page through an issue's events.
- Every search names the environment and a time range.
- Never resolve, ignore, assign, comment on or merge an issue, and never touch an alert rule.
- Never print user identifiers, emails, IPs, headers or request bodies.

Steps:

1. **Releases and when they went live.** `find_releases` for the project: version, date created, first event. Which release was live at impact, and which one before it?

2. **New issues since the live release.** `search_issues` with `is:unresolved firstRelease:<LIVE_RELEASE> environment:<ENVIRONMENT>`, sorted by frequency. For each: title, culprit, events, users, first seen.

3. **The lead-up.** For the top three issues, `get_issue_details`: the daily event counts for the <LOOKBACK, default 14 days> before impact. When did each first appear, and what was its rate per day? A slowly climbing warning-level issue is the preventative signal; the storm at impact is the symptom.

4. **Blast radius.** `get_issue_tag_values` for `release`, `server_name` (or `transaction`) and `url` on each: one release? one host? one endpoint?

5. **Was there a rule for it?** `find_alert_rules`: which rule would have fired for these issues, at what threshold, and did it?

6. **Warnings that stopped.** Search for issues whose `lastSeen` is just before the live release, especially warning-level ones (pool leak warnings, deprecations). An issue that stops at a deploy, because a detector was switched off, is evidence too.

Hand back: a table of issue, level, first seen, rate per day before impact, release, and whether an alert rule covered it. Then the searches you ran, so I can rerun them in the Issues view.
