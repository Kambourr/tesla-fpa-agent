# Build plan

The build is milestones M0 through M6. Each task is one agent session or less. Claim a task by setting its status to `in progress (agent name, date)` and pushing that change before starting work. When it finishes, set `done (commit hash)`. Use `blocked (reason)` when you cannot proceed. Never delete a task; mark a superseded one `superseded (reason)` and point at its replacement.

Status values are exactly: `todo`, `in progress (agent name, date)`, `done (commit hash)`, `blocked (reason)`.

**Tasks done:** 35 of 54 (65%). Recompute this from the status lines when you finish a task, and update the current-status block in `docs/PROGRESS.md`.

Acceptance checks are commands or tests. Do not mark a task done if its check has not been run. Product code starts at M1-T1. Add it only on that task's branch, or on a later task branch after its dependencies are on `main`.

## Order and parallelism

Milestones are grouped for reading. The IDs are not a single file queue: tasks in the same parallel group may be claimed by different agents on different branches after their dependencies are on `main`.

Critical path for the pipeline:

`M0-T1` → `M1-T1` → `M1-T6` → `M1-T8` → `M1-T9` → `M2-T2` → `M2-T3` → `M2-T10` → `M3-T2` → `M3-T7` → `M3-T8` → `M4-T1` → `M4-T2` → `M6-T3` → `M6-T5` → `M6-T6`

The four bridges (`M2-T6`–`M2-T9`), scenarios (`M2-T4`), and the backtest (`M2-T5`) sit between `M2-T3` and `M2-T10` and run in parallel with each other.

Critical path for the dashboard, joining the pipeline at the published JSON:

`M1-T1` → `M5-T1` → `M5-T2` → `M5-T4` → `M5-T15` → `M6-T1` → `M6-T5` → `M6-T6`

`M5-T9` also waits on `M2-T4`.

After `M1-T1` is on `main`, three tracks can run at once:

| Track | Tasks | Wait for |
|---|---|---|
| Data | `M1-T2`, `M1-T3`, `M1-T4`, `M1-T6`, `M1-T7` together, then `M1-T5` after `M1-T4`, then `M1-T8`, then `M1-T9` | `M1-T1` |
| Model notes and prompts | `M2-T1`, `M3-T1` | `M1-T1` |
| Site shell | `M5-T1`, then `M5-T2`, then `M5-T13` and `M5-T14` | `M1-T1` |

After `M2-T3` is on `main`: `M2-T4`, `M2-T5`, `M2-T6`, `M2-T7`, `M2-T8`, `M2-T9` together, then `M2-T10`.

After `M3-T1` and `M1-T9` are on `main`: `M3-T5` and `M3-T6` can start even if narration is still in progress. After `M3-T2`: `M3-T3` and `M3-T4` in parallel. `M3-T7` waits on `M3-T2` and `M3-T5`. `M3-T8` waits on `M3-T3`, `M3-T4`, `M3-T6`, and `M3-T7`.

After `M4-T1` is on `main`: dashboard sections that read JSON (`M5-T4` through `M5-T12`) can proceed with the real schema. `M4-T3` (`refresh.yml`) waits on `M4-T2`. `M4-T4` (`deploy.yml`) waits on `M5-T1` and can run in parallel with `M4-T3`. Neither workflow task enables Pages or changes repo settings.

`M6` is last. `M6-T5` (secret scan) runs after every other task except the closeout entry, then `M6-T6` repeats the scan if the closeout commit adds anything beyond the handoff docs.

## M0 — Handoff

Docs only, before product code. Section 11.

### M0-T1 — Handoff docs and build plan

- **Goal:** Commit the brief, the plan, the handoff log, the decision log, and the agent entry points so the next agent can start from the repo alone.
- **Acceptance:** `docs/BRIEF.md` matches the build brief byte for byte; `AGENTS.md` and `CLAUDE.md` are the section 11 instruction and match each other; `.cursor/rules/handoff.mdc` is always applied and carries that same instruction; `docs/PLAN.md`, `docs/PROGRESS.md`, and `docs/DECISIONS.md` exist; the branch is `task/M0-T1-handoff-docs` with a pull request into `main`.
- **Depends on:** none
- **Can run in parallel with:** none
- **Status:** done (d0b5373c1000411fc88ad7d362bfca2ed6a31d0c)

## M1 — Setup and data ingest

Public data only. SEC companyfacts for CIK 0001318605, plus the filing index so every value can link to its 10-Q or 10-K. Deliveries stay in `data/manual/deliveries.csv` and are not scraped on a normal run.

### M1-T1 — Repo scaffolding

- **Goal:** Create the Python project, lockfile, ignore rules, env template, and CI test workflow so later tasks have one place to put code.
- **Acceptance:** `pyproject.toml` and a lockfile are committed; `uv sync` (or the documented pip equivalent) installs Python 3.11+ and pytest; `.gitignore` ignores `.env` and `data/cache/` and does not ignore `data/manual/`; `.env.example` lists `OPENAI_API_KEY`, `OPENAI_MODEL`, `SEC_USER_AGENT`, and `PUBLISH_FORWARD_FORECAST=false` with no secret values; `.github/workflows/test.yml` runs the test suite on pull requests; that workflow is green on this task's PR.
- **Depends on:** M0-T1
- **Can run in parallel with:** none (everything else waits on this)
- **Status:** done (6eec3c6878ebf6a3b2f87d4ddf728ab57bd9b5a4)

