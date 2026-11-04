# Decisions

Newest entry at the top. Every non-obvious choice goes here: the decision, the alternatives considered, and why. A deviation from `docs/BRIEF.md` is logged here first. The brief is not edited to hide an override.

## 2026-11-04 — DuckDB tables, and the as-of query in SQL

**Decision:** `sql/` is the database. `agent/schema.py` runs those files in name order and does not contain the table definitions. `fact` stores one row per metric, period, and accession, so a comparative from a later filing does not replace the earlier row. `filing` holds the form, the filing's own period end, the filing date, and the filing URL. `fact.accession` references `filing`. The view `fact_with_source` joins them. The macro `fact_as_of(cutoff_date)` returns the latest row whose filing date is on or before that cutoff. `quarter_actual`, `forecast`, `bridge`, and `backtest` are created empty for M1-T8 and M2.

Money and forecast amounts are `DECIMAL(24, 4)`. A whole-dollar filing amount stays exact, and a later ratio does too. Delivery counts stay `BIGINT`. Bull, base, and bear are rows in `forecast`, distinguished by `scenario`.

**Alternatives considered:** An as-of query written only in Python would hide the transform the task asks to keep in SQL. One table for facts and forecasts would share a key that does not fit restatements, scenarios, and bridges. Deleting the older fact when a comparative arrives would drop the restatement M1-T8 has to keep.

## 2026-11-04 — XBRL tags, searched in order

**Decision:** `config/xbrl_tags.json`, loaded by `agent/xbrl_map.py`, is the section 4 tag map. For one filing and one duration, walk that metric's tags in order and use the first fact whose only dimension is the listed member. A tag with no member matches a fact with no dimensions. If none match, leave the metric blank for that period. Do not sum other lines to fill it. `load_xbrl_map()` rejects a required metric that has no tag.

Automotive sales is the line that changed. The 2021 10-K (accession 0000950170-22-000796) reports it as `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` with member `us-gaap:AutomobilesMember` (44,125,000,000 for 2021). The 2022 10-Qs and the 2022 10-K (accession 0000950170-23-001409) report `tsla:AutomotiveSalesRevenue` on member `tsla:AutomotiveRevenuesMember` (67,210,000,000 for 2022). The 2023 10-K, the 2024 10-K (accession 0001628280-25-003063), and the Q3 2026 10-Q (accession 0001628280-26-066775) report the same us-gaap concept with member `tsla:AutomotiveSalesMember` (72,480,000,000 for 2024). Credits and leasing follow the same split: an extension concept in 2022, and a product-or-service member otherwise. In each of those filings the three automotive lines add up to automotive revenue.

**Alternatives considered:** One current tag, `tsla:AutomotiveSalesMember`, would miss 2021 and every 2022 quarter. Reading companyfacts only would miss every segment line: the feed pulled on 2026-11-04 has no `tsla` concepts and no dimensions. Summing members when a total is absent would hide a filing that dropped a line. `tsla:AutomotiveSales` looks like the sales line but is a debit in the 2022 schema (49,599,000,000), equal to neither sales revenue nor automotive cost.

Energy is the parent member `tsla:EnergyGenerationAndStorageMember`, because that member equals energy sales plus energy leasing. Segment cost tries `us-gaap:CostOfRevenue` first. The 2022 10-K has no energy or services member on that concept; `us-gaap:CostOfGoodsAndServicesSold` is the fallback there, and those amounts plus automotive cost equal total cost of revenue. The 2021 10-K tags both concepts with different amounts, so the fallback must stay second. Regulatory-credit cost is not tagged in the filings checked here, so that series is `not_reported`. Free cash flow has no tag; it stays CFO minus capex after `M1-T7`. Deliveries and production stay in the CSV.

## 2026-11-04 — Deliveries structural checks, and page checks stay opt-in

**Decision:** `agent.deliveries.validate_deliveries` is the no-network check. It fails a quarter label that skips a quarter, a row whose `source_url` is blank or not an `http`/`https` URL, and a quarter-over-quarter move in production or deliveries strictly larger than 50%. The committed CSV passes. `scripts/check_deliveries` always runs that check. It reads saved HTML only with `--pages-dir`, and it GETs `source_url` only with `--fetch`. A normal ingest path does not exist yet and must call `validate_deliveries` rather than `fetch_source_page`.

The 50% line is above the largest move in the transcribed series: production rose 41.5% from 2022-Q2 (258,580) to 2022-Q3 (365,923). A move of half the prior quarter, or more, is the implausible case the test fixture uses.

