# PRD: AI-Assisted PR Review Triage

## Problem
Senior engineers on the monorepo team spend a large share of review time on pull requests
that turn out to have no substantive issues, while the PRs that actually need close
attention aren't distinguishable from the queue until someone opens them. As the team has
grown from 6 to 14 engineers, the review queue backs up and merges are delayed for days even
when nothing is architecturally wrong. Reviewers say the problem isn't reviewing itself —
it's not knowing where to spend their attention first.

## Who It Affects
The five engineers on the core monorepo who hold merge rights, directly — their review time
is the scarce resource this feature protects. Indirectly, every contributor waiting on a
review: median time-to-first-review has crept from 4 hours to a day and a half over the last
two quarters as the team has grown.

## What Changes
An AI reviewer runs automatically on every pull request opened or updated against the
monorepo's default branch. It posts a single triage comment that ranks the issues it found
by how much attention a senior reviewer should give them, and labels the PR overall as
either "safe to skim" or "read closely." It doesn't replace the human review — it tells the
human where to look first.

## Goals
- Reduce median reviewer time-to-first-comment on PRs that genuinely need close attention, without slowing down the ones that don't.
- Let a senior reviewer turn around more PRs per day without feeling like review quality dropped.
- Cut the number of "rubber-stamp" approvals on PRs that later needed a follow-up fix.
- Build reviewer trust in the tool's flags over the first month, rather than have them ignored after the first few false alarms.

## Scope
**In scope:**
- A triage comment posted automatically when a PR is opened or updated, on the core monorepo only.
- Ranking of the issues found, not just a flat list.
- A single skim/read-closely recommendation per PR.

**Out of scope:**
- Auto-approving or auto-merging any PR — a human always makes the merge decision.
- Reviewing PRs on any repo other than the core monorepo (other repos are a possible v2).
- Inline suggested-fix diffs — the tool flags issues, it doesn't patch them.

## Requirements

### Automatic triage on PR open
The system SHALL post a triage comment on every pull request opened or updated against the monorepo's default branch.

#### Scenario: PR opened with changes
- GIVEN a pull request is opened against the monorepo's default branch
- WHEN the PR contains at least one file change
- THEN a triage comment appears on the PR before the reviewer is assigned

### Ranked issue list
The system SHALL rank every issue it surfaces on a PR from most to least in need of reviewer attention.

#### Scenario: Multiple issues found
- GIVEN the AI reviewer finds three issues on a PR
- WHEN it posts the triage comment
- THEN the three issues appear in descending order of how much attention each needs, with the reasoning for the order stated inline

### Skim-vs-read-closely recommendation
The system SHALL label each PR with exactly one of two recommendations: "safe to skim" or "read closely."

#### Scenario: No issues found
- GIVEN the AI reviewer finds no issues worth surfacing
- WHEN it posts the triage comment
- THEN the PR is labelled "safe to skim" and the comment says so in one line

### Every triage run is recorded
The system SHALL write a row to the `pull_request_reviews` table for every triage comment it posts, containing the PR id, the issues found, and their ranks.

#### Scenario: Triage comment posted
- GIVEN the AI reviewer posts a triage comment
- WHEN the comment is created
- THEN a corresponding row exists in `pull_request_reviews`

### Reviewers are notified on high-attention PRs
The system SHALL POST to the `#pr-reviews` Slack incoming webhook whenever a PR is labelled "read closely."

#### Scenario: High-attention PR posted
- GIVEN a PR is labelled "read closely"
- WHEN the triage comment is posted
- THEN a message is sent to the `#pr-reviews` Slack webhook with a link to the PR

## What's There Today
Unverified, check against the system before relying on it.
- Per the #eng-platform channel history, the monorepo's CI already runs a lightweight lint-only bot that comments on style violations — this triage feature would be a second bot commenting on the same PRs.
- Per the Q2 reviewer survey, senior engineers say they spend "most" of their review time on PRs under 50 lines that turn out to be trivial.
- Per the infra wiki, the monorepo is hosted on GitHub Enterprise Server (self-hosted), not github.com.

## Open Questions
- What counts as a "high-severity" issue versus a routine one — is that decided per-repo, per-team, or is there one bar for the whole monorepo?
- Does the AI reviewer see the full diff only, or can it read context from files the PR doesn't touch?
- Who owns tuning the tool once reviewers start ignoring some of its flags — the platform team, or each squad?
