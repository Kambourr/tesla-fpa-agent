# Progress

## Current status

- **Current milestone:** M0 handoff, on branch `task/M0-T1-handoff-docs`. M1 has not started.
- **Tasks done:** 1 of 53 (2%).
- **What's next:** After this pull request merges, claim `M1-T1` on a new branch `task/M1-T1-repo-scaffolding`. Set that task to `in progress` and push before adding any package files.
- **Open blockers:**
  - (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
  - (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
  - (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- **How to run the project right now:** There is no pipeline yet. Product code starts at `M1-T1`. Read `docs/PLAN.md` before writing any.

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