### M1-T2 — XBRL tag map

- **Goal:** Map every quarterly series in section 4 to the XBRL tags Tesla reports, in one config file, including what to do when a tag is missing.
- **Acceptance:** The config covers total revenue, automotive sales, automotive regulatory credits, automotive leasing, energy generation and storage, services and other, cost of revenues (total and by segment where reported), gross profit, R&D, SG&A, total operating expenses, operating income, net cash from operating activities, and purchases of property and equipment. A test fails if a required metric has no tag. Gaps and tag changes are documented in the config, and the mapping choice is recorded in `docs/DECISIONS.md`.
- **Depends on:** M1-T1
- **Can run in parallel with:** M1-T3, M1-T4, M1-T6, M1-T7, M2-T1, M3-T1, M5-T1
- **Status:** done (d14ad517a677dbe44c91d60068f427502d58ff13)

### M1-T3 — DuckDB schema and SQL

- **Goal:** Define the local DuckDB database in `.sql` files so raw filings, deliveries, and later forecast tables are visible SQL.
- **Acceptance:** Applying `sql/` to a new DuckDB file creates the raw fact, filing, and deliveries tables, plus named tables the later stages will fill. A test applies the SQL and checks those tables exist. Transforms stay in `.sql` files rather than only in Python.
- **Depends on:** M1-T1
- **Can run in parallel with:** M1-T2, M1-T4, M1-T6, M1-T7, M2-T1, M3-T1, M5-T1
- **Status:** done (129229b4fdf1e0e6a86c4053fd8abb35701a77a4)

### M1-T4 — Transcribe deliveries.csv

- **Goal:** Fill `data/manual/deliveries.csv` with 20 quarters transcribed from each quarter's first official Tesla investor-relations production and deliveries release.
- **Acceptance:** The file has the columns `quarter`, `production_total`, `deliveries_total`, `release_date`, and `source_url`; 20 contiguous quarters; every row's numbers taken from the first release, not a later revision; every row has a release date and a source URL. No pipeline code fetches these pages during ingest.
- **Depends on:** M1-T1
- **Can run in parallel with:** M1-T2, M1-T3, M1-T6, M1-T7, M2-T1, M3-T1, M5-T1
- **Status:** done (f28adc81e25a3e983b129faadd5140545e2d3ed7)

### M1-T5 — Check and validate deliveries

- **Goal:** Add `scripts/check_deliveries` to re-fetch each source page and confirm the transcribed numbers appear there, plus a non-network validation the pipeline can run every time.
- **Acceptance:** `scripts/check_deliveries` reports a mismatch when a saved page fixture does not contain that row's production or deliveries figure, and confirms a match when it does. Where a live page can be fetched, the script can be pointed at it. Pytest, with no network, fails a fixture that has a quarter gap, a missing source, or an implausible quarter-over-quarter change, and passes the committed CSV on those structural checks. A normal `ingest` run does not scrape the source pages.
- **Depends on:** M1-T4
- **Can run in parallel with:** M1-T2, M1-T3, M1-T6, M1-T7, M1-T8
- **Status:** done (8a069eb89a66c93bc57b47c4bb7359b3b9c56d63)

### M1-T6 — SEC ingest, cache, User-Agent, and rate limit

- **Goal:** Download Tesla's companyfacts JSON and the filing index, with a local cache, the SEC User-Agent, and the SEC rate limit.
- **Acceptance:** Tests use fixtures, not the live SEC site. The client sends `User-Agent` from `SEC_USER_AGENT` and fails closed when the variable is empty. Responses are cached under `data/cache/` and a second request for the same URL does not hit the network. The client stays at or below 10 requests per second. The companyfacts URL is `https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json`. No email address is hardcoded.
- **Depends on:** M1-T1
- **Can run in parallel with:** M1-T2, M1-T3, M1-T4, M1-T7, M2-T1, M3-T1, M5-T1
- **Status:** done (0856da8031fe686c3c58951c4fd61bd377aa473d)

### M1-T7 — Q4 derivation and year-to-date cash-flow de-cumulation

- **Goal:** Turn 10-K annual figures into Q4 and turn year-to-date 10-Q cash-flow figures into single quarters, with unit tests for both.
- **Acceptance:** `uv run pytest` (or `pytest`) passes tests where Q4 equals the annual figure minus Q1–Q3, and where a year-to-date cash-flow series de-cumulates into single quarters (Q1 unchanged, Q2 minus Q1, Q3 minus Q2). The tests cover operating cash flow and capex. Free cash flow is computed as CFO minus capex on the quarterly values.
- **Depends on:** M1-T1
- **Can run in parallel with:** M1-T2, M1-T3, M1-T4, M1-T6, M2-T1, M3-T1, M5-T1
- **Status:** done (0856da8031fe686c3c58951c4fd61bd377aa473d)

### M1-T8 — Per-filing value storage

