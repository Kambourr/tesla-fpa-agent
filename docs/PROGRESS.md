# Progress

## Current status

- **Current milestone:** M1 setup and data ingest. `M1-T1` and `M1-T4` are on `main`. `M1-T6` and `M1-T7` are done on branch `task/M1-T6-M1-T7-sec-quarters` and are not on `main` yet.
- **Tasks done:** 5 of 53 (9%).
- **What's next:** Merge the M1-T6 / M1-T7 pull request. `M1-T5` can be claimed now that `M1-T4` is on `main`. These can still be claimed in parallel, each on its own branch, with the claim pushed before any other work: `M1-T2`, `M1-T3`, `M1-T5`, `M2-T1`, `M3-T1`, and `M5-T1`. `M1-T8` still waits on `M1-T2` and `M1-T3` as well as this branch.
- **Open blockers:**
  - (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
  - (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
  - (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- **How to run the project right now:** Install [uv](https://docs.astral.sh/uv/), then from the repo root run `uv sync` and `uv run pytest`. That installs Python 3.11 and pytest. There is no `python -m agent run` yet. Deliveries are the committed CSV. Nothing fetches them on a test run.

## 2026-11-04 12:58 (America/Los_Angeles) — Cursor agent

**Task(s):** M1-T6 (done), M1-T7 (done)
**What changed:**
- Added `agent/sec.py`. It downloads Tesla companyfacts and the submissions filing index, sends `User-Agent` from `SEC_USER_AGENT`, and fails closed when that value is empty. Bodies are cached under `data/cache/`. A second read of the same URL does not call the network. Network calls are spaced at least 100ms apart.
- Added `agent/quarters.py`. Q4 is the annual figure minus Q1–Q3. Year-to-date cash flow becomes single quarters (Q1 unchanged, Q2 minus Q1, Q3 minus Q2). Free cash flow is quarterly CFO minus quarterly capex.
- Added fixture JSON under `tests/fixtures/sec/` and `tests/test_sec_client.py` plus `tests/test_quarters.py`. The SEC tests do not call data.sec.gov.
- Recorded the client and the quarter formulas in `docs/DECISIONS.md`. `data/manual/deliveries.csv` is unchanged.
**Current state:** No ingest command yet. The SEC client and the quarter functions are importable. Local `uv run pytest`: 36 passed. Ruff check and format check passed.
**Next step:** Merge the M1-T6 / M1-T7 pull request. Then claim `M1-T2`, `M1-T3`, or `M1-T5` (M1-T4 is already on `main`). `M1-T8` should call `SecClient.companyfacts`, `SecClient.filing_index`, `derive_q4`, and `decumulate_ytd`.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv` in this task's follow-ups. Income-statement lines are already single quarters; do not pass them through `decumulate_ytd`. Capex passed to `free_cash_flow` is the positive purchases amount. The filing index URL is the submissions JSON, not the HTML browse page. `SEC_USER_AGENT` is read only via `get_secret_value()` inside `SecClient.from_settings`. Refer to it by name. The commit named below is the client and the quarter math. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** 0856da8031fe686c3c58951c4fd61bd377aa473d on task/M1-T6-M1-T7-sec-quarters

## 2026-11-04 12:52 (America/Los_Angeles) — Cursor agent

**Task(s):** M1-T4 (done)
**What changed:**
- Filled `data/manual/deliveries.csv` with 20 contiguous quarters, `2021-Q4` through `2026-Q3`. Columns are `quarter`, `production_total`, `deliveries_total`, `release_date`, and `source_url`.
- Totals are the Total row of each quarter's first investor-relations production-and-deliveries release, checked against that day's Form 8-K Exhibit 99.1. `source_url` is the IR press-release page. `release_date` is the press-release date.
- Added `tests/test_deliveries.py`. It checks the columns, the contiguous window, the first-release totals, the release date and source URL on every row, and that `agent/` does not reference the IR pages.
- Recorded the window, the table-versus-headline choice, and the URL slugs in `docs/DECISIONS.md`.
**Current state:** Manual deliveries only. No ingest command and no fetch of the source pages. `M1-T2` and `M1-T3` were left unclaimed because they are not dependencies of this task. Local `uv run pytest`: 22 passed. `uv run ruff check .` and `uv run ruff format --check .` passed.
**Next step:** Merge the M1-T4 pull request into `main`. Then `M1-T5` can be claimed: add `scripts/check_deliveries` and the no-network structural checks. Do not start `M1-T5` until this CSV is on `main`.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
**Notes for the next agent:** Do not edit `docs/BRIEF.md`. The private-repo override is in `docs/DECISIONS.md`. Refer to secrets only by env var name. The CSV uses `YYYY-Qn` and the exact table totals, not the rounded lead sentence and not a later shareholder update. 2025 Q2, Q3, and Q4 source slugs omit "and" before "deployments"; the quarters around them include it. Full-year rows for 2022 through 2025 sum to the annual Total row on that year's Q4 release. `data/manual/.gitkeep` is still there next to the CSV. The commit named below is the transcription. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** f28adc81e25a3e983b129faadd5140545e2d3ed7 on task/M1-T4-transcribe-deliveries

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
