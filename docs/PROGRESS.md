# Progress

## Current status

- **Current milestone:** M7 (redesign for a first-time reader), added at Jacob's request after the original plan was complete. Live site: https://kambourr.github.io/tesla-fpa-agent/
- **Tasks done:** 55 of 55 (100%).
- **What's next:** Run "Refresh data" once so the published `dashboard.json` carries the new `sources` counts (the build chain shows plain-text fallbacks until then), then refresh the README screenshot.
- **Open blockers:**
  - (a) Pages is enabled and deploys from GitHub Actions (Jacob's go-ahead, 2026-11-04). The repository itself is still private; making it public is Jacob's call (the README and the site are written for a public audience).
  - (b) Resolved 2026-11-04: Jacob added `OPENAI_API_KEY` and `SEC_USER_AGENT` as GitHub Actions secrets. They reach workflows only. This cloud environment has its own `SEC_USER_AGENT` variable and no OpenAI key, by design: live narration runs in Actions.
  - (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
  - (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403 (Akamai Access Denied in headless Chrome too). No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
  - (e) Resolved 2026-11-04: Jacob set Pages Source to GitHub Actions and asked to check that it works, which is his go-ahead to merge PR #20 (`deploy.yml`). Every push to `main` now deploys the site to `https://kambourr.github.io/tesla-fpa-agent/`.
  - (f) Resolved 2026-11-04: `data.sec.gov` and `www.sec.gov` are allowed in this cloud environment, and SEC answers with the configured `SEC_USER_AGENT`.
  - (g) A stray branch `tmp-m3-base` was pushed by mistake while preparing branches on 2026-11-05. This environment cannot delete remote branches (proxy 403). It is unused; please delete it on GitHub (Branches page).
- **How to run the project right now:** Install [uv](https://docs.astral.sh/uv/) and Node 22. `uv sync`, copy `.env.example` to `.env` and fill in `OPENAI_API_KEY` and `SEC_USER_AGENT`, then `uv run python -m agent run` (about seven minutes, about $0.03 when every narrative is regenerated). Tests: `uv run pytest`, and in `site/` `npm ci`, `npm test`, `npm run build`. In GitHub: Actions, "Refresh data", Run workflow; the site redeploys after it commits.

## 2026-11-05 (America/Los_Angeles) — Claude Code

**Task(s):** M7-T1 (done).
**What changed:** Fresh redesign of the dashboard (Jacob's request: a recruiter should understand what went into the project faster), built with the `frontend-design` skill committed in `.claude/skills/frontend-design/`.
- First screen: a small headline, then the first sentence of the latest memo at display size in Newsreader with the code's tick after each figure (they stamp on in reading order; static under reduced motion), a caption naming the filing and the overall check ("337 of 337 tie to the filings"), and "What went into it": five numbered steps with live counts and the stack, linking to the author.
- `dashboard.json` gains `sources` (fact rows, filings, delivery quarters, first and last filing date) from `agent/publish.py`; schema, TypeScript types, and tests updated.
- New palette and fonts (values in `docs/DECISIONS.md`), proportional figures throughout, sections separated by space instead of rules, the run summary moved below model accuracy, favicon recoloured.
**Checks:** `uv run pytest` 335 passed; ruff clean; site tests 142 passed; `tsc` clean; build OK. Playwright: no console errors, `scrollWidth` 375 at 375px, dark mode and reduced motion checked by screenshot. Lighthouse 12.2.1 (local preview): accessibility 100, best practices 100, SEO 100 on mobile and desktop; desktop performance 100; mobile performance 80 to 89 with total blocking time 340 to 650 ms. The unchanged `main` build measured 80 and 91 in the same session, so the mobile spread is this container's CPU, not the redesign.
**Current state:** `main` has the redesign once this task's PR merges (880909404cbb8ca261239b024c2a80f994880fb1); Pages redeploys on merge.
**Next step:** Run "Refresh data" (force off) so `sources` is published; update `docs/images/dashboard.png`.
**Blockers / questions for Jacob:** None new. The earlier list (deliveries spot-check, profile links, employer policy, repo visibility, stray branch) still stands.

## 2026-11-05 06:12 (America/Los_Angeles) — Claude Code

**Task(s):** M6-T6 (done). **The project is complete.**
**What changed:** Final handoff. Section 10 of the brief, item by item:
- [x] `python -m agent run` works from a clean checkout with only the two secrets set and finishes in about seven minutes (GitHub Actions "Refresh data" run 42037719383: 422.6 s, estimated $0.0335).
- [x] All tests pass in CI (pytest and the site tests on every pull request; `uv run pytest`: 334 passed).
- [x] The site is live on GitHub Pages, works at 375px with no horizontal scroll, and shows the latest quarter (Q3 2026) by default. Lighthouse: performance 99 mobile / 100 desktop, accessibility 100.
- [x] Every AI-written figure has a tick mark; flagged and unsupported figures stay visible (the 2026-11-05 run verified 337 of 337).
- [x] No API key in the repo, the built site, or the logs (M6-T5 scan of all history and `site/dist`; Actions logs show secrets as ***).
- [x] The README reads as a case study and includes the disclaimer.
- [x] No Tesla logo, brand colors, or non-public information (M6-T4).
- [x] Forward forecast is off (`PUBLISH_FORWARD_FORECAST=false`; no forward quarter in `dashboard.json`).
- [x] `docs/PLAN.md` shows every task done; this is the final entry.
**Current state:** `main` is green; Pages is live; a refresh is one click (Actions, "Refresh data", Run workflow; about $0.03 when every narrative is regenerated, near zero when nothing changed).
**Next step:** None for an agent. **For Jacob:**
1. Spot-check `data/manual/deliveries.csv` against Tesla's releases. From this environment every investor-relations page returned HTTP 403, so run `uv run python scripts/check_deliveries --fetch` from your own network.
2. Fill in the GitHub, LinkedIn, and résumé URLs in `site/src/config.ts` (`profileLinks`; they show "Not filled in yet").
3. Check your employer's policy before sharing; the site and README say "independent analysis" and "not investment advice".
4. Decide whether to make the repository public (the site is already public through Pages).
5. Delete the stray branch `tmp-m3-base` on GitHub (Branches page); this environment cannot delete remote branches. The other merged `task/*` branches can be deleted too.
6. Optional: your commits carry your personal email as the author address; GitHub's no-reply email keeps it out of future commits if the repo goes public.
7. When Tesla files its next 10-Q, add that quarter's delivery release to `deliveries.csv` and run "Refresh data".
**Blockers / questions for Jacob:** Only the list above.
**Notes for the next agent:** Read the brief and `docs/DECISIONS.md` first. Haiku subagents wrote most task code under Claude Code's review; every decision that deviates from the brief is logged in `docs/DECISIONS.md`.
**Last commit:** ebe5fb8b3e51c943740fa75962f5809570cc97b2 on task/M6-T6-closeout

## 2026-11-05 06:07 (America/Los_Angeles) — Claude Code

**Task(s):** M6-T5 (done)
**What changed:** No code. The final secret scan, run on `main` at c7c4467 after every other task merged:
- `git log -p --all` over 282 commits on every branch: no match for `sk-[A-Za-z0-9_-]{20,}`, `ghp_`, `github_pat_`, `x-access-token:`, or a private-key header (only the scanner's own regular expressions). No filled `OPENAI_API_KEY=` or `SEC_USER_AGENT=` assignment beyond test placeholders (`from-env-file`).
- The SEC contact string (normalized) appears in no commit, in no file under `site/dist` or `site/public`, and not in `data/narrative_cache.json`.
- `site/dist` after a fresh build: no key pattern, no `OPENAI_API_KEY` or `SEC_USER_AGENT` text. No `.env` is tracked.
- GitHub Actions logs show both secrets as `***`.
**Current state:** Clean. Nothing to rotate.
**Next step:** M6-T6 closeout.
**Blockers / questions for Jacob:** none from the scan.
**Notes for the next agent:** `tests/test_scaffold.py` repeats the key-pattern scan on every test run.
**Last commit:** c7c4467dc23a93fb97e658d6ce9d4f5e78776a60 on main (scanned)

## 2026-11-05 05:57 (America/Los_Angeles) — Claude Code

**Task(s):** M6-T1, M6-T2, M6-T3 (done)
**What changed:**
- `README.md` is the case study (written by Claude Code): the problem, the live link and a screenshot, the six pipeline steps, how accuracy is controlled (fact sheet, verifier, tick marks, the latest live run's 337 of 337 verified figures, backtest error 17.1% revenue / 20.6% gross profit / 101.0% operating income), a Mermaid architecture diagram, run-it-yourself with `.env`, one command, about seven minutes and about $0.03 per run, limitations, the disclaimer, and "Designed and built by Jacob Kambour." The screenshot and README ship in one branch, so M6-T2 is recorded with M6-T1.
- `docs/images/dashboard.png` (324 KB, 256 colors): the real page for Q3 2026 with the hero bridge, the 69-of-69 seal, the run summary, and the memo with a tick on every figure. No key or secret is visible.
- M6-T3, the clean-checkout run, ran in GitHub Actions ("Refresh data", run 42037719383): fresh checkout, empty database and SEC cache, only the `OPENAI_API_KEY` and `SEC_USER_AGENT` secrets. It finished in 422.6 s (ingest 2,495 facts; narration 12 calls, 136,980 input and 39,530 output tokens on gpt-6-luna, estimated $0.0335), with `PUBLISH_FORWARD_FORECAST=false` and no forward quarter published, and committed `dashboard.json` and `data/narrative_cache.json` (d14cfbc).
- Live-run fixes merged along the way: the SEC contact secret held a line break (`Invalid header value`), now collapsed to one line; the prompt now asks for readable figures ($28.05 billion, 21.1%) after the first run copied raw values; ticks now survive the model's sentence-number drift (PR #59).
**Current state:** `uv run pytest`: 334 passed; site tests and build pass. Pages is serving the refreshed data.
**Next step:** M6-T5 secret scan, then M6-T6 closeout.
**Blockers / questions for Jacob:** (a), (c), (d), and (g) as in the status block.
**Notes for the next agent:** A refresh is manual: Actions, "Refresh data", Run workflow. Use `force` only to regenerate every narrative (about $0.03).
**Last commit:** f0b8e4c3cd82343177af55c9e838e828cdc5e50d on task/M6-T1-readme

## 2026-11-05 05:39 (America/Los_Angeles) — Claude Code

**Task(s):** M6-T4 (done; Claude Code)
**What changed:** No code. Recorded the anti-goal sweep, run on `main`:
- Brand: `git ls-files` holds one image, `site/public/favicon.svg`, a green tick mark on paper; no Tesla logo, wordmark, product photo, or brand font (`grep -rniE "gotham|universal sans"` empty). The masthead text "Tesla FP&A Agent" is plain IBM Plex Sans, commented in `site/src/config.ts` as not a wordmark.
- Color: no red or near-red hex in `site/src` or `site/index.html`; the palette is the section 6 tokens only.
- Sources: every URL in `agent/`, `config/`, `scripts/`, and `data/manual/` is `https://data.sec.gov`, `https://www.sec.gov`, `https://ir.tesla.com` (the delivery releases), or an XBRL namespace. No other feed.
- No live chatbot: `grep -rniE "openai|api\.openai|sk-" site/src site/index.html` is empty; the built bundle contains no OpenAI client and no fetch to an API. The page reads the bundled `dashboard.json` only. The footer disclaimer is the exact required text.
**Current state:** `uv run pytest`: 334 passed; site tests and build pass.
**Next step:** README screenshot after the first live refresh, then the M6-T5 secret scan and closeout.
**Blockers / questions for Jacob:** (a), (c), (d), and (g) as in the status block.
**Notes for the next agent:** Re-run these greps if a new asset or source is added.
**Last commit:** 372bf6a38ecacfaff8580871b8e92910294dfaf8 on task/M6-T4-anti-goal-sweep

## 2026-11-05 05:17 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T15 (done; Claude Code)
**What changed:**
- `site/src/main.tsx` imports the committed `site/public/data/dashboard.json` at build time (Vite emits it as `JSON.parse`), so the page renders complete on first paint. Loading it after first render inserted every section above the methods section: cumulative layout shift 0.45 to 0.49, which held Lighthouse performance at 78 to 80. `App` still accepts a fetched file (tests cover that path).
- Lighthouse 12.6.0 on the production build (local preview, all sections): mobile performance 99, accessibility 100, best practices 100, SEO 100 (CLS 0.002, LCP 1.7 s); desktop performance 100, accessibility 100, best practices 100, SEO 100 (CLS 0, LCP 0.4 s).
- Keyboard: a Playwright pass tabbed through all 19 focusable elements (quarter picker, theme toggle, scenario buttons, chart quarter buttons, links) in light and dark; every one shows the focus ring. Tick focus is covered by their component tests (no memo is published yet).
- Width: at 375px the document is exactly 375px wide (no horizontal page scroll); the bridge and the tables scroll inside their own boxes with the first column pinned.
- Dark mode contrast: every token pair was measured at M5-T1 and passes WCAG AA (table in `docs/DECISIONS.md`).
**Current state:** `uv run pytest`: 332 passed; site tests and build pass.
**Next step:** Merge this PR; README and launch tasks.
**Blockers / questions for Jacob:** (a), (c), (d), and (g) as in the status block.
**Notes for the next agent:** The site rebuilds whenever `dashboard.json` changes (deploy runs on push and after "Refresh data"), so the bundled data is always the committed file.
**Last commit:** 45b2f83c5a0dbb63e082d178d283f1de2fd8f2d6 on task/M5-T15-accessibility

## 2026-11-05 05:09 (America/Los_Angeles) — Claude Code

**Task(s):** M4-T2 (done)
**What changed:**
- Added `agent/run.py` and `python -m agent run` (Haiku subagent, reviewed by Claude Code): ingest, load, forecast (model + variance), explain (narration with one re-ask), verify, publish, each timed into the published run metadata with the model, tokens (re-asks included), estimated cost, and data-as-of date. A bridge that cannot be built stops the run instead of publishing a gap. A `Makefile` adds `make run` and `make test`.
- `agent/publish.py` fills each quarter's `memo` and the latest quarter's `qa` from the narrative and verification tables, with each claim's status, expected value, and source. A narrative without a verification row stops publishing with "run python -m agent verify", so unchecked figures are never shown as checked.
- Added `agent/narrative_store.py`: verified narratives are exported to `data/narrative_cache.json` after verify and imported before explain, so a fresh database (every GitHub Actions run) reuses already-verified text. Decision logged in `docs/DECISIONS.md`.
- Added `tests/test_run.py` (13) and `tests/test_narrative_store.py` (10).
**Current state:** `uv run pytest`: 332 passed; site tests and build pass. Fixture-mode run: six stages timed, 12 memos plus 10 answers, dashboard validates; a second run with the same cache file makes zero model calls. No live OpenAI call has run yet.
**Next step:** Jacob runs "Refresh data" once in the Actions tab.
**Blockers / questions for Jacob:** (a), (c), (d), and (g) as in the status block.
**Notes for the next agent:** A fixture run must pass `--database` and `--output` so fixture numbers never overwrite `data/fpa.duckdb` or the committed `dashboard.json`. When a new latest quarter arrives, the previous latest is drafted again as a memo only (one extra call).
**Last commit:** 8da111ffe5dcae4e350fddbcb9648c0ea6730dcf on task/M4-T2-run-command

## 2026-11-05 01:44 (America/Los_Angeles) — Claude Code

**Task(s):** site fixes from a visual check (no plan task)
**What changed:**
- `site/src/sections/AgentRunFormat.ts`: the run details wait for a recorded model. The publish step records its own start time and duration, so the live page read "Total run time: under 1 second".
- `site/src/styles/global.css`: `.visually-hidden` is pinned to `top: 0; left: 0`. Hidden favorable/unfavorable words inside the scrolling forecast table sat outside the scroll box and widened the page to 611px at a 375px viewport; with the fix it is 375px.
**Current state:** `uv run pytest`: 309 passed; site tests and build pass. Checked in a local preview with Playwright at 1280px and 375px: no horizontal page scroll, no console errors.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block. Also: a stray branch `tmp-m3-base` was pushed by mistake while preparing branches; this environment cannot delete remote branches (proxy 403). It is unused; please delete it on GitHub.
**Notes for the next agent:** Wrap screen-reader-only tables in an element with `overflow: hidden` (as `.hero-table-clip` does); tables do not shrink to the 1px `.visually-hidden` box.
**Last commit:** 153d2c139d6e08edcbe2a3fab9dc9c6e8e4e7c64 on fix/run-details-need-model

## 2026-11-05 01:44 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T11 (done)
**What changed:**
- `site/src/sections/AskSection.tsx` (+ format, CSS, tests), coded by a Haiku subagent and reviewed by Claude Code: the ten pre-answered questions as an expandable list (buttons with `aria-expanded`), each answer through `NarrativeText` with its ticks and a "Source:" link from the first sourced claim. Questions 7 and 8 carry "Uses all 12 quarters". When an earlier quarter is selected, a note says the answers cover the latest quarter only, with a button that switches to it. Before narration runs it says the answers appear after the next full pipeline run.
**Current state:** `uv run pytest`: 309 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** Answers come from `dashboard.qa`, which `M4-T2` fills. Visitors never call the model.
**Last commit:** df6407001ce19246f0867bb49dac2a010c9b8335 on task/M5-T11-ask

## 2026-11-05 01:44 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T7 (done)
**What changed:**
- `site/src/sections/MemoSection.tsx` (+ CSS, tests), coded by a Haiku subagent and reviewed by Claude Code: the memo on a plain paper sheet (surface, 1px rule, no shadow) with a To/Re/Prepared-by header, the body through `NarrativeText` so every figure carries its tick, the tickmark legend beside it on wide screens, and a count line ("18 of 19 figures tie to the filings. 1 flagged."). Before narration runs it says the memo appears after the next full pipeline run.
**Current state:** `uv run pytest`: 309 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** The memo text comes from `quarter.memo`, which `M4-T2` fills from the narrative and verification tables.
**Last commit:** 5c5119f0ac1d3afe08eb1cde1d99dbcda7f24043 on task/M5-T7-memo

## 2026-11-05 01:44 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T5 (done)
**What changed:**
- `site/src/sections/VerificationSeal.tsx` (+ format, CSS, tests), coded by a Haiku subagent and reviewed by Claude Code, rendered under the hero bridge: "{verified} of {total} figures in the commentary tie to the filings", summing the memo and, for the Q&A quarter, the answers; flagged and unsupported counts are appended and never hidden, with an amber flag. Up to five tick glyphs appear after the bridge finishes drawing (at once under reduced motion). "See how the figures are checked" links to the methods section (`#method-title`). Before any commentary exists it says so.
**Current state:** `uv run pytest`: 309 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** The seal sits in the hero's bridge branch, so it does not show when a quarter has no bridge.
**Last commit:** f2f5f8ad0f5ae1bfd335773b70fa41b536ee1acf on task/M5-T5-seal

## 2026-11-05 01:44 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T9 (done)
**What changed:**
- `scripts/make_scenario_fixture.py` builds `site/src/data/scenarioParity.fixture.json` from the synthetic database through the real publish path: four quarters of four-decimal drivers and the bull/bear outputs computed by `agent/scenarios.py` `_flex`. `tests/test_scenario_parity.py` fails if the committed fixture drifts from Python; `site/src/sections/scenarioParity.test.ts` recomputes every case with `recomputeScenario`. Coded by a Haiku subagent, reviewed by Claude Code.
- Result: 56 of 56 values match exactly at four decimals (4 quarters × bull/bear × 7 metrics). Both tests were checked to fail when one expected digit is changed.
**Current state:** `uv run pytest`: 309 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** Parity is defined on bull and bear; the published base uses unrounded inputs, so the browser shows it as published. `toFixed(4)` is exact for these magnitudes (a guard test keeps values below 1e11).
**Last commit:** a3b0c40eb33b45fbc89c3f4b8416ff671a35ae63 on task/M5-T9-scenario-parity

## 2026-11-05 01:44 (America/Los_Angeles) — Claude Code

**Task(s):** M4-T3 (done)
**What changed:**
- `.github/workflows/refresh.yml` ("Refresh data"), coded by a Haiku subagent and reviewed by Claude Code: manual `workflow_dispatch` with a `force` input; the quarterly schedule is a comment only. It checks that `OPENAI_API_KEY` and `SEC_USER_AGENT` secrets are set without printing them, runs `uv run python -m agent run`, and commits only `site/public/data/dashboard.json` and `data/narrative_cache.json` when they changed.
- `deploy.yml` also runs after a successful "Refresh data" run (a push made with `GITHUB_TOKEN` does not trigger other workflows) and builds `main`.
- Claude Code removed an `actions/cache` step whose pin could not be verified from this environment.
**Current state:** `uv run pytest`: 309 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** The workflow needs `python -m agent run` (`M4-T2`). It pushes to `main` with `GITHUB_TOKEN`; branch protection on `main` would block that.
**Last commit:** 80c6cb4d373185a46f16b83180dd089b428879a8 on task/M4-T3-refresh-workflow

## 2026-11-05 01:44 (America/Los_Angeles) — Claude Code

**Task(s):** M3-T8 (done)
**What changed:**
- `agent/verify_stage.py` and `sql/013_verification.sql` (Haiku subagent, reviewed by Claude Code): `verify_quarter`/`verify_all` re-run `review_draft` on each stored narrative and write a per-quarter `verification` row (counts, guard hits, issues, every claim with its status, expected value, and source, and later restatements). `restatements` lists income-statement quarters where a later filing reports a different value; `quarter_actual` keeps the first-reported value. `format_report` prints e.g. "2024-Q1: 2 of 3 figures verified, 1 flagged, 0 unsupported; keyword guard clean; no later restatements."
- `python -m agent narrate [--force]` (needs `OPENAI_API_KEY`, never prints it) and `python -m agent verify`.
- `tests/test_verify_stage.py` (9 tests).
**Current state:** `uv run pytest`: 309 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** `reasked` in the report is always false: the narrative table does not store it yet. Run `verify` after `narrate`. Q4 and cash-flow lines are not checked for restatements (Q4 is derived; cash flow is de-cumulated).
**Last commit:** 4eb7cb1534c6d99e1ac01b7a9945069413bd2330 on task/M3-T8-verify-report

## 2026-11-05 01:44 (America/Los_Angeles) — Claude Code

**Task(s):** M3-T7 (done)
**What changed:**
- Added `agent/review.py` (coded by a Haiku subagent, reviewed by Claude Code): `review_draft` verifies every memo and answer claim against the fact sheet (plus the backtest sheet for the latest quarter), runs the keyword guard, and collects draft issues. `narrate_and_review` drafts a quarter; if the review is not clean it asks the model once more with a plain correction list (each flagged value with the sheet's value, each unsupported key, each guard phrase, each issue). The second draft is kept as written, flags and all; no code path replaces a model's number. A row is marked verified only when its final review is clean. `review_all` runs every published quarter.
- Added `tests/test_review.py` (11 tests): wrong-then-right ends verified; wrong twice stays flagged and unverified with exactly two calls; clean first draft makes one call; an unsupported key and "price target" trigger the re-ask; a cached verified narrative makes no call; final claim values equal what the fake model returned.
**Current state:** `uv run pytest`: 309 passed; site tests and build pass.
**Next step:** Merge this PR, then `M3-T8` (verification report and the `narrate`/`verify` commands, in progress).
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** The re-ask reuses the first draft's input hash, so the cache key stays the input, not the correction.
**Last commit:** 9f5998f970967173a8ba4ecdca152be6a1e26dfc on task/M3-T7-reask

## 2026-11-05 01:30 (America/Los_Angeles) — Claude Code

**Task(s):** M3-T4 (done)
**What changed:**
- `agent/usage.py` and `config/model_prices.json` (Haiku subagent, reviewed by Claude Code): `estimate_cost` from USD per million tokens (gpt-6-luna $0.10 in / $0.50 out, gpt-6-astra $10 / $50, checked 2026-11-04), `summarize_usage` over narration results (calls versus cached), and `format_usage`/`log_usage`, one line with tokens and the estimate, warning above the one-dollar target. Unknown models report the cost as unknown. Tests check that no secret value appears.
**Current state:** `uv run pytest`: 278 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** `M4-T2` writes the `RunUsage` into the published run metadata.
**Last commit:** 29d929b8072ed627056111826ee43842c4046df2 on task/M3-T4-cost-logging

## 2026-11-05 01:21 (America/Los_Angeles) — Claude Code

**Task(s):** M3-T3 (done)
**What changed:**
- `agent/narrate.py` (Haiku subagent, reviewed by Claude Code): before calling the model, `narrate_quarter` reuses a stored narrative only when the quarter, kind, and input hash match and the row is verified; then it returns `cached=True` with zero tokens and no API call. `force=True` always calls the model. `mark_verified` sets the flag for one hash. `sql/012_narrative_verified.sql` adds the `verified` column.
- `tests/test_narrative_cache.py` (13 tests): second run makes zero calls; a model, prompt-version, or fact-sheet change misses only the affected quarters; unverified rows are not reused.
**Current state:** `uv run pytest`: 264 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** `store_narration` writes `verified = result.cached`, so a fresh draft starts unverified until `M3-T7`/`M3-T8` calls `mark_verified`.
**Last commit:** ff3c8d53739dde265051eea58b0e5b35a3bc035b on task/M3-T3-narrative-cache

## 2026-11-05 01:17 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T3 (done)
**What changed:**
- `site/src/components/ticks/`, coded by a Haiku subagent and reviewed by Claude Code: `TickNumber` (green hand-drawn check linking to the filing, amber flag with the expected value, amber outlined question mark), tooltips on hover and focus with the source line, period, source, and result, closed by Escape; `TickLegend`; `NarrativeText`, which numbers sentences and wraps each claim's number in its `sentence_ref` sentence, listing unmatched claims under "Figures not found in the text" instead of dropping them.
**Current state:** `uv run pytest`: 251 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** `M5-T7` (memo) and `M5-T11` (Q&A) render text through `NarrativeText` and show `TickLegend` near the memo.
**Last commit:** dfc3cc51ff88ab990fe3fdcaba7da802c527c2e5 on task/M5-T3-tick-marks

## 2026-11-05 01:13 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T10 (done)
**What changed:**
- `site/src/sections/ForecastChart.tsx` (+ format, CSS, tests), coded by a Haiku subagent and reviewed by Claude Code: custom SVG line chart (d3-scale 4.0.2) of total revenue by quarter, base forecast dashed cobalt with hollow circles and actual solid ink with filled squares, a legend with glyphs and words, $B gridlines. The selected quarter has a rule, a bold label, and hidden "Selected"; quarter labels are buttons that switch quarters. A hidden table repeats the values.
**Current state:** `uv run pytest`: 251 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** Fewer labels below 480px; the selected quarter and its neighbours keep theirs.
**Last commit:** de6116643d8e952b0d62cd07a243ee02bacf2acd on task/M5-T10-forecast-chart

## 2026-11-05 01:09 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T8 (done)
**What changed:**
- `site/src/sections/ForecastSection.tsx` (+ `scenarioMath.ts`, format, CSS, tests), coded by a Haiku subagent and reviewed by Claude Code: Bear/Base/Bull toggle (aria-pressed buttons) and the P&L table (line, forecast, actual, variance $, variance %) with signed variances, favorable green or unfavorable amber plus a hidden word, a sticky first column, and a flex sentence built from `scenario_flex`.
- `recomputeScenario` ports `agent/scenarios.py` `_flex` with exact decimal arithmetic and half-even rounding to four places; tests match the Python output on four invented driver sets.
**Current state:** `uv run pytest`: 251 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** Bull and bear recompute to the published values within 0.0001 for all 12 real quarters. Base does not recompute exactly from the four-decimal drivers (up to about $1.15M on gross profit), because the Python base uses unrounded inputs, so the page shows the published base. `M5-T9` parity covers bull and bear.
**Last commit:** 4a5c49a8edf73fbb94f0e7585b7158bea9eb7582 on task/M5-T8-forecast-table

## 2026-11-05 00:59 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T4 (done)
**What changed:**
- `site/src/sections/HeroSection.tsx` (+ format, CSS, tests), coded by a Haiku subagent and reviewed by Claude Code: the lede ("Q3 2026: forecast $35.53B, actual $28.05B, −$7.48B (−21.1%).") and the custom SVG revenue waterfall (forecast, six drivers, actual) with signed labels, ▲/▼ glyphs, favorable green and unfavorable amber, connectors, and a hidden table. Bars draw in sequence over 1.2 s on first load, then `data-drawn="true"`; reduced motion shows the final state at once. The bridge scrolls horizontally at 480px and below. An empty `.seal-slot` waits for M5-T5.
**Current state:** `uv run pytest`: 251 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** Claude Code changed the axis after a visual check: it starts at a padded level below the bridge's lowest point (not zero), the forecast and actual bars carry a break mark, and a note under the chart says where the axis starts (`bridgeDomain` in `HeroSection.tsx`). A bridge that reaches zero keeps a zero-based axis.
**Last commit:** 38bff51b4055e5687e2718381531b36a53221102 on task/M5-T4-hero-bridge

## 2026-11-05 00:54 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T6 (done)
**What changed:**
- `site/src/sections/AgentRunSection.tsx` (+ format, CSS, tests), coded by a Haiku subagent and reviewed by Claude Code: the six stages in order (1 Ingest to 6 Publish) with durations from `dashboard.run.stages`, Explain marked "Model" and the rest "Code", and a stat list (last run, total run time, AI cost, model, data as of). Nothing animates.
- Claude Code changed the empty rule: until a full run records a start time or a model, the section says "The run details appear after the next full pipeline run." A publish-only run's own duration no longer reads as the pipeline's run time.
**Current state:** `uv run pytest`: 251 passed; site tests and build pass.
**Next step:** Merge this PR and continue down the merge queue.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** `M4-T2` must fill `run.started_at`, `duration_seconds`, every stage's seconds, `model`, tokens, and cost.
**Last commit:** 42a9a1261437ef1917f4661be14b6cd7e34ddcd6 on task/M5-T6-agent-run

## 2026-11-05 00:44 (America/Los_Angeles) — Claude Code

**Task(s):** M5-T12 (done)
**What changed:**
- `site/src/sections/AccuracySection.tsx` (+ `AccuracyFormat.ts`, `AccuracySection.css`, tests), coded by a Haiku subagent and reviewed by Claude Code: absolute percent error by quarter for revenue, gross profit, and operating income, plus a bold average row, from `dashboard.backtest`. Each cell shows the full number and a quiet inline bar capped at 100% with a "+" marker beyond, so a large miss is never clipped. The selected quarter's row is marked. The table scrolls with a sticky first column.
**Current state:** `uv run pytest`: 251 passed; site tests and build pass.
**Next step:** Merge this PR; continue merging the other M5 sections.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** Error bars use quiet ink, not green or amber: an error is not favorable or unfavorable.
**Last commit:** d9e79b3169073d65726f241045fd76ced18d3e40 on task/M5-T12-model-accuracy

## 2026-11-05 00:38 (America/Los_Angeles) — Claude Code

**Task(s):** M3-T2 (done)
**What changed:**
- Added `agent/narrate.py` (coded by a Haiku subagent, reviewed by Claude Code): `narrate_all` drafts a memo for each published quarter with a forecast, oldest first, and the ten answers for the latest quarter only. The user message is JSON holding only the quarter's fact sheet, the questions, and, with the questions, the backtest sheet for questions 7 and 8. `OpenAIClient` uses the Responses API with `text_format=NarrativeDraft` and refuses an empty key.
- `validate_draft` records issues (memo 150–250 words, answers 60–120, the right answer set, a `sentence_ref` past the text) without raising; the re-ask task acts on them. `input_hash` covers the message, the prompt version and content hash, and the model.
- `prompts/memo.md` now requires claims to cite fact-sheet keys and periods, signed values, and fixed unit strings, and to avoid the keyword guard's phrases. Prompt version `2026-11-05.1`. `sql/011_narrative.sql` stores each quarter's draft, tokens, and issues.
- Added `tests/test_narrate.py` (14 tests, fake client, no network).
**Current state:** `uv run pytest`: 251 passed. The real OpenAI call has not run yet; it runs in GitHub Actions with the `OPENAI_API_KEY` secret once `refresh.yml` exists (M4-T3).
**Next step:** Merge this PR. Then `M3-T3` (cache and `--force`) and `M3-T4` (token and cost logging) in parallel, then `M3-T7` (re-ask once) and `M3-T8`.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** `narrate_all` does not write the database; call `store_narration` per result. Temperature is 0.2 from `prompts/manifest.json`; if the configured model rejects `temperature`, handle it in `OpenAIClient`, not in the prompt files.
**Last commit:** c956d48173c847beb2a0e8aae2878b16ebc7926e on task/M3-T2-narrate

## 2026-11-05 00:34 (America/Los_Angeles) — Claude Code

**Task(s):** M5 groundwork (no plan task)
**What changed:**
- `site/src/App.tsx` loads `data/dashboard.json` through `loadDashboard`, shows a loading line and an error section that says what is missing, and drives the quarter picker from the published quarters (`quarterRecords` in `site/src/quarters.ts`). The label-only quarter fixture is gone.
- Each dashboard section has its own component in `site/src/sections/` (`HeroSection`, `AgentRunSection`, `MemoSection`, `ForecastSection`, `ForecastChart`, `AskSection`, `AccuracySection`) taking `SectionProps` (dashboard, selected quarter, `onSelectQuarter`). They render nothing until their M5 task fills them, so section tasks can run in parallel without editing `App.tsx`.
- `site/src/data/testDashboard.ts` is invented sample data for component tests only. `tests/test_quarter_picker.py` fails if production code imports it.
**Current state:** `npm test`: 4 passed; `npm run build` succeeded; `uv run pytest`: 237 passed.
**Next step:** Merge this PR, then run the M5 section tasks in parallel.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** A section task edits only its own file in `site/src/sections/` (plus new helpers and its CSS block). Never show numbers from `testDashboard.ts` on the page.
**Last commit:** a82f8ebe0d3b535eb6baa7921b2877531761bbcd on task/M5-data-wiring

## 2026-11-05 00:29 (America/Los_Angeles) — Claude Code

**Task(s):** M4-T1 (done; pulled forward ahead of M3-T8)
**What changed:**
- Added `agent/publish_schema.py` (pydantic models, `extra="forbid"`) and `agent/publish.py` (`build_dashboard`, `write_dashboard`), and `python -m agent publish`. Coded by a Haiku subagent, reviewed by Claude Code.
- The site reads one file, `site/public/data/dashboard.json`: quarters (P&L lines with forecast, actual, variance, favorable flag; drivers; bull/base/bear; four bridges; memo), Q&A, backtest, scenario flexes, run metadata. `site/src/data/dashboard.schema.json` is generated from the models and a pytest fails on drift. `site/src/data/types.ts` mirrors it with `loadDashboard()`.
- Committed the first real `dashboard.json` from a live run: 12 quarters, 2023-Q4 to 2026-Q3. Memo and Q&A are null until narration lands. Run metadata (model, tokens, cost, stage times) is null until `M4-T2`.
- Plan change and output choices logged in `docs/DECISIONS.md`.
**Current state:** For 2026-Q3 the base forecast was 621,339 deliveries and $35.53B revenue against 486,532 and $28.05B actual (−21.1%). The revenue bars sum exactly to the variance. Backtest average absolute error: revenue 17.1%, gross profit 20.6%, operating income 101.0%. `uv run pytest`: 237 passed; `npm test` 2 passed; `npm run build` succeeded.
**Next step:** Merge this PR, then start the M5 sections against `dashboard.json`.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** `site/public/data/dashboard.json` holds real numbers only: regenerate it with `python -m agent publish` after a live run, never from the test fixture. Change `agent/publish_schema.py`, then regenerate `dashboard.schema.json` and update `types.ts` together.
**Last commit:** eca07f3ca1e57e1865ccb871d309bc806612eb2f on task/M4-T1-publish-json

## 2026-11-05 00:25 (America/Los_Angeles) — Claude Code

**Task(s):** M1-T10 (done)
**What changed:**
- Added `agent/instances.py` (coded by a Haiku subagent, reviewed by Claude Code): reads each 10-Q and 10-K XBRL instance (`*_htm.xml`, found through the filing folder's `index.json`) and stores the segment revenue and cost lines whose context has exactly one dimension, the configured member. `SecClient` gains `filing_folder_index` and `filing_document` (cached, rate-limited, validated names).
- `python -m agent ingest` adds those facts for filings from Jan 1 of (latest report year − 5). Fixture mode reads `<fixtures>/instances/{accession}.xml` when present.
- Added `tests/test_instances.py` (22 tests). Decision logged in `docs/DECISIONS.md`.
**Current state:** Live run on 2026-11-05: ingest stored 2,495 facts; `model` wrote 12 quarters; `variance` wrote all 48 bridges with no failures. For 2026-Q3, automotive sales 20,094,000,000 + credits 113,000,000 + leasing 353,000,000 + energy 2,881,000,000 + services 4,605,000,000 = total revenue 28,046,000,000, and segment costs sum to cost of revenue 22,552,000,000. 2024-Q1 to 2026-Q3 carry all 10 segment lines. `uv run pytest`: 226 passed.
**Next step:** Merge this PR and the M4-T1 PR, then publish the first real `site/public/data/dashboard.json`.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** 2021 to 2023 filings have fewer segment rows, matching the gaps in `config/xbrl_tags.json`. Do not commit `data/fpa.duckdb` or `data/cache/`.
**Last commit:** 105ccfb3215d3b030bbc94ec94c05b64181c4710 on task/M1-T10-segment-instances

## 2026-11-05 00:22 (America/Los_Angeles) — Claude Code

**Task(s):** M3-T5 (done)
**What changed:**
- Added `agent/fact_sheet.py` (written by Claude Code): the contract between narration and verification. Every citable number for a quarter has a key (`actual.<metric>`, `forecast.<scenario>.<metric>`, `variance.<metric>`, `variance_pct.<metric>`, `bridge.<bridge>.<driver>`, `backtest.<metric>.abs_pct_error`, `backtest.<metric>.average_abs_pct_error` for period `12Q`), a period, a unit (USD, percent, units, USD_per_unit), and a source with the filing URL where there is one.
- Added `agent/verifier.py` (coded by a Haiku subagent, reviewed by Claude Code): `verify_claim`/`verify_claims` return verified, flagged (with the expected value), or unsupported. Units normalize ($1.5 billion matches 1,500,000,000). Tolerances: ±0.5% for USD and ASP, ±0.1 points for percent, exact for unit counts (a claim in thousands is compared at its own precision). Opposite signs are flagged. The verifier never edits a claim.
- Added `tests/test_fact_sheet.py` and `tests/test_verifier.py`. Decision logged in `docs/DECISIONS.md`.
**Current state:** `uv run pytest`: 204 passed. Ruff check and format check passed.
**Next step:** Merge this PR, then `M3-T2`: narration sends `quarter_facts` (and `backtest_facts` for questions 7 and 8) as the only input and requires claims to cite fact keys and periods.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** A claim's `metric` is a fact-sheet key and its `period` the fact's period. Variances must be signed. Change the fact keys only together with the prompt and the verifier.
**Last commit:** f2d8faf8fb531cd328b5d50cfe1a1f57f2d820f5 on task/M3-T5-verifier

## 2026-11-05 00:20 (America/Los_Angeles) — Claude Code

**Task(s):** M3-T6 (done)
**What changed:**
- Added `agent/keyword_guard.py`: `check_text` and `check_narrative` return `GuardHit`s for buy/sell recommendations, ratings (overweight, outperform), "price target", "fair value" in price forms, upside/downside to a price, valuation words, "investors should", "we recommend", and "$X per share" outside reported EPS, dividends, or buybacks. Plain variance language passes ("sales", "sold", "buyback", "earnings per share").
- Added `tests/test_keyword_guard.py` (37 tests). Coded by a Haiku subagent and reviewed by Claude Code, which tightened the per-share exemption so a price target later in a sentence that mentions EPS still flags.
**Current state:** `uv run pytest`: 174 passed. Ruff check and format check passed.
**Next step:** Merge this PR. `M3-T8` will put the guard result in the verification report.
**Blockers / questions for Jacob:** (a), (c), and (d) as in the status block.
**Notes for the next agent:** Scenario answers should say "downside case" or name a metric after a percent ("downside of 8% to operating income"); a bare "downside of 8%" flags. "investors should" flags by design.
**Last commit:** 26feabd02059226cd348de9e7b7fee5bc83d302d on task/M3-T6-keyword-guard

## 2026-11-04 21:37 (America/Los_Angeles) — Claude Code

**Task(s):** live-run check (no plan task)
**What changed:**
- First live run from this environment. Fixed `agent/ingest.py`: the SEC client is built from `Settings()`, and the filing index overflow pages are loaded (`SecClient.filing_index_page` in `agent/sec.py`, `merge_submission_pages`). Added a test that runs the real live path with a fake transport.
- Updated blockers (b), (e), and (f) in the status block. Decision logged in `docs/DECISIONS.md`.
**Current state:** Live `python -m agent ingest` stored 1,850 facts, and deliveries run through 2026-Q3. `model` wrote 12 quarters (2023-Q4 to 2026-Q3) with the forward forecast off. `variance` wrote all 12 free cash flow bridges and reported the other 36 as not buildable, because revenue segment lines are missing (`M1-T10`), so forecast total revenue and gross profit are empty. `uv run pytest`: 136 passed.
**Next step:** Claim `M1-T10`. Read the segment lines from each 10-Q and 10-K XBRL instance under `https://www.sec.gov/Archives/edgar/data/1318605/`, through `SecClient`.
**Blockers / questions for Jacob:** (a), (c), (d), and (e) as in the status block.
**Notes for the next agent:** `data/fpa.duckdb` and `data/cache/` are git-ignored. Do not commit them. SEC rejects requests without a real contact `User-Agent`.
**Last commit:** 8246c8d62a18ac3cdc6fe5b3d30e1869de707434 on fix/live-ingest-sec-client

## 2026-11-04 17:57 (America/Los_Angeles) — Claude Code

**Task(s):** M2-T10 (done); M1-T10 added to the plan
**What changed:**
- Added `agent/model_stage.py`, `sql/010_published_quarter.sql`, and the `model` and `variance` subcommands in `agent/__main__.py`. `model` writes bull, base, and bear plus the backtest for the last 12 reported quarters and records them in `published_quarter`. The forward quarter is computed only when `PUBLISH_FORWARD_FORECAST=true`. `variance` writes the four bridges and exits 1, naming each one, when a bridge cannot be built.
- Fixed `agent/revenue_bridge.py` to read actual deliveries from the `deliveries` table. Fixed `agent/actuals.py` so the latest, unfinished year gets cash-flow Q1 to Q3 without waiting for the 10-K. Both bugs were hidden by unit tests that inserted rows directly.
- Added `tests/pipeline_fixture.py` (synthetic 19-quarter database through the real storage path) and `tests/test_model_stage.py`, plus a regression test in `tests/test_actuals.py`.
- Added `M1-T10` to `docs/PLAN.md`. Companyfacts drops the dimension members every revenue segment line needs, so on live data the forecast has no automotive sales or total revenue. Logged in `docs/DECISIONS.md`.
**Current state:** `uv run pytest`: 135 passed. Ruff check and format check passed. On the fixture, all 48 bridges (12 quarters × 4) sum exactly to their variance.
**Next step:** Merge the M2-T10 pull request. Then claim `M1-T10`: fetch each 10-Q and 10-K XBRL instance through `SecClient` (cached, rate-limited), read the contexts whose only explicit member is the configured one, and store the segment lines with `store_reported_facts`. Use a saved instance fixture in tests, with no network.
**Blockers / questions for Jacob:** (a) to (e) as in the status block.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Use `tests/pipeline_fixture.py` for stage tests rather than inserting `quarter_actual` rows by hand: that is how both bugs above hid. The commit named below is the stage commands. The two fixes are the two commits before it.
**Last commit:** 6d470ce98a51078ae94ab45cc8fddfb1102f57ad on task/M2-T10-model-variance-commands

## 2026-11-04 17:50 (America/Los_Angeles) — Claude Code

**Task(s):** M2-T9 (done)
**What changed:**
- Added `agent/free_cash_flow_bridge.py`: an operating cash flow bar and a capex bar (minus the capex change, so higher capex is unfavorable). Actual free cash flow is CFO minus capex, because ingest does not store it.
- Added `tests/test_free_cash_flow_bridge.py`: higher capex is unfavorable, lower capex is favorable, a non-tying stored value is rejected, and the database write sums exactly with rounded forecast inputs. Decision logged in `docs/DECISIONS.md`.
**Current state:** All four bridges exist. `uv run pytest`: 127 passed. Ruff check and format check passed.
**Next step:** Merge the M2-T9 pull request, then claim `M2-T10`: `python -m agent model` writes base, bull, and bear plus the backtest for every published quarter, and `python -m agent variance` writes the four bridges. Neither marks a forward quarter for publication while `PUBLISH_FORWARD_FORECAST=false`.
**Blockers / questions for Jacob:** (a) to (e) as in the status block.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. The commit named below is the bridge. Later commits on this branch only update the handoff.
**Last commit:** cd327ed5ad0273cd502c03aadc1aa86231a0d084 on task/M2-T9-free-cash-flow-bridge

## 2026-11-04 17:50 (America/Los_Angeles) — Claude Code

**Task(s):** M2-T8 (done)
**What changed:**
- Added `agent/operating_income_bridge.py`. The bars are gross profit variance, then R&D, SG&A, and `restructuring_and_other` (opex change minus the R&D and SG&A changes), with the sign flipped so a higher cost is unfavorable. One `operating_expenses` bar replaces the three when either side lacks R&D or SG&A.
- Added `tests/test_operating_income_bridge.py`: a fixture where R&D and SG&A rose, one where they fell, the single-bar fallback, a non-tying actual, and the database write. Decision logged in `docs/DECISIONS.md`.
**Current state:** `uv run pytest`: 122 passed. Ruff check and format check passed.
**Next step:** Merge the M2-T8 pull request, then claim `M2-T9`: operating cash flow and capex bars (higher capex is unfavorable) built with `reconciled()` against stored `free_cash_flow`.
**Blockers / questions for Jacob:** (a) to (e) as in the status block.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. The commit named below is the bridge. Later commits on this branch only update the handoff.
**Last commit:** 5960dc9803d14f8efc1d65710510e3533b22f25d on task/M2-T8-operating-income-bridge

## 2026-11-04 17:47 (America/Los_Angeles) — Claude Code

**Task(s):** M2-T7 (done)
**What changed:**
- Added `agent/gross_profit_bridge.py`. With segment cost on both sides, it writes one bar per segment (revenue effect plus margin-rate effect). Without it, it writes three revenue bars at the forecast total margin plus a `gross_margin_rate` bar. Today every quarter takes the total path, because companyfacts has no segment cost.
- `agent/forecast.py` stores `gross_profit_automotive`, `gross_profit_energy`, and `gross_profit_services` when it uses segment margins. `agent/scenarios.py` leaves them out of bull and bear.
- Added `reconciled()` to `agent/bridge.py`: bars are quantized and the rounding gap goes to the largest bar, so they sum exactly to the stored variance. A gap above $1,000 raises. `agent/revenue_bridge.py` uses it now and ties to stored `total_revenue`. Before this, rounded forecast inputs left the revenue bars cents off the variance.
- Added `tests/test_gross_profit_bridge.py`, a rounded-input test in `tests/test_revenue_bridge.py`, and segment-profit assertions in `tests/test_forecast.py`. Decision logged in `docs/DECISIONS.md`.
**Current state:** `uv run pytest`: 116 passed. Ruff check and format check passed. The site was not touched.
**Next step:** Merge the M2-T7 pull request, then claim `M2-T8`: bars for gross profit variance, R&D, SG&A, and other opex (higher cost is unfavorable), built with `reconciled()` against stored `operating_income`.
**Blockers / questions for Jacob:** (a) to (e) as in the status block. (e) asks whether to merge PR #20 now or wait until Pages is enabled.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not use the stored four-place `gross_margin` in a bridge. Imply margins from dollar amounts. A `gross_margin_rate` bar means the total-margin path ran. The commit named below is the bridge. Later commits on this branch only update the handoff.
**Last commit:** 306a9a85eda536322f241d00b3a185393c7c797d on task/M2-T7-gross-profit-bridge

## 2026-11-04 17:42 (America/Los_Angeles) — Claude Code

**Task(s):** takeover; M2-T7 (in progress)
**What changed:**
- Claude Code took over from Grok and the Cursor agents, whose usage ran out. `docs/BRIEF.md` matches the original brief byte for byte, and every section 11 handoff file is present.
- Found work that was finished but not on `main`: PRs #17, #18, #19, and #21 (`M2-T3` through `M2-T6`, stacked). Merged `main` into `task/M2-T6-revenue-bridge` (docs conflicts only), CI green, merged #21 with a merge commit, so #17 to #19 landed too.
- PR #15 had merged `M5-T14` into `task/M5-T13-how-it-works` after that branch was already on `main`, so the about section never reached `main`. Opened and merged PR #22 to fix that.
- `M4-T4` (PR #20) is done but not merged. Its author wrote that it should wait for Jacob, because the deploy job fails until Pages is turned on. Marked done in `docs/PLAN.md` and added question (e).
- `task/M2-T7-gross-profit-bridge` and `task/M3-T5-verifier` held only claim commits from the Cursor agents, with no code. Claude Code takes over `M2-T7`. `M3-T5` is free to claim again.
**Current state:** `main` at the merge of #22. `uv run pytest`: 107 passed. Ruff check and format check passed. In `site/`, `npm test` (1 passed) and `npm run build` succeeded.
**Next step:** Build `M2-T7` on `task/M2-T7-gross-profit-bridge`: segment volume and margin-rate bars when segment cost is reported, the total-margin path otherwise, summing exactly to the gross profit variance.
**Blockers / questions for Jacob:** (a) to (d) as in the status block, plus (e): merge PR #20 now, or wait until Pages is enabled?
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not enable Pages. Stacked task branches: merge with a merge commit, not a squash, so the PRs below the top one close as merged. Some of the older `task/*` branches look "ahead" of `main` only because they were squash-merged.
**Last commit:** c73ac47e5b0e8830850cafc9216e45c1a1bca595 on main (before this entry)

## 2026-11-04 14:01 (America/Los_Angeles) — Cursor agent

**Task(s):** M4-T4 (done)
**What changed:**
- Added `.github/workflows/deploy.yml`. A push to `main` builds `site/` and uploads `site/dist` for GitHub Pages, then runs `actions/deploy-pages`.
- The workflow does not read or print `OPENAI_API_KEY` or `SEC_USER_AGENT`.
- Added `tests/test_deploy_workflow.py`, which parses the YAML and checks the trigger, the build commands, and the Pages actions. `pyyaml` is a dev dependency for that parse.
- Did not enable GitHub Pages, did not change visibility, and did not change any other repo setting. The question is below.
**Current state:** The workflow file is valid and the test passes. Local `uv run pytest`: 96 passed. Ruff check and format check passed. Pages is still off.
**Next step:** Merge this pull request when Jacob wants the workflow on `main`. The deploy job cannot publish until he sets the Pages source.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Every deliveries `source_url` returned HTTP 403 from this environment, so the live page check did not run. Please run `scripts/check_deliveries --fetch` from a network that can open the investor-relations pages. The CSV was left as transcribed in M1-T4.
- (e) Question: may I leave Pages off? This workflow does not turn it on. To publish, set Settings, Pages, Source to GitHub Actions. Please do that yourself when you want the site live. Do not change the repo from private until you decide that separately.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not enable Pages. Do not change repo visibility. Do not put a secret in `deploy.yml`. The commit named below is the workflow. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** 50de24b9c39d0c4333ee9bdc16bec68e73865df6 on task/M4-T4-deploy-workflow

## 2026-11-04 14:02 (America/Los_Angeles) — Cursor agent

**Task(s):** M2-T6 (done)
**What changed:**
- Added `agent/revenue_bridge.py`. The six bars are volume, price/mix, regulatory credits, leasing, energy, and services.
- Volume is the change in total deliveries times forecast ASP. Price/mix is the change in ASP times actual deliveries. ASP is automotive sales divided by total deliveries. A positive bar is favorable.
- Added `tests/test_revenue_bridge.py`. The leasing limitation is in `docs/DECISIONS.md` for the `M5-T13` methods copy.
**Current state:** The revenue bridge can be stored for one quarter. Gross profit, operating income, and free cash flow bridges are not built yet. Local `uv run pytest`: 104 passed. Ruff check and format check passed.
**Next step:** Merge pull requests #17, #18, and #19, then this one. `M2-T7` should split gross-profit variance into volume and margin-rate bars that sum exactly.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403. No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T6` or `M1-T7`. Leased units stay inside the delivery total. This branch includes `M2-T3` through `M2-T5` until those pull requests are on `main`. The commit named below is the revenue bridge. Later commits on this branch only update the handoff.
**Last commit:** 69b9f4eb7a4be1033000e9076f25c1b58d205257 on task/M2-T6-revenue-bridge

## 2026-11-04 14:01 (America/Los_Angeles) — Cursor agent

**Task(s):** M2-T5 (done)
**What changed:**
- Added `agent/backtest.py`. Absolute percent error is `100 * abs(forecast - actual) / abs(actual)` for total revenue, gross profit, and operating income.
- A miss above 100 percent is stored as that larger percent. An actual of zero keeps the quarter and stores a null error. The average is the mean of the non-null errors and is not a quarter row.
- Added `tests/test_backtest.py`. The choice is in `docs/DECISIONS.md`.
**Current state:** The accuracy table can be written for a quarter that already has a base forecast. The four bridges are not built yet. Local `uv run pytest`: 102 passed. Ruff check and format check passed.
**Next step:** Merge pull requests #17 and #18, then this one. `M2-T6` should build the six-bar revenue bridge so the bars sum to the total revenue variance.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403. No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T6` or `M1-T7`. Do not clip a backtest error. This branch includes the M2-T3 and M2-T4 commits until those pull requests are on `main`. The commit named below is the backtest. Later commits on this branch only update the handoff.
**Last commit:** 71192a1da7659c1ab05acc6839cafa7f223f4b4e on task/M2-T5-backtest

## 2026-11-04 13:57 (America/Los_Angeles) — Cursor agent

**Task(s):** M2-T4 (done)
**What changed:**
- Added `agent/scenarios.py`. Bull and bear flex deliveries, ASP, and gross margin by the config percentages. Automotive sales is the product of the flexed factors. The other lines stay at the base forecast.
- Base rows match `base_forecast()`. An empty base stays empty in all three scenarios.
- Added `tests/test_scenarios.py`. The choice is in `docs/DECISIONS.md`.
**Current state:** Three scenarios can be stored for one quarter. The backtest and the bridges are not built yet. Local `uv run pytest`: 98 passed. Ruff check and format check passed.
**Next step:** Merge the M2-T3 pull request, then this one. `M2-T5` should measure absolute percent error for revenue, gross profit, and operating income, including large misses.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403. No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T6` or `M1-T7`. Do not hardcode 10, 5, or 100 in the scenario function. This branch includes the M2-T3 commits until that pull request is on `main`. The commit named below is the scenario flex. Later commits on this branch only update the handoff.
**Last commit:** cb1ef8002daa2194f8a79b0a3d6cb8430098b1f7 on task/M2-T4-scenarios

## 2026-11-04 13:55 (America/Los_Angeles) — Cursor agent

**Task(s):** M2-T3 (done)
**What changed:**
- Added `agent/forecast.py`. `base_forecast()` applies `config/forecast.json` to cutoff inputs. `write_base_forecast()` stores the base scenario.
- The stored lines are deliveries, ASP, automotive sales, regulatory credits, leasing, energy, services, total revenue, gross margin, gross profit, operating expenses, operating income, CFO, capex, and free cash flow. R&D and SG&A are added when their history can build a run-rate.
- Fewer than four earlier quarters sets `empty_history` and leaves the value null. A later filing and the target quarter's deliveries are not inputs.
- Added `tests/test_forecast.py`. The choice is in `docs/DECISIONS.md`.
**Current state:** The base forecast can be written for one quarter. Scenarios, the backtest, and the bridges are not built yet. Local `uv run pytest`: 96 passed. Ruff check and format check passed.
**Next step:** Merge the M2-T3 pull request. `M2-T4` should flex deliveries, ASP, and gross margin from the config percentages and keep base equal to this forecast.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403. No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T6` or `M1-T7`. Do not hardcode the scenario percentages. Capex in `forecast` is `purchases_of_property_and_equipment`. `gross_margin` is the ratio that turns forecast revenue into forecast gross profit. This branch is based on `main` after the M2-T2 merge. The commit named below is the base forecast. Later commits on this branch only update the handoff.
**Last commit:** c639f699414bda0669f7b3a20fbb3ebd24e024db on task/M2-T3-base-forecast

## 2026-11-04 13:48 (America/Los_Angeles) — Cursor agent

**Task(s):** M2-T2 (done)
**What changed:**
- Added `agent/forecast_inputs.py`. The cutoff for quarter Q is the earliest filing date of the 10-Q or 10-K whose period end is Q-1. An amendment does not move that date later.
- Facts come from `fact_as_of(cutoff_date)`. A restatement filed on or before the cutoff is the forecast input. `quarter_actual` stays the first report.
- Deliveries and production for Q, and any later quarter, are excluded. A release date on or before the cutoff is not enough to include Q's own row.
- Added `tests/test_forecast_inputs.py`. The choice is in `docs/DECISIONS.md`.
**Current state:** Forecast inputs can be loaded for one target quarter. The base P&L is not computed yet. Local `uv run pytest`: 93 passed. Ruff check and format check passed.
**Next step:** Merge the M1-T9 pull request, then this one. `M2-T3` should build the base forecast from these inputs and the formulas in `config/forecast.json`.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403. No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T6` or `M1-T7`. Do not read `quarter_actual` as the forecast input when a later filing on or before the cutoff restates the period. Do not include the target quarter's deliveries. This branch includes the M1-T9 commits until that pull request is on `main`. The commit named below is the cutoff loader. Later commits on this branch only update the handoff.
**Last commit:** 159b63e7e00388a0563c8203d1de442f7bb6823f on task/M2-T2-cutoff-no-lookahead

## 2026-11-04 13:47 (America/Los_Angeles) — Cursor agent

**Task(s):** M5-T14 (done)
**What changed:**
- Added the about section after the methods section. The credit is "Built by Jacob Kambour, MS Finance & Analytics, Santa Clara University."
- GitHub, LinkedIn, and résumé are read from `profileLinks` in `site/src/config.ts`. All three stay empty strings. A blank row says "Not filled in yet" and is not a link.
- Added `tests/test_about.py`. Recorded the blank-link choice in `docs/DECISIONS.md`.
**Current state:** The about block follows the methods section, under the quarter status. This branch is rebased onto `task/M5-T13-how-it-works`, which is on `main` with the quarter picker. Ruff check and format check passed. `npm test` and `npm run build` in `site/` succeeded. A local preview at `http://127.0.0.1:4173/tesla-fpa-agent/` was checked. No links are rendered. Pages is not enabled.
**Next step:** Merge the M5-T13 pull request, then this one. Fill `profileLinks` only when Jacob supplies the URLs.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Every deliveries `source_url` returned HTTP 403 from this environment, so the live page check did not run. Please run `scripts/check_deliveries --fetch` from a network that can open the investor-relations pages. The CSV was left as transcribed in M1-T4.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not enable Pages. Do not invent GitHub, LinkedIn, or résumé URLs. The commit named below is the section. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** 3961ba389d9d3048a6f9a6667da8ef6739edd712 on task/M5-T14-about

## 2026-11-04 13:45 (America/Los_Angeles) — Cursor agent

**Task(s):** M5-T13 (done)
**What changed:**
- Added an inline SVG of the six pipeline stages. Below 481px the same stages are a vertical SVG. Explain is marked Model. The other stages are marked Code.
- The fixture in `site/src/methodExample.ts` is labeled "Example of the pipeline. Not a recorded run." It has no durations and no dollar amounts.
- The section says the code checks figures and the model writes, that this page does not call the model, how verified, flagged, and unsupported figures differ, that the sources are public SEC filings and investor-relations releases only, and that leased units sit inside total deliveries.
- Added `tests/test_method_section.py`. Recorded the choice in `docs/DECISIONS.md`.
**Current state:** The methods section is on the page under the quarter status. Rebased onto `main` after the quarter picker merged. Ruff check and format check passed. `npm run build` in `site/` succeeded. A local preview at `http://127.0.0.1:4173/tesla-fpa-agent/` was checked in light at 1280px and in dark at 375px. The wide diagram shows on the desktop width. The narrow diagram shows at 375px. No horizontal overflow. No console warnings. Pages is not enabled.
**Next step:** Merge this pull request. `M5-T6` should take durations from published run metadata, not from `methodExample.ts`.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Every deliveries `source_url` returned HTTP 403 from this environment, so the live page check did not run. Please run `scripts/check_deliveries --fetch` from a network that can open the investor-relations pages. The CSV was left as transcribed in M1-T4.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not enable Pages. Do not put a recorded duration or a dollar amount in `methodExample.ts`. `.narrative` is only for the memo and the Q&A. The commit named below is the section. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** 23b6ee0368dd2a5732f32121f3d27cfc48dba1f7 on task/M5-T13-how-it-works

## 2026-11-04 13:39 (America/Los_Angeles) — Cursor agent

**Task(s):** M1-T9 (done)
**What changed:**
- Added `agent/ingest.py` and `agent/__main__.py`. `python -m agent ingest` validates `deliveries.csv`, stores per-filing facts, rebuilds `quarter_actual`, and loads the deliveries table.
- `--fixtures` reads `companyfacts.json` and `submissions.json` and does not call the SEC client. The default path uses `SecClient`. Neither path prints `SEC_USER_AGENT` or `OPENAI_API_KEY`, and neither path calls `fetch_source_page`.
- After the load, the database must hold the last 12 `total_revenue` quarters plus the earlier quarters in `config/forecast.json` `input_offsets` (five, through Q-5). Older rows stay, including a restatement in `fact`.
- Added `tests/test_ingest.py`. The choice is in `docs/DECISIONS.md`.
**Current state:** The ingest command runs from fixtures. Segment lines are still blank because companyfacts has no dimensions. Local `uv run pytest`: 81 passed. Ruff check and format check passed.
**Next step:** Merge the M1-T9 pull request. The ingest command is the load step a later `python -m agent run` can call.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403. No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T6` or `M1-T7`. Do not scrape investor-relations pages from ingest. Do not drop an older `fact` row. This branch is rebased onto `main` after the M1-T8 squash. The commit named below is the ingest command after that rebase. Later commits on this branch only update the handoff.
**Last commit:** 5da704bcb15846fd72b6e8775e317d70f28575ba on task/M1-T9-ingest

## 2026-11-04 13:36 (America/Los_Angeles) — Cursor agent

**Task(s):** M5-T2 (done)
**What changed:**
- Added a masthead quarter listbox. Q3 2026, the latest fixture quarter, is selected on load. Choosing Q4 2025 shows the required history sentence once.
- The fixture in `site/src/quarters.ts` is labels only. Q4 2025 has no forecast. Later quarters do. No wireframe dollar amounts.
- The open list sits in the masthead, above the double rule, so it does not cover the headline at 375px. The selected row uses an ink tick and the word Selected.
- Added `site/src/App.test.tsx`. `npm test` runs Vitest. The site CI job runs that command before `npm run build`.
- Recorded the fixture and the listbox in `docs/DECISIONS.md`.
**Current state:** The shell can switch quarters. Rebased onto `main` after `M1-T9` and `M2-T2` merged. In `site/`, `npm test` and `npm run build` succeeded on the same site files. A local preview at `http://127.0.0.1:4173/tesla-fpa-agent/` was checked in light and dark, at 1280px and 375px: default quarter Q3 2026, Q4 2025 shows the history sentence, the menu does not cover the headline, keyboard focus is cobalt, and the console had no warnings. Pages is not enabled.
**Next step:** Merge this pull request. M5-T4 should replace the placeholder lede with published forecast, actual, and variance, and should not hardcode the wireframe amounts.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Every deliveries `source_url` returned HTTP 403 from this environment, so the live page check did not run. Please run `scripts/check_deliveries --fetch` from a network that can open the investor-relations pages. The CSV was left as transcribed in M1-T4.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not enable Pages. Keep one footer and the existing h1. `.narrative` is only for the memo and the Q&A. The empty sentence must stay exact when a quarter has fewer than four earlier quarters. Replace `quarterFixture` when published JSON exists. Do not put dollar amounts in that fixture. The commit named below is the picker. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** e81cc88aed6b085284c2e90cadc3841148f6794d on task/M5-T2-shell-quarter-picker

## 2026-11-04 13:33 (America/Los_Angeles) — Cursor agent

**Task(s):** M1-T8 (done)
**What changed:**
- Added `agent/actuals.py`. `store_reported_facts()` inserts one `filing` row and one `fact` row per accession. A second filing of the same period is another row, with its own accession, filing date, and filing URL.
- `assemble_quarter_actuals()` rebuilds `quarter_actual`. Q1–Q3 income lines come from the 10-Q whose period end is that quarter. A later comparative stays in `fact`. Q4 is `derive_q4` from the 10-K annual amount minus those three quarters. Cash-flow lines go through `cash_flow_quarters`.
- `facts_from_companyfacts()` reads consolidated tags only. Member tags are skipped because companyfacts has no dimensions. The choice is in `docs/DECISIONS.md`.
- Added `tests/test_actuals.py`.
**Current state:** Facts and first-reported quarters can be loaded from a fixture. No ingest command yet, and no filing-instance read for segment lines. Local `uv run pytest`: 78 passed. Ruff check and format check passed.
**Next step:** Merge the M1-T8 pull request. `M1-T9` should call `apply_schema()`, `store_reported_facts()`, `assemble_quarter_actuals()`, and `validate_deliveries`. It should not fetch investor-relations pages.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403. No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T6` or `M1-T7`. Do not drop an older `fact` row when a later filing repeats the period. Do not fill a segment line from companyfacts. This branch is rebased onto `main` after the M5-T1 squash. The commit named below is the storage loader after that rebase. Later commits on this branch only update the handoff.
**Last commit:** 3251c5e109cf7bd758292d7d103d90362bf0ae34 on task/M1-T8-per-filing-storage

## 2026-11-04 13:22 (America/Los_Angeles) — Cursor agent

**Task(s):** M1-T3 (done)
**What changed:**
- Added `sql/001` through `sql/007` for `filing`, `fact`, `deliveries`, `quarter_actual`, `forecast`, `bridge`, and `backtest`. `fact` keeps one row per metric, period, and accession. `fact.accession` references `filing`.
- Added `sql/008_fact_with_source.sql`, the join that puts the filing date and URL on each fact, and `sql/009_fact_as_of.sql`, the macro that returns the latest row on or before a cutoff and leaves older rows in `fact`.
- Added `agent/schema.py`, which only executes those files in name order, and `tests/test_schema.py`. Money columns are `DECIMAL(24, 4)`. The choice is in `docs/DECISIONS.md`.
**Current state:** A new DuckDB file gets the raw tables and the empty tables later stages fill. Local `uv run pytest`: 56 passed. Ruff check and format check passed.
**Next step:** Merge the M1-T3 pull request. `M1-T8` should insert per-filing rows into `fact` and read `fact_as_of(cutoff_date)` for the latest value. `M1-T9` should call `apply_schema()` before loading.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403. No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T6` or `M1-T7`. Do not drop an older `fact` row when a later filing repeats the period. This branch is rebased onto `main` after the M1-T2 squash. The commit named below is the SQL and the loader after that rebase. Later commits on this branch only update the handoff: the done hash in `docs/PLAN.md`, and this entry in `docs/PROGRESS.md`.
**Last commit:** 129229b4fdf1e0e6a86c4053fd8abb35701a77a4 on task/M1-T3-duckdb-schema

## 2026-11-04 13:20 (America/Los_Angeles) — Cursor agent

**Task(s):** M1-T2 (done)
**What changed:**
- Added `config/xbrl_tags.json` and `agent/xbrl_map.py`. Each required series has at least one tag. The loader rejects a required metric with an empty tag list.
- Automotive sales is searched in filing order: `tsla:AutomotiveSalesRevenue` on `tsla:AutomotiveRevenuesMember` (2022), then `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` on `tsla:AutomotiveSalesMember` (2023 onward), then the same concept on `us-gaap:AutomobilesMember` (2021). Credits and leasing follow that split. The checked filings' three automotive lines add up to automotive revenue.
- Energy uses the parent member, which includes energy leasing. Segment cost tries `us-gaap:CostOfRevenue` first and `us-gaap:CostOfGoodsAndServicesSold` only where the 2022 10-K left the member off `CostOfRevenue`. A missing tag stays blank.
- Documented the companyfacts limit: the feed has no `tsla` concepts and no dimensions, so segment lines come from the filing instance. Free cash flow is computed. Deliveries and production stay in the CSV. The choice is in `docs/DECISIONS.md`.
- Added `tests/test_xbrl_map.py`.
**Current state:** The map loads and names every required tag. It does not extract facts yet. Local `uv run pytest`: 59 passed. Ruff check and format check passed.
**Next step:** Merge the M1-T2 pull request. `M1-T8` should read facts with this map, from the filing instance when a tag has a member or a `tsla` concept, and leave the quarter blank when nothing matches.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403. No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T6` or `M1-T7`. Do not sum members to fill a missing tag, and do not read `tsla:AutomotiveSales` as revenue or cost. The commit named below is the map and the loader after the rebase onto `main`. Later commits on this branch only update the handoff: the done hash in `docs/PLAN.md`, and this entry in `docs/PROGRESS.md`.
**Last commit:** d14ad517a677dbe44c91d60068f427502d58ff13 on task/M1-T2-xbrl-tag-map

## 2026-11-04 13:11 (America/Los_Angeles) — Cursor agent

**Task(s):** M1-T5 (done)
**What changed:**
- Added `agent/deliveries.py`. `validate_deliveries` checks the CSV for a quarter gap, a missing source URL, and a quarter-over-quarter move strictly above 50%. It does not fetch.
- Added `scripts/check_deliveries`. It always runs the structural check. `--pages-dir` reads saved HTML. `--fetch` GETs each `source_url`.
- Added `tests/test_check_deliveries.py`. Saved-page fixtures cover a match and a mismatch. Structural fixtures cover a gap, a missing source, and an implausible move. The committed CSV passes with the network blocked.
- Recorded the 50% rule and the opt-in fetch in `docs/DECISIONS.md`.
**Current state:** Deliveries can be validated without a network. Local `uv run pytest`: 31 passed. `uv run ruff check .` and `uv run ruff format --check .` passed. `scripts/check_deliveries --fetch` returned `FETCH_FAILED` with HTTP 403 for all 20 quarters. No `MISMATCH` line. No CSV number was edited.
**Next step:** Merge the M1-T5 pull request. Jacob runs `scripts/check_deliveries --fetch` where `https://ir.tesla.com` loads. Do not replace a total because the fetch was blocked.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
- (d) Every deliveries `source_url` returned HTTP 403 from this environment, so the live page check did not run. Please run `scripts/check_deliveries --fetch` from a network that can open the investor-relations pages. The CSV was left as transcribed in M1-T4.
**Notes for the next agent:** Do not edit `docs/BRIEF.md`. The private-repo override is in `docs/DECISIONS.md`. Refer to secrets only by env var name. `validate_deliveries` is what ingest should call. Do not call `fetch_source_page` from ingest. Branch `task/M1-T4-M1-T5-deliveries` had claimed M1-T4 and M1-T5 with no implementation; M1-T4 was already on `main` from pull request #3, and this branch is the M1-T5 work. `M1-T6` and `M1-T7` are taken by another agent. The commit named below is the checker. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** 8a069eb89a66c93bc57b47c4bb7359b3b9c56d63 on task/M1-T5-check-deliveries

## 2026-11-04 13:06 (America/Los_Angeles) — Cursor agent

**Task(s):** M3-T1 (done)
**What changed:**
- Added `prompts/manifest.json` (version `2026-11-04.1`, temperature `0.2`), `prompts/memo.md`, and `prompts/questions.json`. The ten section 4 questions are in the questions file. Questions 7 and 8 set `uses_backtest` and say to use all 12 published quarters.
- Added `agent/narrative.py`. `NarrativeDraft` requires a memo and answers. A claim requires `metric`, `period`, `value`, `unit`, and `sentence_ref`. `load_prompts()` returns the version and a SHA-256 of the three prompt files. `cache_material` is the version plus that hash.
- An empty or missing `OPENAI_MODEL` now resolves to `gpt-6-luna`. `.env.example` stays blank. The choice is in `docs/DECISIONS.md`.
- Added `tests/test_narrative_prompts.py` and a blank-model settings test. No test calls the model.
**Current state:** Prompts and the response schema only. No narration call and no cache yet. After rebasing onto `main`, local `uv run pytest`: 51 passed, which includes the M2-T1 tests. The earlier GitHub Actions run 41913074156 on pull request #7, commit `4f8a5b5`, was before that rebase: job `pytest` succeeded, 43 passed in 2.67s. Ruff check and format check passed.
**Next step:** Merge the M3-T1 pull request. `M3-T2` should call the model with `PromptBundle` and parse `NarrativeDraft`. `M3-T3` should hash `cache_material` with the input tables and the model id.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live model call needs `OPENAI_API_KEY`. CI does not call the model.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv`. Do not claim `M1-T2`, `M1-T3`, `M1-T5`, or `M5-T1`. The default model id is `gpt-6-luna`; override it with `OPENAI_MODEL`. Do not put an email in a prompt file. The commit named below is the prompts and the schema. Later commits on this branch only update the handoff: the done hash in `docs/PLAN.md`, and this entry in `docs/PROGRESS.md`.
**Last commit:** 8b9d6f1d0b6d49438adadc60f59ef3708701090b on task/M3-T1-prompts

## 2026-11-04 13:04 (America/Los_Angeles) — Cursor agent

**Task(s):** M2-T1 (done)
**What changed:**
- Added `config/forecast.json` and `agent/forecast_config.py`. The cutoff is the previous quarter's filing date. Drivers read only earlier quarters. The loader rejects an offset of zero or a later quarter.
- Deliveries are `D(Q-4) * (1 + g)` with `g` from `D(Q-1)` and `D(Q-5)`. ASP is a four-quarter average. Automotive sales are deliveries times ASP. Credits, leasing, energy, services, and operating expenses are a four-quarter run-rate with that same year-over-year growth. Gross margin and capex are four-quarter averages. Free cash flow is forecast CFO minus forecast capex.
- Bull, base, and bear flex only deliveries (+10 / 0 / -10 percent), ASP (+5 / 0 / -5 percent), and gross margin (+100 / 0 / -100 basis points).
- Added `tests/test_forecast_config.py`. Recorded the choices in `docs/DECISIONS.md`.
**Current state:** The formulas are documented and load. They are not executed yet. Local `uv run pytest`: 44 passed. Ruff check and format check passed.
**Next step:** Merge the M2-T1 pull request. M2-T3 should execute this config and keep the empty-forecast rule at four earlier quarters. M2-T4 should read the scenario integers from the config.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
**Notes for the next agent:** Do not edit `docs/BRIEF.md`. The flexes are case-study assumptions, not guidance. `g = 0` when `D(Q-5)` is missing; do not fill it from the target quarter. Leasing uses the run-rate formula and still overlaps total deliveries. Capex and the capex identity use a positive purchases amount. The commit named below is the config and the loader. A later commit on this branch only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** 90a90910c6ddcbef6355b3683d6f856d6bcfd36c on task/M2-T1-driver-formulas

## 2026-11-04 13:01 (America/Los_Angeles) — Cursor agent

**Task(s):** M5-T1 (done)
**What changed:**
- Added `site/` as a Vite, React, and TypeScript app. `base` is `/tesla-fpa-agent/`. npm is the package manager, and `site/package-lock.json` pins the install. `npm run build` runs `tsc -b && vite build`.
- Set the section 6 palette, a dark mode, IBM Plex Sans, Source Serif 4, and tabular figures. The dark hexes and their contrast ratios are in `docs/DECISIONS.md` and `site/src/styles/tokens.css`.
- The page is the workpaper frame: masthead, the section 5 headline, an empty state that names the missing quarter, and the required disclaimer in `site/src/config.ts`. No quarter picker, no waterfall, and no wireframe dollar amounts.
- Added a `site build` job to `.github/workflows/test.yml`. It runs `npm ci` and `npm run build` on pull requests. It does not receive secrets and does not enable Pages.
- Added `tests/test_site_shell.py` for the base path, the palette, the type, and WCAG AA contrast.
**Current state:** Site shell builds. Local `uv run pytest`: 30 passed, including the deliveries tests from `M1-T4` and the new site checks. `npm run build` in `site/` succeeded. A local preview at `http://127.0.0.1:4173/tesla-fpa-agent/` was checked in light and dark, at 1280px and 375px, including keyboard focus. No console warnings. Pages is not enabled.
**Next step:** Merge the M5-T1 pull request. Then create `task/M5-T2-shell-quarter-picker`, set `M5-T2` to `in progress (agent name, date)`, and push that claim before adding the picker. Keep the existing header string and the disclaimer. Add the empty state "No forecast for this quarter: it needs four earlier quarters of history." when a fixture says the quarter lacks history.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values).
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
**Notes for the next agent:** Do not edit `docs/BRIEF.md`. The header already reads "Tesla FP&A Agent" and the footer disclaimer is already the exact section 5 sentence. Do not add a second footer. The `h1` is already the M5-T4 headline. Add the quarter line and the waterfall under it, and do not hardcode the wireframe amounts. `.narrative` is Source Serif 4 at line-height 1.55. Use it only for the memo and the Q&A. `profileLinks` in `site/src/config.ts` are blank on purpose. Dark mode is `data-theme` on the document element. The storage key is `paper-theme`. The inline script in `site/index.html` sets it before paint. Keep `base` as `/tesla-fpa-agent/`. Node 22, `npm ci` in `site/`, then `npm run build`. Do not enable Pages. Do not edit `data/manual/deliveries.csv` in a site task. The commit named below is the site shell. The tip of this branch may be one commit later, and that later commit only writes this hash into `docs/PLAN.md` and this entry into `docs/PROGRESS.md`.
**Last commit:** f3a797ed4f48512ae53791fd0e25a0fae291affd on task/M5-T1-site-shell

## 2026-11-04 12:58 (America/Los_Angeles) — Cursor agent

**Task(s):** M1-T6 (done), M1-T7 (done)
**What changed:**
- Added `agent/sec.py`. It downloads Tesla companyfacts and the submissions filing index, sends `User-Agent` from `SEC_USER_AGENT`, and fails closed when that value is empty. Bodies are cached under `data/cache/`. A second read of the same URL does not call the network. Network calls are spaced at least 100ms apart.
- Added `agent/quarters.py`. Q4 is the annual figure minus Q1–Q3. Year-to-date cash flow becomes single quarters (Q1 unchanged, Q2 minus Q1, Q3 minus Q2). Free cash flow is quarterly CFO minus quarterly capex.
- Added fixture JSON under `tests/fixtures/sec/` and `tests/test_sec_client.py` plus `tests/test_quarters.py`. The SEC tests do not call data.sec.gov.
- Recorded the client and the quarter formulas in `docs/DECISIONS.md`. `data/manual/deliveries.csv` is unchanged.
**Current state:** No ingest command yet. The SEC client and the quarter functions are importable. Local `uv run pytest`: 36 passed. GitHub Actions run 41911801747 on pull request #4, commit `1b39801`, job `pytest`: success, 36 passed in 2.39s. Ruff check and format check passed in that job.
**Next step:** Merge the M1-T6 / M1-T7 pull request. Then claim `M1-T2`, `M1-T3`, or `M1-T5` (M1-T4 is already on `main`). `M1-T8` should call `SecClient.companyfacts`, `SecClient.filing_index`, `derive_q4`, and `decumulate_ytd`.
**Blockers / questions for Jacob:**
- (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
- (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
- (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
**Notes for the next agent:** Do not edit `docs/BRIEF.md` or `data/manual/deliveries.csv` in this task's follow-ups. Income-statement lines are already single quarters; do not pass them through `decumulate_ytd`. Capex passed to `free_cash_flow` is the positive purchases amount. The filing index URL is the submissions JSON, not the HTML browse page. `SEC_USER_AGENT` is read only via `get_secret_value()` inside `SecClient.from_settings`. Refer to it by name. The commit named below is the client and the quarter math. Later commits on this branch only update the handoff: the done hash in `docs/PLAN.md`, and this entry in `docs/PROGRESS.md`.
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
