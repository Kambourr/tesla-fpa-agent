# Progress

## Current status

- **Current milestone:** M2 model and variance. Claude Code is the builder. `M2-T7` is done on `task/M2-T7-gross-profit-bridge` and goes to `main` with its pull request. `M0-T1`, `M1-T1` through `M1-T9`, `M2-T1` through `M2-T6`, `M3-T1`, `M5-T1`, `M5-T2`, `M5-T13`, and `M5-T14` are on `main`. `M4-T4` is done on `task/M4-T4-deploy-workflow` (PR #20) and stays off `main` until Jacob decides on Pages.
- **Tasks done:** 23 of 53 (43%).
- **What's next:** `M2-T8` (operating income bridge), then `M2-T9`, `M3-T5`, `M3-T6`, and `M2-T10`. Build bridge bars with `reconciled()` in `agent/bridge.py`.
- **Open blockers:**
  - (a) The brief says the repo should be public, but Jacob said do NOT make it public, enable Pages, or change repo settings without his explicit go-ahead. The repo is currently private, so Pages deployment needs his decision.
  - (b) Jacob must add repo secrets `OPENAI_API_KEY` and `SEC_USER_AGENT` (names only, never values). A live SEC call needs `SEC_USER_AGENT`. CI does not call the live site.
  - (c) Later: spot-check `deliveries.csv`, fill in links in `site/src/config.ts`, check employer policy.
  - (d) Live check of `deliveries.csv`: from this environment every `source_url` returned HTTP 403 (Akamai Access Denied in headless Chrome too). No total was compared and none was changed. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.
  - (e) PR #20 (`deploy.yml`) is ready. Once it is on `main`, every push to `main` runs a deploy job that fails until Pages is set to GitHub Actions. Jacob: merge it now and accept the red deploy runs, or wait until you enable Pages?
- **How to run the project right now:** Install [uv](https://docs.astral.sh/uv/), then from the repo root run `uv sync` and `uv run pytest`. `write_revenue_bridge(connection, quarter)` and `write_gross_profit_bridge(connection, quarter)` store the revenue and gross profit bars. Each bridge sums exactly to the stored actual minus the base forecast. Nothing fetches on a test run. For the site, install Node 22, then in `site/` run `npm ci`, `npm test`, and `npm run build`. `npm run dev` serves the app at the `/tesla-fpa-agent/` base path.

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
