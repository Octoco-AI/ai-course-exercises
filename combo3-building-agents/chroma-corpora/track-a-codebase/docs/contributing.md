# Contributing

Short version: fork, branch, PR, wait for CI, merge with reviewer's approval. No squash; we keep commit history clean per commit. We review everything.

## Setup

```
uv venv
uv pip install -e '.[dev]'
pre-commit install
```

`pre-commit` runs ruff and mypy on staged files before every commit.

## Running the service locally

```
docker compose -f ops/compose-local.yml up -d   # postgres + redis
uv run uvicorn todomagic.api:app --reload
```

The local stack seeds a `demo@todomagic.test` user with password `demopass`.

## Running tests

```
pytest tests/unit           # fast
pytest tests/integration    # needs postgres; testcontainers manages it
pytest tests/e2e            # full stack; slowest
pytest                      # all of the above
```

CI runs all three. A PR cannot merge with any red.

## Coding conventions

- Ruff config in `pyproject.toml`. We use the default rules plus a few additions; don't disable rules in a PR without justification.
- Mypy in strict mode. Explicit types on all public function signatures.
- Imports: stdlib, third-party, first-party. Alphabetised within each group. `isort` is the source of truth.
- Docstrings on public functions and services. Keep them short; the signature is the spec.
- No emojis in source code or commit messages.

## Commit messages

Conventional commits. Prefixes we use:

- `feat:` — new feature.
- `fix:` — bug fix.
- `refactor:` — no behavioural change.
- `test:` — tests only.
- `docs:` — docs only.
- `chore:` — CI, deps, tooling.

One logical change per commit. PRs with 40 commits get asked to rebase.

## Review

At least one reviewer. Reviewer checks:

1. Does the code do what the PR says it does?
2. Are the tests complete? Is there a test for the thing that was broken?
3. Any obvious performance issues? N+1 queries are the usual suspect.
4. Does the changelog entry exist and make sense?
5. Is the migration (if any) backward-compatible?

Requesting changes in review is normal. Don't take it personally; we review PRs, not people.

## What NOT to bring in

- **Dependencies we don't already have.** Adding a dependency requires a separate PR with justification in the description. No "I needed this utility function so I added this 50MB library."
- **New infrastructure.** Anything that changes `fly.toml`, `compose-local.yml`, or the CI config needs a design note in `docs/adrs/`.
- **Clever one-liners.** We prefer dull code that a new team member can read.
- **AI-generated code that hasn't been read.** If Claude wrote it, YOU read it line by line before submitting. Reviewers will ask if they suspect a drive-by paste.

## What to expect timeline-wise

- First reviewer response: within 1 working day.
- Small PRs: merged within 2 days of opening.
- Larger PRs (feature work): 3–5 days of back-and-forth is normal.
- Urgent fixes: flag in the PR title with `[hotfix]` and ping in Slack.