- **Goal:** Store one value per metric, period, and filing, then assemble quarter actuals without dropping later restatements.
- **Acceptance:** A fixture with the same period in two filings produces two stored rows, each with its accession number, filing date, and filing URL. Actuals for quarter Q are the values as first reported in Q's own 10-Q, or the Q4 derivation from M1-T7 for a 10-K. A later comparative does not overwrite that first-reported row. The rows needed for "latest value as of a cutoff date" are queryable. The restatement itself is kept for the verification report in M3-T8.
- **Depends on:** M1-T2, M1-T3, M1-T6, M1-T7
- **Can run in parallel with:** M1-T5
- **Status:** done (3251c5e109cf7bd758292d7d103d90362bf0ae34)

### M1-T9 — Ingest command

- **Goal:** Load companyfacts and `deliveries.csv` into DuckDB through one ingest command, including source links and the quarterly series.
- **Acceptance:** `python -m agent ingest` (cache or fixtures, no secret printed) loads raw per-filing values, quarterly actuals, and deliveries. The database holds the last 12 reported quarters plus the earlier quarters the forecast needs as history. Deliveries validation from M1-T5 runs; the source pages are not scraped. Filing accession, filing date, and filing URL are stored for every financial value.
- **Depends on:** M1-T5, M1-T8
- **Can run in parallel with:** none
- **Status:** done (5da704bcb15846fd72b6e8775e317d70f28575ba)

### M1-T10 — Segment lines from filing XBRL instances

- **Goal:** Load the revenue and cost segment lines (automotive sales, regulatory credits, leasing, energy, services, and the segment costs) from each 10-Q and 10-K XBRL instance, because companyfacts drops the dimension members those lines need.
- **Acceptance:** Tests with a saved instance fixture, and no network, show that each segment metric in `config/xbrl_tags.json` is read from the context whose only explicit member is the configured one, for the filing's own quarter, and stored through `store_reported_facts` with the filing's accession, date, and URL. The segment lines for a filing tie to total revenue and total cost of revenue in that filing. The client uses the cached SEC client with `SEC_USER_AGENT` and the 10-requests-per-second limit. `python -m agent ingest` loads them. Without them, the base forecast has no automotive sales or total revenue, and the revenue bridge cannot run on live data.
- **Depends on:** M1-T9
- **Can run in parallel with:** M2-T10, M3-T5, M3-T6, and M5 tasks
- **Status:** done (105ccfb3215d3b030bbc94ec94c05b64181c4710)

## M2 — Model and variance

Forecast cutoff is the filing date of the previous quarter's 10-Q or 10-K. The model knows last quarter's full results and does not know this quarter's delivery report. Publish forecast-versus-actual for reported quarters only. `PUBLISH_FORWARD_FORECAST` stays `false`.

### M2-T1 — Document driver formulas and scenario percentages

- **Goal:** Write the forecast formulas and the bull, base, and bear flexes into config, with the percentages explicit.
- **Acceptance:** Config states how deliveries, automotive ASP, automotive sales revenue, regulatory credits, energy, services, gross margin, operating expenses, and capex are projected, and the bull/base/bear percentages applied to deliveries, ASP, and gross margin. A test loads the config. The choices are recorded in `docs/DECISIONS.md`. No look-ahead is described in the formulas (same-quarter-last-year and recent growth use only data before the cutoff).
- **Depends on:** M1-T1
- **Can run in parallel with:** M1-T2 through M1-T9, M3-T1, M5-T1
- **Status:** done (90a90910c6ddcbef6355b3683d6f856d6bcfd36c)

### M2-T2 — Cutoff date and no-look-ahead tests

- **Goal:** Build the forecast for quarter Q only from values that existed on the previous quarter's filing date.
- **Acceptance:** A test fails if the forecast for Q reads a filing dated after the previous quarter's filing date, or if it reads Q's own delivery or production figure. Forecast inputs are the latest stored values available on that cutoff, which may differ from first-reported actuals. The cutoff rule matches section 8.
- **Depends on:** M1-T9, M2-T1
- **Can run in parallel with:** none
- **Status:** done (159b63e7e00388a0563c8203d1de442f7bb6823f)

### M2-T3 — Base driver forecast

- **Goal:** Produce the base forecast P&L and free cash flow for each target quarter from the drivers in section 4.
- **Acceptance:** For a fixture quarter the forecast includes deliveries, automotive sales (deliveries times ASP), regulatory credits, leasing, energy, services, gross profit, operating expenses, operating income, capex, and free cash flow. The result uses only cutoff inputs. Empty history is explicit when a quarter has fewer than the documented minimum of earlier quarters (the site copy later says four).
- **Depends on:** M2-T2
- **Can run in parallel with:** none
- **Status:** done (c639f699414bda0669f7b3a20fbb3ebd24e024db)

### M2-T4 — Bull, base, and bear scenarios

- **Goal:** Flex deliveries, ASP, and gross margin by the configured percentages to produce three scenarios.
- **Acceptance:** Each target quarter gets bull, base, and bear forecasts. A test checks the scenario ordering implied by the config (the bull delivery assumption is above base, bear below, on the configured drivers) and checks that base matches M2-T3. Percentages are read from config, not hardcoded in the scenario function.
- **Depends on:** M2-T3
- **Can run in parallel with:** M2-T5, M2-T6, M2-T7, M2-T8, M2-T9
- **Status:** done (cb1ef8002daa2194f8a79b0a3d6cb8430098b1f7)

### M2-T5 — Backtest accuracy

