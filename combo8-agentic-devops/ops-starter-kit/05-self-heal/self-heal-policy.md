# Self-heal policy — <ALARM_CLASS>

> **Design only.** This is the written policy that has to exist, reviewed and merged, **before** any agent works at the **act** rung for this alarm class. Writing one is how a team discovers whether the class is safe to automate at all. Often it isn't, and that is a fine outcome.

Policy id: <SH-NNN>    Owner: <TEAM>    Approved by: <NAME_OR_ROLE>, <YYYY-MM-DD>    Review by: <YYYY-MM-DD>    Status: draft / approved / suspended / retired

## The shape every policy follows

```
alarm fires
   │
   ▼
1. Deterministic classification ── no match ──▶ 2. Cheap-model classification ── low confidence / "other" ──▶ page a human
   │ match                                          │ match ≥ threshold
   ▼                                                ▼
3. Allowed action: the agent opens an MR in the IaC/config repo (never touches the system)
   │
   ▼
4. Human gate: named approver reviews and merges ── rejects ──▶ close MR, record why
   │ merges
   ▼
5. Normal deploy pipeline applies it (the agent has no deploy rights)
   │
   ▼
6. Verify: did the alarm clear? ── no ──▶ rollback and page a human
```

The agent's write access is to **one repository, by MR**, on the paths this policy names. It never has write access to production.

## 1. Classification — deterministic first

Rules a script can evaluate without a model: trigger name or tag, host group, metric values, file paths and sizes, the last deploy. Write them as a table so they can be tested.

| Rule | Condition | Class |
|---|---|---|
| D1 | | |

Anything no rule matches goes to step 2, never straight to an action.

## 2. Classification — cheap model second

Only for what the rules did not match. The model **chooses among the classes above, or answers `other`**. It never invents a new action.

- Model: <SMALL_FAST_MODEL> — the cheapest that passes the eval set
- Input: the aggregated evidence the deterministic step gathered (no raw logs)
- Output: `{ "class": "<one of the classes> | other", "confidence": 0–1, "evidence": ["…"] }`
- Threshold: below <0.8> confidence, or `other` → page a human with the evidence
- Eval set: <N> labelled past alarms in `<PATH>`. Re-run whenever the prompt, the model or the classes change

## 3. Allowed action

| Class | Allowed action (always an MR) | Repo and paths the MR may touch | Never |
|---|---|---|---|

## 4. Human gate

- Approver: <ROLE_OR_ROTA> — a CODEOWNERS entry on the paths above, not "anyone with merge rights"
- Response expectation: <e.g. within 30 minutes in working hours; out of hours the alarm pages as normal>
- The MR description must carry: the alarm, the classification and its evidence, the policy id, the expected effect and the rollback

## 5. Rollback

<How to undo the change: normally "revert the MR; the deploy pipeline re-applies the previous state". Name anything a revert does not undo.>

## 6. Kill switch

- **Switch:** <one place, e.g. CI/CD variable `SELF_HEAL_<CLASS>_ENABLED=false`, or a flag file in the config repo that the pipeline checks before invoking the agent>
- **Who may pull it:** anyone on the team, no approval needed
- **Effect:** the agent stops opening MRs for this class. Alarms page humans as before
- **Also:** revoking the agent's repo token stops every class at once. Record where that token lives in the agent inventory

## 7. Limits

- At most <1> open MR per class per host. Further alarms add a comment to the open MR, not a new one
- At most <N> MRs per day across the class. Beyond that, suspend and page
- Demotion: <2> reverted or rejected MRs in <30> days → status `suspended`, back to the recommend rung, review at the next team retro

## 8. Records

- Agent inventory entry: `05-self-heal/agent-inventory-entry.md` → <link>
- Destructive actions this policy relies on **not** taking: <list ids from `destructive-actions.md`>
- Metrics reviewed monthly: MRs opened, merged unchanged, merged with edits, rejected, reverted; time from alarm to merge

---

# Worked example — disk filling on a log volume (SH-001, synthetic)

Hosts: application VMs `app01`–`app06.example.internal`, volume `/var/log`, logrotate managed by Ansible in the config repo `ops/config` (role `logrotate`). Everything here is invented.

**Why this class is a good first candidate:** it is frequent and well understood, the fix is a config change with a clean revert, and the dangerous shortcut (deleting files) is easy to name and forbid.

### 1. Deterministic classification

A read-only script (`du` on a fixed list of paths, `find -newer`, the last Ansible run time) runs when the Zabbix trigger `vfs.fs.size[/var/log,pused] > 85` fires.

| Rule | Condition | Class |
|---|---|---|
| D1 | > 60 % of used space is files matching `*.log.[0-9]*` (rotated, uncompressed) and `compress` is absent from that app's logrotate config | `rotation-not-compressing` |
| D2 | > 60 % of used space is rotated files, and their count exceeds the configured `rotate` by more than 2 | `rotation-count-not-enforced` |
| D3 | One active `*.log` file is > 50 % of used space and grew > 1 GiB in the last hour | `runaway-logger` |
| D4 | Used space grew > 10 % in 1 hour and no single file explains it | `unknown-growth` |
| — | Volume is not `/var/log`, or host not in group `app-vms` | out of scope → page |

### 2. Cheap-model classification

Only `unknown-growth` and unmatched cases reach the model. It gets the top-20 directory sizes and growth rates and chooses among D1–D3 or `other`. In practice most cases land on `other` and page a human. That is the expected behaviour, not a failure.

### 3. Allowed action

| Class | Allowed action | Repo and paths | Never |
|---|---|---|---|
| `rotation-not-compressing` | MR adding `compress` and `delaycompress` to that app's logrotate vars | `ops/config`: `inventories/*/group_vars/app_vms/logrotate.yml` only | delete, truncate or move any file; run Ansible; ssh to a host |
| `rotation-count-not-enforced` | MR lowering `rotate` to the documented standard (<N>) and adding `maxsize <SIZE>` | same file | same |
| `runaway-logger` | **No MR.** Page the owning app team with the evidence. The fix is the app's log level or a bug, which is not a logrotate change | — | change the app's log level; restart the app; truncate the file |
| `unknown-growth`, `other` | No MR. Page on-call | — | — |

### 4. Human gate

Approver: on-call platform engineer via CODEOWNERS on `group_vars/app_vms/logrotate.yml`. If the disk is above 95 %, the alarm also pages as HIGH, independent of the MR. A human can free space by hand (runbook DISK-02) while the MR waits.

### 5. Rollback

Revert the MR. The next scheduled Ansible run re-applies the previous logrotate config. Compressed files stay compressed, which is harmless.

### 6. Kill switch

CI/CD variable `SELF_HEAL_LOGROTATE_ENABLED=false` on the alarm-handler pipeline. The agent's project access token for `ops/config` (Developer role, `api` scope, expiry 90 days) is listed in the agent inventory. Revoking it stops all self-heal MRs.

### 7. Limits

One open MR per host group. At most 3 MRs a day. Two reverts in 30 days → suspended.

### 8. Records

Inventory entry: `self-heal-logrotate`. Relies on not taking DA-01 (delete files), DA-07 (run configuration management) or DA-08 (shell on a host).