Page text matching strips tags, keeps inline tags from splitting a number (`433,3<b>7</b>1` still counts as 433,371), and refuses a longer grouped number (`1,433,371` is not 433,371).

**Why:** M1-T5 asks for a re-fetch tool and for a check the pipeline can run every time without scraping. M1-T9 will call the structural check during ingest and must not scrape the release pages.

**Live fetch on this date:** `scripts/check_deliveries --fetch` got HTTP 403 for all 20 `source_url` values. Headless Chrome got Akamai "Access Denied" for the same host. No response body was available, so no total was compared and no CSV cell was changed. This is a fetch failure, not a mismatch. Jacob should run `scripts/check_deliveries --fetch` from a network that can open `https://ir.tesla.com`.

**Alternatives considered:**

- A 40% limit. Rejected because the committed 2022-Q3 production rebound is 41.5%, and the file has to pass.
- Fetching inside `validate_deliveries` or during ingest. Rejected because M1-T5 says a normal ingest run does not scrape the source pages.
- Treating the same-day Form 8-K exhibit as a successful check of `source_url`. Rejected because the column points at the investor-relations page. The exhibit was the M1-T4 transcription check. A 403 is not a match.

**What this means for later tasks:** M1-T9 calls `validate_deliveries` and does not pass `--fetch`. Saved-page checks stay in `scripts/check_deliveries`. Do not edit a deliveries total because a fetch was blocked.

## 2026-11-04 — Narration prompts and the default model

`OPENAI_MODEL` defaults to `gpt-6-luna` when the variable is missing or blank. Rechecked on 2026-11-04: `https://developers.openai.com/api/docs/models/gpt-6-luna` lists the model id `gpt-6-luna` and lists `structured_outputs` under supported features. The structured-outputs guide says new projects can start with `gpt-6-astra`. Astra's model page lists the same feature, at $10 per million input tokens and $50 per million output tokens. Luna's page prices text at $0.10 per million input tokens and $0.50 per million output tokens. This job is twelve short memos plus ten short answers, so Luna stays inside the dollar limit in section 6. Set `OPENAI_MODEL` to `gpt-6-astra` if a later run needs the flagship. `.env.example` stays blank; the code supplies the default.

Prompt files live in `prompts/`. `manifest.json` holds version `2026-11-04.1` and temperature `0.2`. The loader also hashes the three prompt files. The cache material is the version plus that hash, so an edit that forgets to bump the version still misses. Questions 7 and 8 are the only ones flagged `uses_backtest`, and their text says to use all 12 published quarters. The response schema requires `memo`, `answers`, and claim objects with `metric`, `period`, `value`, `unit`, and `sentence_ref`.

## 2026-11-04 — Forecast formulas and scenario flexes

**Decision:** `config/forecast.json`, loaded by `agent/forecast_config.py`, is the forecast specification. The cutoff is the previous quarter's filing date. Inputs are the latest stored values available on that date. A numeric forecast needs four earlier quarters, which is the number the site copy will use. Every driver lists the relative quarters it reads, and the loader rejects an offset of zero or a later quarter.

Deliveries are the same quarter last year times recent year-over-year growth: `D(Q-4) * (1 + g)`, with `g = D(Q-1) / D(Q-5) - 1`. If `D(Q-5)` is missing or zero, `g` is 0, so the forecast is the same quarter last year rather than a number taken from the target quarter. Automotive ASP is the average of automotive sales revenue divided by deliveries over the prior four quarters. Automotive sales revenue is forecast deliveries times forecast ASP. Regulatory credits, leasing, energy, services, and operating expenses are the prior-four-quarter average times the same kind of year-over-year growth. Gross margin is the prior-four-quarter average, by segment when that margin is in the cutoff history, otherwise the total margin, with no growth term. Capex is the prior-four-quarter average of positive purchases, with no growth term. Operating cash flow uses that same average so free cash flow can be CFO minus capex. R&D and SG&A, when present, use the operating-expense formula.

Scenarios flex only deliveries, ASP, and gross margin. Base is unflexed. Bull is deliveries +10 percent, ASP +5 percent, and gross margin +100 basis points (1 percentage point). Bear is the same amounts with the sign reversed. Credits, leasing, energy, services, operating expenses, capex, and operating cash flow stay at the base forecast. These are case-study assumptions, not a view on the company.

**Why:** Section 4 and section 9 leave the exact formulas to the builder as long as they stay inside the driver framework, are documented, and do not look ahead. Section 8 says the cutoff is the previous quarter's filing date, so the target quarter's delivery report is excluded. M2-T1 requires the percentages in config and a test that loads them. M2-T4 will read those percentages instead of hardcoding them.