- **Goal:** Measure absolute percent error for revenue, gross profit, and operating income on every target quarter, plus the average error.
- **Acceptance:** A test on a fixture computes absolute percent error for those three lines and the average across quarters. The published table includes quarters where the error is large. No error is dropped or clipped to look better.
- **Depends on:** M2-T3
- **Can run in parallel with:** M2-T4, M2-T6, M2-T7, M2-T8, M2-T9
- **Status:** done (71192a1da7659c1ab05acc6839cafa7f223f4b4e)

### M2-T6 — Revenue bridge

- **Goal:** Build the revenue waterfall from forecast to actual so the six driver bars sum exactly to the total revenue variance.
- **Acceptance:** A test asserts exact equality of volume (change in deliveries times forecast ASP) + price/mix (change in ASP times actual deliveries) + regulatory credits + leasing + energy + services and other with total revenue variance. ASP is automotive sales revenue divided by total deliveries. Each bar is labeled favorable or unfavorable. The leasing limitation (leased units sit inside deliveries) is recorded for the methods copy in M5-T13.
- **Depends on:** M2-T3
- **Can run in parallel with:** M2-T4, M2-T5, M2-T7, M2-T8, M2-T9
- **Status:** done (69b9f4eb7a4be1033000e9076f25c1b58d205257)

### M2-T7 — Gross profit bridge

- **Goal:** Split gross-profit variance into volume/revenue and margin-rate effects that sum exactly to the total.
- **Acceptance:** For each segment shown in the filings, a test covers the volume/revenue effect (change in segment revenue times forecast segment margin) and the margin-rate effect (change in segment margin percent times actual segment revenue). Bars group into automotive, energy, and services and other. Their sum equals gross profit variance exactly. Each bar is labeled favorable or unfavorable. Where segment margin is not reported, the total-margin path from section 4 is used and documented.
- **Depends on:** M2-T3
- **Can run in parallel with:** M2-T4, M2-T5, M2-T6, M2-T8, M2-T9
- **Status:** done (306a9a85eda536322f241d00b3a185393c7c797d)

### M2-T8 — Operating income bridge

- **Goal:** Bridge operating income from gross profit variance through operating expenses, with an exact sum.
- **Acceptance:** Bars are gross profit variance, R&D, SG&A, and restructuring or other opex when present. A higher cost is unfavorable (sign flip). A test asserts the bars sum exactly to operating income variance, including a fixture where R&D or SG&A increased. Each bar is labeled favorable or unfavorable.
- **Depends on:** M2-T3
- **Can run in parallel with:** M2-T4, M2-T5, M2-T6, M2-T7, M2-T9
- **Status:** done (5960dc9803d14f8efc1d65710510e3533b22f25d)

### M2-T9 — Free cash flow bridge

- **Goal:** Explain free-cash-flow variance with operating cash flow and capex, summing exactly.
- **Acceptance:** The two bars are operating cash flow and capex. Higher capex is unfavorable. A test asserts an exact sum to free cash flow variance (free cash flow is CFO minus capex) and checks the unfavorable label when capex rose.
- **Depends on:** M2-T3
- **Can run in parallel with:** M2-T4, M2-T5, M2-T6, M2-T7, M2-T8
- **Status:** done (cd327ed5ad0273cd502c03aadc1aa86231a0d084)

### M2-T10 — Model and variance commands

- **Goal:** Expose the forecast, scenarios, backtest, and bridges as `model` and `variance` commands.
- **Acceptance:** `python -m agent model` and `python -m agent variance` run against the local database (or a fixture database in CI) and write the base forecast, three scenarios, backtest table, and four bridges. No forward quarter is marked for publication while `PUBLISH_FORWARD_FORECAST=false`.
- **Depends on:** M2-T4, M2-T5, M2-T6, M2-T7, M2-T8, M2-T9
- **Can run in parallel with:** none
- **Status:** done (6d470ce98a51078ae94ab45cc8fddfb1102f57ad)

## M3 — Narration and verification

The model sees computed tables only. It never sees raw filings. Prompts live in `prompts/` as versioned files. Temperature stays low. A full run should cost roughly a dollar or less.

### M3-T1 — Prompts, question set, and claim schema

- **Goal:** Add versioned prompt files, the ten fixed questions, and the structured claim schema the verifier will check.
- **Acceptance:** Prompt files under `prompts/` have a version the cache can hash. The ten questions from section 4 are present, and questions 7 and 8 are specified to use the backtest across all 12 quarters. Pydantic models require a memo, answers, and claim objects `{metric, period, value, unit, sentence_ref}`. `OPENAI_MODEL` is read from the environment; the default is a current GPT model that supports structured JSON outputs, chosen from OpenAI's docs at build time and recorded in `docs/DECISIONS.md`.
- **Depends on:** M1-T1
- **Can run in parallel with:** M1-T2 through M1-T9, M2-T1, M5-T1
- **Status:** done (8b9d6f1d0b6d49438adadc60f59ef3708701090b)

### M3-T2 — Narrate memos and the latest-quarter Q&A

- **Goal:** Generate a variance memo for each of the 12 published quarters and the Q&A set for the latest quarter only.
- **Acceptance:** A test with a mocked OpenAI client returns structured JSON: a memo of about 150–250 words and answers of about 60–120 words. Claims accompany every number the text mentions. Twelve memos are produced and only the latest quarter gets the ten answers. The client is given the computed tables for that quarter, not raw filings. Questions 7 and 8 receive the backtest table.
- **Depends on:** M2-T10, M3-T1
- **Can run in parallel with:** M3-T5, M3-T6 if those have not already landed
- **Status:** done (c956d48173c847beb2a0e8aae2878b16ebc7926e)

