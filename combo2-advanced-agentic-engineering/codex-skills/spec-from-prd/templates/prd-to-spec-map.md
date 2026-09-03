# PRD → spec map

The mapping Phase 2 works through, worked here against the sample PRD
(`../../../claude-code-skills/example-prd.md`, "AI-Assisted PR Review Triage") so the mapping is concrete rather
than abstract. Use `prd-intake-checklist.md` for the *reading* discipline; use this for the
*writing* discipline — where each thing actually lands in `spec-template.md`.

| PRD section | Spec destination | Worked example |
|---|---|---|
| `## Problem`, `## Who It Affects` | Context note above the requirements — motivation, not a requirement | "Senior reviewers spend time on trivial PRs; the tool exists to redirect their attention, not replace them." |
| `## What Changes` | One-line spec summary | "An AI reviewer triages every PR on the monorepo and ranks issues by how much attention they need." |
| `## Goals` | Candidate performance thresholds — **ask for the number** | Goal: "reviewers trust the tool's flags over the first month." Ask: "what would tell us trust is building rather than eroding — a false-positive rate ceiling? a percentage of flags reviewers act on?" |
| `## Scope` → In scope | Boundary of the requirement set | Triage runs on PR open/update, on the core monorepo only — nothing outside that boundary gets a requirement without asking first |
| `## Scope` → Out of scope | Spec `## Out of scope`, verbatim, with the PRD's stated reason | "Auto-approving or auto-merging any PR — a human always makes the merge decision" carries straight across |
| `## Requirements` | Functional requirements, strength verb intact, scenarios become acceptance-criteria lines | "The system SHALL rank every issue it surfaces on a PR from most to least in need of reviewer attention" carries across unchanged — it already passes the durability test |
| `## Requirements` (durability failure) | Restated in observable terms, flagged in `## Traceability` | "Writes a row to `pull_request_reviews`" → "A record of every triage comment posted exists and is retrievable by PR" |
| `## What's There Today` | Checked against the repo, never promoted to a requirement | "Monorepo is on GitHub Enterprise Server" → check `git remote -v`; mark verified / contradicted / could not verify |
| `## Open Questions` | Carried into Phase 3 verbatim, unanswered | "What counts as a high-severity issue?" is not resolved here — it goes straight into Clarify |

## What Phase 2 adds that the PRD has no section for

These are the four extras from `spec-template.md`. None of them come from the PRD — they
come from asking the user, and every one gets marked `[NEW — not in PRD]`:

- **Performance thresholds** — e.g. what false-positive rate on flagged issues is
  acceptable before reviewers start ignoring the tool.
- **Graceful degradation** — e.g. what the triage comment says if the AI reviewer times out
  or the provider is down; does the PR just get no comment, or a placeholder saying "not
  reviewed"?
- **Learning expectations** — e.g. does the tool learn from which flags a reviewer actually
  acts on, and if so per-reviewer, per-team, or across the whole org?
- **Failure modes** — e.g. false positives (noise reviewers start skipping), false negatives
  (a real issue ranked "safe to skim"), bias (certain file types always flagged), adversarial
  inputs (a contributor structuring a diff to dodge the ranking).

## `## Traceability` — the section neither PRD nor `spec-driven` has

One row per spec item. This is what makes the handoff auditable rather than a one-way
translation the PM can't check:

| Spec item | PRD source | Status |
|---|---|---|
| "Automatic triage on PR open" | PRD Requirements | Carried |
| "A record of every triage comment posted exists…" | PRD Requirements ("Writes a row to `pull_request_reviews`") | Carried, restated for durability |
| Performance threshold — false-positive rate | — | `[NEW — not in PRD]` |
| "GitHub Enterprise Server" (What's There Today) | PRD What's There Today | Contradicted — repo remote is `github.com` |

## `## Questions for the PRD author` — the round trip back

Anything that surfaces while specifying that the PM should weigh in on, not just what
Clarify surfaces from the checklist. Two kinds show up here in practice:

- A requirement that only became ambiguous once you tried to make it testable (the PRD read
  fine; writing a scenario for it revealed a gap).
- A plan-stage decision (Phase 4) that constrains or contradicts a requirement — this section
  is where that goes instead of quietly overriding the PRD.