**Alternatives considered:**

- A trailing growth rate that uses only four quarters, such as `D(Q-1) / D(Q-4)`. Rejected because the brief's example is year-over-year growth, which compares a quarter with the quarter a year earlier.
- Refusing a forecast until five earlier quarters exist. Rejected because the site copy is specified as four. The missing year-ago growth rate becomes zero instead of borrowing the target quarter.
- Flexing gross margin by 10 percent of itself. Rejected because a percent of an 18 percent margin is easy to misread. Basis points are an absolute margin move.
- Flexing every revenue line. Rejected because section 4 names deliveries, ASP, and gross margin as the scenario drivers.
- Projecting free cash flow as its own trend. Rejected because free cash flow is defined as CFO minus capex. CFO is the extra series that makes that identity work.
- Leaving leasing out of the config. Rejected because the revenue bridge treats it as its own bar, and the forecast has to say where that bar's forecast comes from.

**What this means for later tasks:** M2-T3 should execute this file and should treat fewer than four earlier quarters as an empty forecast. It must not read the target quarter's deliveries or a filing dated after the cutoff. M2-T4 should import the scenario integers from this config. Do not treat the flexes as guidance.

## 2026-11-04 — SEC client, filing index, and quarter derivation

**Decision:** `agent/sec.py` downloads two documents for CIK 0001318605. Companyfacts is `https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json`. The filing index is `https://data.sec.gov/submissions/CIK0001318605.json`. The client reads `SEC_USER_AGENT` at the moment it builds a request and sends that string as the `User-Agent` header. An empty or blank value raises `MissingUserAgentError` before any request. No email address is written in the client, the tests, or this entry.

Responses are stored as raw bytes under `data/cache/`, which is git-ignored. The file name is the SHA-256 of the URL. A second `get` of the same URL reads that file and does not call the transport. A failed request is not cached. Network calls are serialized and spaced at least 100ms apart, which is 10 requests per second and not more. A cache hit does not count toward that limit.

`agent/quarters.py` is the quarter math M1-T8 will call. `derive_q4` is `annual - q1 - q2 - q3` for figures that are already single quarters (income-statement lines). `decumulate_ytd` turns 10-Q cash-flow year-to-date figures into single quarters: Q1 unchanged, Q2 minus Q1, Q3 minus Q2. Q4 of a cash-flow line is the annual figure minus those three single quarters. Free cash flow is quarterly CFO minus quarterly capex. Capex here is the positive purchases amount, matching the brief's "CFO − capex". A negative single quarter is kept. These functions do not fetch.

`data/manual/deliveries.csv` is unchanged. M1-T4 owns that file.

**Why:** Section 2 requires the companyfacts API, the filing index, the User-Agent from the environment, a local cache, and at most 10 SEC requests per second. M1-T6 says tests use fixtures rather than the live site. The submissions JSON is the filing index that carries accession numbers, form types, and filing dates for the 10-Q and 10-K links. Section 4 says 10-K figures are annual, so Q4 is annual minus Q1–Q3, and 10-Q cash-flow lines are year-to-date and must be de-cumulated. Free cash flow is computed on the quarterly values, not on the year-to-date totals.

**Alternatives considered:**

- Parse companyfacts in this task. Rejected because M1-T8 owns per-filing storage. This task only fetches and derives.
- Use the HTML EDGAR browse page as the filing index. Rejected because the submissions JSON is the same index, it is one cacheable document, and it does not need scraping.
- Pace at fewer than 10 requests per second. Rejected because the acceptance check is "at or below 10", and 100ms spacing meets that without adding delay the limit does not require.
- De-cumulate income-statement lines the same way as cash flow. Rejected because a 10-Q income statement is already one quarter. Running it through year-to-date math would double-count.
- Treat capex as a negative cash outflow and add it to CFO. Rejected because the brief defines free cash flow as CFO minus capex, and the XBRL purchases concept is a positive amount. The caller passes that positive amount.
- Edit `deliveries.csv` while adding this client. Rejected because M1-T4 already transcribed it.

**What this means for later tasks:** M1-T8 should call `SecClient.companyfacts` and `SecClient.filing_index`, then `derive_q4` for income-statement Q4 and `decumulate_ytd` plus `derive_q4` for cash-flow Q4. Free cash flow comes from `quarterly_free_cash_flow` after those single quarters exist. Ingest must not log `SEC_USER_AGENT`. The live client is untested against data.sec.gov in CI on purpose.

## 2026-11-04 — Deliveries transcription window, totals, and source URLs