### M3-T3 — Narrative cache and force flag

- **Goal:** Reuse a memo or answer set when its input tables, prompt version, and model are unchanged.
- **Acceptance:** A test runs narration twice against the same tables and shows the second run does not call the API. Changing the table hash, the prompt version, or the model misses the cache. `--force` regenerates even on a hit. Cached text is the already-verified text.
- **Depends on:** M3-T2
- **Can run in parallel with:** M3-T4
- **Status:** todo

### M3-T4 — Token and cost logging

- **Goal:** Log token usage and estimated cost on every narration run.
- **Acceptance:** A test with mock token counts writes the model name, input tokens, output tokens, and estimated dollar cost. The logger never prints `OPENAI_API_KEY` or `SEC_USER_AGENT`. The estimate is available for the publish metadata in M4-T1.
- **Depends on:** M3-T2
- **Can run in parallel with:** M3-T3
- **Status:** todo

### M3-T5 — Verifier

- **Goal:** Check every claim against the database in code, with the section 4 tolerances.
- **Acceptance:** Tests show a deliberately wrong number is flagged with the expected value, unit strings normalize (so 1,500,000,000 and $1.5 billion can match), percentages use a tolerance of ±0.1 percentage points, currency uses ±0.5%, and unit counts must match exactly. An unknown metric is `unsupported`. Results are only `verified`, `flagged`, or `unsupported`. The verifier does not rewrite the sentence.
- **Depends on:** M1-T9, M3-T1
- **Can run in parallel with:** M2-T2 through M2-T10, M3-T2, M3-T6
- **Status:** done (f2d8faf8fb531cd328b5d50cfe1a1f57f2d820f5)

### M3-T6 — Keyword guard

- **Goal:** Reject buy/sell language and price targets in the memo and answers.
- **Acceptance:** A test flags text that contains buy/sell instructions or a price target, and passes a memo that only discusses variances and metrics. The guard is a keyword check, not another model call.
- **Depends on:** M3-T1
- **Can run in parallel with:** M3-T2, M3-T5
- **Status:** done (26feabd02059226cd348de9e7b7fee5bc83d302d)

### M3-T7 — Re-ask once

- **Goal:** When any claim is flagged or unsupported, ask the model once with the errors, and keep the flags if they remain.
- **Acceptance:** A mocked test where the first response is wrong and the second is right ends verified. A test where the second response is still wrong stays flagged or unsupported and is still published. No test path silently replaces the model's number with the database number.
- **Depends on:** M3-T2, M3-T5
- **Can run in parallel with:** M3-T3, M3-T4
- **Status:** todo

### M3-T8 — Verification report and narrate/verify commands

- **Goal:** Write a verification report per quarter and expose `narrate` and `verify` as commands.
- **Acceptance:** `python -m agent narrate` and `python -m agent verify` run on fixtures. Each quarter gets a report with verified, flagged, and unsupported counts, plus a note when a later filing restated a period that actuals still hold at the first-reported value (see M1-T8). The keyword-guard result is in the report.
- **Depends on:** M3-T3, M3-T4, M3-T6, M3-T7
- **Can run in parallel with:** none
- **Status:** todo

## M4 — Publish and automation

The site reads committed JSON only. Visitors never call the API. Do not enable GitHub Pages or change repo settings in this milestone (see `docs/DECISIONS.md`).

### M4-T1 — Publish JSON and schema test

- **Goal:** Write the site's versioned JSON into `site/public/data/` and lock the shape with a schema test.
- **Acceptance:** Publish writes quarters, forecasts, scenarios, bridges, memos, Q&A, claims, verification results, backtest accuracy, and run metadata (run time, duration, model, tokens, estimated cost, data as-of date). `pytest` fails if the output does not match the schema the frontend imports. Secrets do not appear in the JSON or in the command output. With `PUBLISH_FORWARD_FORECAST=false`, no unpublished forward quarter is included as a published forecast-versus-actual.
- **Depends on:** M2-T10, M3-T8
- **Can run in parallel with:** none
- **Status:** done (eca07f3ca1e57e1865ccb871d309bc806612eb2f)

### M4-T2 — Single run command

- **Goal:** Run the whole pipeline with one command, and keep each stage runnable on its own.
- **Acceptance:** `python -m agent run` executes ingest, model, variance, narrate, verify, and publish in order. `python -m agent ingest`, `model`, `variance`, `narrate`, `verify`, and `publish` each still run alone. A fixture-mode test completes without a live API call. A `make run` target may call the same command; if it does, it is documented.
- **Depends on:** M1-T9, M2-T10, M3-T8, M4-T1
- **Can run in parallel with:** M5 sections that only need the schema, once M4-T1 has merged
- **Status:** todo

### M4-T3 — refresh.yml

