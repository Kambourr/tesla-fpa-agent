# Progress

## Current status

- **Current milestone:** M1 setup and data ingest. Scaffolding is on branch `task/M1-T1-repo-scaffolding` (pull request #2) and is not on `main` yet.
- **Tasks done:** 2 of 53 (4%).
- **What's next:** Merge pull request #2. After `M1-T1` is on `main`, claim these in parallel, each on its own branch, and push the claim before any other work: `M1-T2`, `M1-T3`, `M1-T4`, `M1-T6`, `M1-T7`, `M2-T1`, `M3-T1`, and `M5-T1`. `M1-T5` still waits on `M1-T4`.
- **Open blockers:**
  - (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
  - (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
  - (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- **How to run the project right now:** Install [uv](https://docs.astral.sh/uv/), then from the repo root run `uv sync` and `uv run pytest`. That installs Python 3.11 and pytest. There is no `python -m agent run` yet.

## 2026-11-04 12:44 (America/Los_Angeles) — Cursor agent

**Task(s):** M1-T1 (done)
**What changed:**
- Added `pyproject.toml`, `uv.lock`, and `.python-version` (3.11). `uv sync` installs CPython 3.11 and pytest.
- Added `.gitignore`, which ignores `.env` and `data/cache/` and keeps `.env.example` and `data/manual/`. Added `.env.example` with empty `OPENAI_API_KEY`, `OPENAI_MODEL`, and `SEC_USER_AGENT`, and `PUBLISH_FORWARD_FORECAST=false`. Added `data/manual/.gitkeep`.
- Added the `agent` package (`agent/__init__.py`, `agent/settings.py`) and `tests/test_scaffold.py` plus `tests/test_settings.py`.
- Added `.github/workflows/test.yml`. It runs ruff and pytest on pull requests and on pushes to `main`. It does not receive secrets and does not change repository settings.
- Recorded the toolchain and layout in `docs/DECISIONS.md`. The README stub is unchanged.
**Current state:** Scaffold only. No ingest, model, site, or pipeline command. Local `uv run pytest`: 14 passed. GitHub Actions run 41909378571 on pull request #2, commit `6eec3c6`, job `pytest`: success, 14 passed in 2.35s.
**Next step:** Merge pull request #2 into `main`. Then start the parallel claims listed above. For each one, set the status to `in progress (agent name, date)` and push that commit before adding files.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
**Notes for the next agent:** Do not edit `docs/BRIEF.md`. The private-repo override is in `docs/DECISIONS.md`. Refer to secrets only by env var name. `uv sync` is the install command; there is no separate requirements file. Add a new dependency with `uv add` in the same commit as the code that imports it. `OPENAI_MODEL` is empty on purpose; choose the structured-output model in the narration task after checking OpenAI's docs. The README stub stays until M6. The commit named below is the scaffold. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** 6eec3c6878ebf6a3b2f87d4ddf728ab57bd9b5a4 on task/M1-T1-repo-scaffolding

## 2026-11-04 12:35 (America/Los_Angeles) — Cursor agent

**Task(s):** M0-T1 (done)
**What changed:**
- Added `docs/BRIEF.md`, a byte-for-byte copy of the build brief.
- Added `docs/PLAN.md` with milestones M0–M6 and 53 tasks.
- Added `docs/PROGRESS.md` and `docs/DECISIONS.md` (private-repo deviation and the docs layout).
- Added `AGENTS.md`, `CLAUDE.md`, and `.cursor/rules/handoff.mdc` with the section 11 instruction.
**Current state:** Handoff docs only. No package, no tests, no site. The one-line `README.md` stub is unchanged. `pytest` is not set up, so there is no pass/fail count.
**Next step:** After the pull request `M0-T1: handoff docs and build plan` merges, check out `main`, pull, create `task/M1-T1-repo-scaffolding`, set `M1-T1` to `in progress (agent name, date)` in `docs/PLAN.md`, and push that claim before scaffolding `pyproject.toml`, the lockfile, `.gitignore`, `.env.example`, or `.github/workflows/test.yml`.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
**Notes for the next agent:** Do not edit `docs/BRIEF.md`. The private-repo override is in `docs/DECISIONS.md`. Do not start product code on `task/M0-T1-handoff-docs`. Refer to secrets only by env var name. `AGENTS.md` and `CLAUDE.md` are the same file contents; keep them that way. The commit named below introduced the handoff files. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and `docs/PROGRESS.md`.
**Last commit:** d0b5373c1000411fc88ad7d362bfca2ed6a31d0c on task/M0-T1-handoff-docs