**Decision:** `data/manual/deliveries.csv` holds 20 quarters, `2021-Q4` through `2026-Q3`, in that order. `2026-Q3` is the latest production-and-deliveries release available on 2026-11-04 (dated 2026-10-02). `2026-Q4` is not out yet.

`quarter` is `YYYY-Qn`. `release_date` is the date Tesla published the release, which in this window is the 2nd of the following month (January for Q4). That date is the press-release date. When the 2nd falls on a weekend or holiday, the Form 8-K is sometimes filed the next business day. The CSV keeps the press-release date.

`production_total` and `deliveries_total` are the Total row of that quarter's first investor-relations production-and-deliveries release. They are not the rounded lead sentence ("over 305,000") and not a figure reprinted later in a shareholder update or a 10-Q. The same Total row appears in the Exhibit 99.1 attached to the Form 8-K Tesla filed for that release. Those exhibits were the check that the live pages still show the first-release table.

`source_url` is the `https://ir.tesla.com/press-release/...` page for that release. Slug spelling follows the live page. The 2025 Q2, Q3, and Q4 slugs omit the word "and" before "deployments". The quarters around them include it. No pipeline code fetches these pages. There is still no ingest command.

The Q4 release also prints an annual Total row. The four quarters of 2022, 2023, 2024, and 2025 sum to those annual totals (production and deliveries). That is the cross-check for a one-cell typo. 2021 and 2026 are partial years in this file, so they are not part of that check.

**Why:** Section 2 and M1-T4 require the last 20 quarters, transcribed from the first official release, with a release date and a source URL, and they require that a normal ingest does not scrape the pages. The table total is the figure Tesla states exactly. The lead sentence is approximate. A later operational summary can be restated. The Q3 2025 shareholder update, for example, later adjusted the operating-lease count. The production and deliveries totals on these first releases were not revised. The 8-K exhibit is the frozen copy of the first release. The IR page is the source URL the brief asks for, and it is the page M1-T5 will re-fetch.

**Alternatives considered:**

- Start the window at `2022-Q1` and stop at a later quarter. Rejected because `2026-Q4` has no release yet, and "the last 20 quarters" means the 20 most recent releases.
- Store the rounded headline figures. Rejected because they are not the table totals and would not match the page M1-T5 checks.
- Store model-level rows or energy-storage deployments. Rejected because the brief's columns are vehicle production and delivery totals only.
- Use the shareholder-letter operational summary, or the 10-Q delivery count, when it differs. Rejected because M1-T4 says the first release, not a later revision.
- Put the SEC exhibit URL in `source_url`. Rejected because the brief asks for the investor-relations release. The exhibit was the transcription check, not the cited source.
- Add an ingest client that downloads the pages. Rejected because M1-T4 says no pipeline fetch, and M1-T5 owns the optional re-fetch checker.

**What this means for later tasks:** M1-T5 can re-fetch `source_url` and look for that row's production and deliveries figures on the page. It should compare against this CSV, not against a shareholder deck. Ingest loads the file from disk. Do not add a scraper under `agent/` for these pages. Jacob still spot-checks the CSV. Extending the file past `2026-Q3` is a later edit once Tesla publishes the next release.

## 2026-11-04 — Python toolchain, package layout, and the test workflow

**Decision:** The Python project uses uv. `uv.lock` is the lockfile, `.python-version` pins 3.11, and `requires-python` is `>=3.11`. The install command is `uv sync`. It downloads CPython 3.11 when the machine does not already have it, and it installs the project plus pytest.

The import package is `agent` at the repository root. `uv_build` is configured with `module-name = "agent"` and `module-root = ""`, which is the flat layout from section 7. Later tasks add stages under that package and run them with `python -m agent`.

Runtime dependencies, locked in this task: DuckDB, pandas, openai, pydantic, and pydantic-settings. pydantic-settings reads `.env` and depends on python-dotenv. Dev dependencies: pytest and ruff. `uv add --bounds lower` wrote the floors in `pyproject.toml` from the versions resolved on this date. `uv.lock` holds the pins.

`agent.settings.Settings` loads the four names in `.env.example`. `OPENAI_API_KEY` and `SEC_USER_AGENT` are `SecretStr` fields, so a repr of the model does not contain their values. `publish_forward_forecast` defaults to false. `openai_model` defaults to an empty string. The narration task will choose a current structured-output model when the client is written, after checking OpenAI's docs.

`.gitignore` ignores `.env`, other `.env.*` files, and `data/cache/`. `.env.example` and `data/manual/` stay tracked. `data/manual/.gitkeep` keeps that directory until M1-T4 adds `deliveries.csv`.