- **Goal:** Add a manual workflow that runs the pipeline from GitHub Actions secrets and commits the updated JSON.
- **Acceptance:** `.github/workflows/refresh.yml` supports `workflow_dispatch`. Any schedule is present only if it is disabled by default. The workflow reads `OPENAI_API_KEY` and `SEC_USER_AGENT` from secrets and does not echo them. It commits updated data so `deploy.yml` can run afterward. The workflow file contains no secret values. Repo settings are not changed.
- **Depends on:** M4-T2
- **Can run in parallel with:** M4-T4, M5-T3 through M5-T14
- **Status:** in progress (Claude Code, 2026-11-05)

### M4-T4 — deploy.yml

- **Goal:** Add the workflow that builds the static site on push to `main`.
- **Acceptance:** `.github/workflows/deploy.yml` builds the site on push to `main` and is the Pages deploy workflow. YAML is valid. The workflow does not print secrets. Committing the file does not, by itself, enable GitHub Pages or change repo visibility; if the GitHub UI or API would need a settings change, stop and leave the question in `docs/PROGRESS.md`.
- **Depends on:** M5-T1
- **Can run in parallel with:** M4-T3, M5-T2 and later site tasks
- **Status:** done (50de24b9c39d0c4333ee9bdc16bec68e73865df6)

## M5 — Dashboard

One static page: Vite, React, and TypeScript, data from the committed JSON, latest quarter by default. Charts are custom SVG with D3 scales. The wireframe numbers in section 6 are placeholders, not data to hardcode.

Design constraints for every M5 task, from section 6:

- Palette: Paper `#F4F6F8`, Ink `#18212B`, Ledger rule `#CBD3DC`, Forecast cobalt `#2448C8`, Tied green `#0E7A5A`, Flag amber `#A85B00`. White `#FFFFFF` only for raised table and memo surfaces. No Tesla red and nothing close to it.
- Dark mode uses the same hues (Paper `#121820`, Ink `#E6EBF0`, cobalt, green, and amber lightened enough for WCAG AA). Record the final dark hex values in `docs/DECISIONS.md`.
- IBM Plex Sans for the interface, tables, and numbers, with `font-variant-numeric: tabular-nums` wherever numbers appear. Source Serif 4 only for the memo and Q&A, with line-height about 1.55.
- Sentence case, active voice, no hype words, no emoji, no all-caps labels, no tracked-out eyebrows, no monospace small labels, no arrow stuck on a link.
- Variance meaning uses a sign and the words favorable or unfavorable, not color alone.
- Visible cobalt focus ring. Respect `prefers-reduced-motion`.
- Layout: left-aligned, content max about 1120px, prose about 680px, sections separated by whitespace and a ledger rule. No grid of identical cards, no gradient washes, no neon-on-black, no cream-and-terracotta.
- Empty and error states say what is missing and what to do.

### M5-T1 — Site scaffold, type, and color

- **Goal:** Scaffold the Vite, React, and TypeScript app with the section 6 palette, fonts, and GitHub Pages base path.
- **Acceptance:** `npm run build` (or the package manager the repo actually uses, recorded in `docs/DECISIONS.md`) succeeds. `base` is set for the repo name. Fonts and color tokens match the constraints above, including a dark mode. Tabular numbers are on for figures.
- **Depends on:** M1-T1
- **Can run in parallel with:** M1-T2 through M1-T9, M2, M3
- **Status:** done (f3a797ed4f48512ae53791fd0e25a0fae291affd)

### M5-T2 — Shell, quarter picker, and disclaimer

- **Goal:** Build the page shell a hiring manager scrolls, with the latest quarter selected and the required footer.
- **Acceptance:** The latest quarter is selected by default and a picker can select an earlier one. The footer text is exactly: "Independent analysis built from Tesla's public SEC filings and investor-relations releases. Not affiliated with or endorsed by Tesla, Inc. Not investment advice." Header reads "Tesla FP&A Agent". An empty state such as "No forecast for this quarter: it needs four earlier quarters of history." renders when the fixture says so. Layout matches the widths and ledger-rule rules above.
- **Depends on:** M5-T1
- **Can run in parallel with:** M4-T4
- **Status:** done (e81cc88aed6b085284c2e90cadc3841148f6794d)

### M5-T3 — Tick marks and legend

- **Goal:** Render every AI-written figure as a number plus a keyboard-focusable tick.
- **Acceptance:** Verified ticks, flagged ticks, and unsupported ticks match section 6 (green tick, amber flag, amber-outline question mark) and have accessible names. Hover or focus shows the source line, filing, and result; a flagged tick shows the expected value; activating a tied tick opens the source filing. A legend sits with the memo. A component test covers all three states.
- **Depends on:** M5-T2, M4-T1
- **Can run in parallel with:** M5-T4, M5-T6, M5-T8, M5-T10, M5-T12, M5-T13, M5-T14
- **Status:** todo

### M5-T4 — Hero revenue bridge

- **Goal:** Make the latest quarter's revenue waterfall the centerpiece of the page.
- **Acceptance:** The headline is exactly "Tesla's quarter, forecast and explained by an agent, checked against the filings." Under it: the quarter, forecast vs actual revenue, and the variance in dollars and percent. The custom SVG waterfall is forecast revenue, volume, price/mix, credits, leasing, energy, services and other, actual revenue. On first load the bars draw in sequence in about 1.2 seconds, then the seal's ticks appear; `prefers-reduced-motion` shows the final state immediately. A visually hidden table lists the bridge values. At 375px the bridge scrolls horizontally or switches to a vertical bridge.
- **Depends on:** M5-T2, M4-T1
- **Can run in parallel with:** M5-T3, M5-T6, M5-T8, M5-T10, M5-T12, M5-T13, M5-T14
- **Status:** done (38bff51b4055e5687e2718381531b36a53221102)

### M5-T5 — Verification seal

- **Goal:** Show how many commentary figures tie to the filing, and link that seal to the verification section.
- **Acceptance:** The seal states the verified count out of the total, including when some are flagged (flagged figures stay visible). It links to the verification or methods section. The count comes from the published verification results, not a hardcoded "41 of 41".
- **Depends on:** M5-T3, M5-T4
- **Can run in parallel with:** M5-T6, M5-T7, M5-T8
- **Status:** todo

### M5-T6 — How the agent ran

- **Goal:** Show the six pipeline stages with last-run durations, time, cost, and model.
- **Acceptance:** The sequence is ingest, load, forecast, explain, verify, publish, each with its duration from run metadata. The page also shows last run date, total run time, AI cost, and model. Values come from the published metadata. Nothing in this section animates on its own.
- **Depends on:** M5-T2, M4-T1
- **Can run in parallel with:** M5-T3, M5-T4, M5-T8, M5-T10, M5-T12, M5-T13, M5-T14
- **Status:** done (42a9a1261437ef1917f4661be14b6cd7e34ddcd6)

### M5-T7 — Analyst memo

- **Goal:** Present the AI variance memo as a memo, with a tick on every figure.
- **Acceptance:** The selected quarter's memo renders in Source Serif 4 inside the prose column. Every figure uses the M5-T3 tick. Flagged figures are visibly marked. Switching quarters loads that quarter's memo. The legend from M5-T3 is visible here.
- **Depends on:** M5-T3
- **Can run in parallel with:** M5-T5, M5-T11
- **Status:** todo

### M5-T8 — Forecast table and scenario toggle

- **Goal:** Show the P&L against forecast and let a visitor switch bull, base, and bear in the browser.
- **Acceptance:** The table columns are line, Forecast, Actual, Variance $, and Variance %. Favorable and unfavorable cells include a plus or minus and the word, not color alone. The bull/base/bear control recomputes forecast columns in the browser from the published drivers. The table scrolls horizontally at narrow widths with the first column pinned. User-triggered scenario changes may animate briefly.
- **Depends on:** M5-T2, M4-T1
- **Can run in parallel with:** M5-T3, M5-T4, M5-T6, M5-T10, M5-T12, M5-T13, M5-T14
- **Status:** done (4a5c49a8edf73fbb94f0e7585b7158bea9eb7582)

### M5-T9 — TypeScript and Python scenario parity

- **Goal:** Prove the browser scenario math matches the Python model on a shared fixture.
- **Acceptance:** One fixture of drivers and bull/base/bear outputs is produced by the Python model. A TypeScript test recomputes those forecast columns and matches the Python output exactly on the agreed rounding. Both `pytest` and the site test command pass on that fixture. The fixture is committed.
- **Depends on:** M2-T4, M5-T8
- **Can run in parallel with:** M5-T10, M5-T11, M5-T12
- **Status:** todo

### M5-T10 — Twelve-quarter forecast chart

- **Goal:** Chart revenue, forecast versus actual, across the 12 published quarters.
- **Acceptance:** A custom SVG line chart (D3 scales, not a default chart-library theme) plots forecast and actual revenue for the published quarters. A text alternative exposes the same values. The selected quarter is identifiable without color alone.
- **Depends on:** M5-T2, M4-T1
- **Can run in parallel with:** M5-T3, M5-T4, M5-T6, M5-T8, M5-T12, M5-T13, M5-T14
- **Status:** todo

### M5-T11 — Ask the analyst

- **Goal:** List the ten pre-answered questions, with ticks, and keep older quarters pointed at the latest Q&A.
- **Acceptance:** The latest quarter expands each of the ten questions to its answer, each with tick-marked numbers and a source link. When an earlier quarter is selected, the section says the Q&A covers the latest quarter only and offers a control that switches to it. Answers are the published JSON, not a live request.
- **Depends on:** M5-T3
- **Can run in parallel with:** M5-T7, M5-T9
- **Status:** todo

### M5-T12 — Model accuracy

- **Goal:** Show backtest error by quarter and the average, including the misses.
- **Acceptance:** The section shows absolute percent error by quarter for revenue, gross profit, and operating income, plus the average. A fixture quarter with a large error is displayed, not hidden. Wording stays plain.
- **Depends on:** M5-T2, M4-T1
- **Can run in parallel with:** M5-T3, M5-T4, M5-T6, M5-T8, M5-T10, M5-T13, M5-T14
- **Status:** done (d9e79b3169073d65726f241045fd76ced18d3e40)

### M5-T13 — How it works and how it is controlled

- **Goal:** Explain the pipeline, what the code does versus the model, and the limits of the data.
- **Acceptance:** A simple inline SVG diagram (not a screenshot of code) shows the stages. The copy covers verification rules, public SEC and investor-relations sources only, the leasing limitation on the revenue bridge, and that visitors do not call the model. No Tesla logo, wordmark, or product image.
- **Depends on:** M5-T2
- **Can run in parallel with:** M5-T3, M5-T4, M5-T6, M5-T8, M5-T10, M5-T12, M5-T14
- **Status:** done (23b6ee0368dd2a5732f32121f3d27cfc48dba1f7)