`.github/workflows/test.yml` runs on pull requests and on pushes to `main`. The job checks out the repo, installs uv and Python 3.11, runs `uv sync --locked --all-extras --dev`, then ruff and `uv run pytest`. It requests `contents: read` and does not receive `OPENAI_API_KEY` or `SEC_USER_AGENT`. Action SHAs are pinned to `actions/checkout` v7.0.1 and `astral-sh/setup-uv` v10.3.3.

The one-line `README.md` stub stays until M6. Current run instructions live in `docs/PROGRESS.md`.

**Why:** Section 4 requires Python 3.11+, uv or pip with a lockfile, DuckDB, pandas, the official OpenAI SDK, pydantic, and pytest, and it requires those tests to pass in CI. Section 7 places the package at `agent/`. Section 11 requires `main` to pass tests. The plan already treats `test.yml` as the CI workflow for that requirement. It is separate from `deploy.yml` and does not enable Pages.

**Alternatives considered:**

- pip-tools with a requirements lock. Rejected because the brief names uv first, and `uv sync` also installs the Python version the acceptance check calls for.
- The `src/tesla_fpa_agent` tree that `uv init --package` generates. Rejected because section 7 and `python -m agent` both use the `agent` package at the repo root.
- Adding DuckDB, pandas, openai, and pydantic only when a later task imports them. Rejected because the parallel tasks that start after M1-T1 merges would each rewrite `uv.lock`.
- Putting a default model name in `OPENAI_MODEL` now. Rejected because section 2 says to check OpenAI's docs at build time for a model that supports structured JSON outputs. That check belongs with the narration client.
- Filling in `README.md` with setup steps. Rejected because M6 owns the case-study README, and the M0 decision keeps the stub until then.

**What this means for later tasks:** After pulling, run `uv sync`. Add a dependency with `uv add` in the same commit as the code that imports it. Keep secret values out of `.env.example`, workflow files, docs, and logs. `refresh.yml` and `deploy.yml` are still later tasks. This test workflow does not change repository settings.

## 2026-11-04 — Private repo for now, and handoff docs live under `docs/`

### Keep the repository private until Jacob says otherwise

**Decision:** The repo stays private. Do not make it public, do not enable GitHub Pages, and do not change repository settings unless Jacob's go-ahead is recorded in `docs/PROGRESS.md`.

**Why:** Jacob instructed the builder not to do those things without his explicit go-ahead. The repo is private today. GitHub Pages deployment needs his decision before anyone enables it.

**What the brief says:** The header and section 3 call for a public GitHub repo on Jacob's account, with the dashboard on GitHub Pages. That remains the brief. This entry is the override.

**Alternatives considered:**

- Make the repo public now, matching section 3. Rejected because it contradicts Jacob's instruction.
- Edit section 3 of `docs/BRIEF.md` so the brief itself says private. Rejected because section 11 forbids silent edits to the brief. Overrides are logged here.

**What this means for later tasks:** `deploy.yml` (M4-T4) may be committed so the workflow is ready. Enabling Pages, flipping visibility, or changing other repo settings is out of scope until Jacob answers the question already listed in `docs/PROGRESS.md`. The live shareable link in the README stays blocked on that answer.

### Docs layout for the first commit

**Decision:** This commit adds only the section 11 handoff files, in the locations from section 7:

- `AGENTS.md` and `CLAUDE.md` (the same short instruction)
- `.cursor/rules/handoff.mdc` (always applied, same instruction)
- `docs/BRIEF.md` (byte-for-byte copy of the build brief)
- `docs/PLAN.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md`

No product code, package files, workflows, prompts, or data files are in this commit. The existing one-line `README.md` stub stays until M6.

**Why:** Section 11 requires these files before any product code, and says the repo is the source of truth for handoffs. `docs/BRIEF.md` is copied verbatim so later agents read the same brief. Changes to the brief, if Jacob ever wants them, are logged here and are not made quietly.

**Alternatives considered:**

- Scaffold the Python package and the site in this same commit. Rejected because section 11 says the first commit is the handoff docs, before any product code.
- Leave the brief only in chat. Rejected because nothing important may exist only in an agent's chat history.

**Plan conventions recorded here so later agents do not re-litigate them:**

- The section 11 first commit is task `M0-T1`. Milestones M1 through M6 use the names given in section 11. M0 exists so setup and data ingest stay one milestone.
- Section 7 names `deploy.yml` and `refresh.yml`. Section 4 also says tests must pass in CI, so M1-T1 adds a separate test workflow. That workflow is not a second deploy and does not enable Pages.
- Branches follow section 11: `task/<id>-short-name`, one task per branch, pull request into `main`.