### M5-T14 — About

- **Goal:** Add Jacob's credit and the links he will fill in later.
- **Acceptance:** The about copy is "Built by Jacob Kambour, MS Finance & Analytics, Santa Clara University." GitHub, LinkedIn, and résumé URLs are read from `site/src/config.ts`. Placeholders are obvious and empty of guessed URLs. The page still renders when they are blank.
- **Depends on:** M5-T2
- **Can run in parallel with:** M5-T3, M5-T4, M5-T6, M5-T8, M5-T10, M5-T12, M5-T13
- **Status:** done (3961ba389d9d3048a6f9a6667da8ef6739edd712)

### M5-T15 — Accessibility and Lighthouse

- **Goal:** Meet the section 6 quality floor on the built site.
- **Acceptance:** Keyboard focus is visible on interactive elements, including ticks, the quarter picker, and the scenario control. Text and chart elements meet WCAG AA in light and dark mode. Lighthouse accessibility is at least 95 and performance is at least 90 on the production build. The 375px layout still reaches every section, with tables scrolling horizontally and the first column pinned. Record the Lighthouse scores in `docs/PROGRESS.md`.
- **Depends on:** M5-T4, M5-T5, M5-T6, M5-T7, M5-T8, M5-T9, M5-T10, M5-T11, M5-T12, M5-T13, M5-T14
- **Can run in parallel with:** none
- **Status:** todo

## M6 — README, polish, and launch

Section 10 is the definition of done. Do not make the repo public or enable Pages while closing these tasks.

### M6-T1 — README case study

- **Goal:** Replace the stub README with a case study a hiring manager can read on its own.
- **Acceptance:** `README.md` has the nine parts from section 7: the problem statement, a place for the screenshot or GIF and the live link, the six pipeline steps, how accuracy is controlled and the backtest, an architecture diagram, run-it-yourself setup including `.env` and one command and cost per run, limitations and assumptions (public data only, simple driver models, manual delivery data), the same disclaimer as the site, and the credit line "Designed and built by Jacob Kambour." If Pages is still not enabled, the live link is described as waiting on Jacob rather than invented.
- **Depends on:** M4-T2, M5-T15
- **Can run in parallel with:** M6-T3
- **Status:** todo

### M6-T2 — Dashboard screenshot or GIF

- **Goal:** Add a still or short GIF of the dashboard to the README.
- **Acceptance:** The README image shows the real page (hero bridge and ticks), not the wireframe placeholders. The file is committed and renders on GitHub. No API key is visible in the capture.
- **Depends on:** M5-T15, M6-T1
- **Can run in parallel with:** M6-T3, M6-T4
- **Status:** todo

### M6-T3 — Fresh-clone run

- **Goal:** Prove `python -m agent run` works from a fresh clone with only `.env` filled in.
- **Acceptance:** On a clean checkout, with `.env` set and caches empty, `python -m agent run` finishes in a few minutes and writes `site/public/data/`. `PUBLISH_FORWARD_FORECAST` is false and no forward quarter is published. Token and cost logging stay within the roughly-one-dollar target, and the cost is recorded in `docs/PROGRESS.md`. If the env vars are not available to the agent, mark this task `blocked (needs .env on the machine running the pipeline)` instead of inventing values.
- **Depends on:** M4-T2
- **Can run in parallel with:** M6-T1, M6-T2, M6-T4
- **Status:** todo

### M6-T4 — Anti-goal sweep

- **Goal:** Confirm the repo and the built site stay independent, public-data-only, and free of a live chatbot.
- **Acceptance:** A recorded search finds no Tesla logo, wordmark, brand font, brand red, or product photo, and no non-public source. The built site contains no OpenAI client and no path that calls the API from the browser. Results are written in `docs/PROGRESS.md`.
- **Depends on:** M5-T15, M6-T1
- **Can run in parallel with:** M6-T2, M6-T3
- **Status:** todo

### M6-T5 — Git history secret scan

- **Goal:** Search the full git history and the built site for secrets before any public launch.
- **Acceptance:** `git log -p --all` and the built site directory show no API keys, no filled-in `OPENAI_API_KEY` or `SEC_USER_AGENT` values, and no `sk-` key material. The commands and the clean result are recorded in `docs/PROGRESS.md`. A hit stops the launch tasks until the secret is removed from history and Jacob has rotated it.
- **Depends on:** M6-T1, M6-T2, M6-T3, M6-T4, and every M1–M5 task
- **Can run in parallel with:** none
- **Status:** todo

### M6-T6 — Launch closeout

- **Goal:** Mark the plan complete and leave Jacob a final handoff that does not change repo settings.
- **Acceptance:** Every earlier task is `done` or explicitly `blocked` with a Jacob question. `docs/PROGRESS.md` has a final entry that states the project is complete and lists what is still his: spot-check `deliveries.csv`, fill in the links in `site/src/config.ts`, check employer policy, and decide whether to make the repo public and enable Pages. Section 10's checklist is addressed in that entry. Re-run the M6-T5 scan if this task changes anything besides the handoff docs. Do not make the repo public, enable Pages, or change repo settings.
- **Depends on:** M6-T5
- **Can run in parallel with:** none
- **Status:** todo
