# Decisions

Newest entry at the top. Every non-obvious choice goes here: the decision, the alternatives considered, and why. A deviation from `docs/BRIEF.md` is logged here first. The brief is not edited to hide an override.

## 2026-11-04 — Revenue bridge uses total deliveries, including leased units

**Decision:** The volume bar is the change in total deliveries times the forecast ASP. The price/mix bar is the change in ASP times actual total deliveries. ASP is automotive sales divided by total deliveries. Regulatory credits, leasing, energy, and services are actual minus forecast. A positive bar is favorable. Zero is not favorable. Leased units sit inside the delivery total, so the volume bar is not a pure retail-unit effect. `M5-T13` should say that in the methods copy.

**Alternatives considered:** Removing leased units from the volume bar would need a leased-unit count the delivery file does not have. Treating a zero leasing bar as favorable would mark an unchanged line as good news.

## 2026-11-04 — Backtest keeps every miss, including a large one

**Decision:** Absolute percent error is `100 * abs(forecast - actual) / abs(actual)`, stored as a percent. A result of 300 means the miss was three times the actual. The value is not clipped. An actual of zero, or a null forecast, stores the quarter with a null error. The average is the mean of the non-null errors for that metric. It is computed from the table and is not inserted as a quarter named `average`.

**Alternatives considered:** Dropping a zero actual would hide the quarter. Capping the error at 100 percent would make a bad forecast look bounded. Storing the average under `quarter = 'average'` would make a later loop treat it as a period.

## 2026-11-04 — Scenarios flex three drivers and compound sales

**Decision:** `scenario_forecasts()` starts from `base_forecast()` and writes bull, base, and bear. The flex amounts and units are read from `config/forecast.json` at call time. Deliveries and ASP move by a percent of themselves. Gross margin moves by basis points, which is an absolute ratio change (`100` basis points is `0.01`). Automotive sales is the flexed delivery count times the flexed ASP. Total revenue, gross profit, and operating income are rebuilt from those flexed pieces. Credits, leasing, energy, services, operating expenses, CFO, capex, and free cash flow stay at the base amount. An empty base forecast stays empty in all three scenarios.

**Alternatives considered:** Flexing sales by a separate percent would ignore the compounding the config notes already describe. Hardcoding 10, 5, and 100 in the scenario function would miss a later config edit. Flexing free cash flow would invent a cash effect the formulas do not have.

## 2026-11-04 — Base forecast executes the config on cutoff history

**Decision:** `base_forecast()` reads only the `ForecastInputs` from `load_forecast_inputs()`. A target quarter with fewer than `minimum_earlier_quarters` earlier quarters in that input is stored with a null value and `empty_history` true. The count is any earlier quarter that has a delivery row or a mapped financial fact, not a count of one metric.

Deliveries are `D(Q-4) * (1 + g)` with `g = D(Q-1) / D(Q-5) - 1`, and `g` is 0 when `D(Q-5)` is missing or zero. ASP drops a prior quarter with missing sales or zero deliveries and averages what remains. Run-rate lines need all four prior quarters. Capex is stored as `purchases_of_property_and_equipment`. Cash-flow history is year-to-date de-cumulated; a year can contribute Q1 or Q2 without a later 10-Q. Income history uses a single-quarter duration when one is stored, and derives Q4 from the annual amount only when that duration is absent. Gross profit uses automotive, energy, and services margins when all three are in the four prior quarters. Otherwise it uses total gross profit divided by total revenue. The stored `gross_margin` is the margin that turns forecast revenue into that gross profit. R&D and SG&A are written only when their own run-rate can be built.

**Alternatives considered:** Reading `quarter_actual` would ignore a restatement that was already public on the cutoff. Requiring five earlier quarters would contradict the four-quarter empty state. Averaging a run-rate over the quarters that happen to exist would hide a hole in the history. Treating every Q4 duration as derived would drop a single-quarter amount `fact_as_of` already selected.

## 2026-11-04 — Forecast cutoff is the previous quarter's first filing

**Decision:** `load_forecast_inputs()` dates the forecast for quarter Q at the earliest `filing_date` of a 10-Q, 10-K, or amendment whose own period end is Q-1. Facts are `fact_as_of(cutoff_date)`, so a restatement filed on or before that date replaces the first-reported number. `quarter_actual` stays the first report. A 10-Q/A of Q-1 does not move the cutoff later, so an amendment filed after the original 10-Q is invisible to the forecast for Q. Deliveries and production are included only when the quarter is before Q and the release date is on or before the cutoff. Q's own delivery row is dropped even when its release date is earlier than the cutoff.

**Alternatives considered:** Using the latest amendment date as the cutoff would slide the forecast forward and could include Q's delivery report. Reading `quarter_actual` for every input would hide a restatement that was already public on the cutoff. Treating a delivery release date on or before the cutoff as enough would let Q's own deliveries in, which section 8 rules out.

## 2026-11-04 — Ingest keeps the forecast window and does not scrape

**Decision:** `python -m agent ingest` validates `deliveries.csv` before it opens the database or the SEC client. A validation failure stops the command. The command never calls `fetch_source_page`. `--fixtures` reads local JSON so a test run does not need `SEC_USER_AGENT`. The default path uses `SecClient`, which reads that variable and does not print it.

The database keeps every loaded quarter. After the load it checks that `quarter_actual` for `total_revenue`, and the `deliveries` table, both contain the last 12 reported quarters plus the earlier quarters the forecast reads. That history is the deepest `input_offsets` value in `config/forecast.json`, which is five quarters (through Q-5). `minimum_earlier_quarters` is 4, which is shorter than those offsets, so the check uses the offsets. A restatement stays in `fact`.

**Alternatives considered:** Trimming the database to exactly those quarters would drop restatements and the deliveries quarters before the window. Checking only `minimum_earlier_quarters` would leave the Q-5 input unread. Scraping investor-relations pages during ingest would repeat the fetch that already returns HTTP 403 from this network. M1-T5 kept that fetch out of the load path.

## 2026-11-04 — About links stay blank until Jacob fills them in

**Decision:** The about credit is the sentence in section 5. GitHub, LinkedIn, and résumé come from `profileLinks` in `site/src/config.ts`. All three values stay empty strings. A blank value renders the label and the words "Not filled in yet". It does not render an anchor, so the page has no guessed URL and no link that goes nowhere.

**Why:** M5-T14 says the placeholders are obvious and empty of guessed URLs, and the page still renders when they are blank. An example URL would be a guess.

**Alternatives considered:**

- Placeholder links to `example.com` or `#`. Rejected because they look like real destinations.
- Hiding the three rows until a URL exists. Rejected because the empty state would not show Jacob where to type.

**What this means for later tasks:** Fill `profileLinks` only when Jacob supplies the URLs. Do not invent them.

## 2026-11-04 — Methods diagram is an example, not a recorded run

**Decision:** `site/src/methodExample.ts` is the shape of the six section 5 stages. The page says "Example of the pipeline. Not a recorded run." The fixture has no durations, costs, or dollar amounts. Explain is the only stage whose actor is Model. The other five are Code. The word is in the diagram, and Model is also cobalt, so the split does not depend on color. At 480px and below the same stages render as a vertical SVG.

The prose says visitors do not call the model, that a commentary figure is verified, flagged, or unsupported, that the only sources are public SEC filings and investor-relations releases, and that leased units sit inside total deliveries. Automotive ASP uses that total, so the volume bar treats a leased unit like a sold one. Leasing stays its own bar.

**Why:** M5-T13 asks for the diagram and those limits before a published run exists. Durations and cost belong to M5-T6, which reads run metadata.

**Alternatives considered:**

- A screenshot of code or of a terminal. Rejected because the task asks for an inline SVG.
- Arrow characters between the stages. Rejected because the site scan forbids `→`, and a ledger line is enough.
- Sample durations or a dollar figure marked "example." Rejected because a number on this page would be easy to read as a result. The label says the diagram is not a recorded run, and it contains no amounts.

**What this means for later tasks:** M5-T6 can show durations from published run metadata. Do not put those numbers in `methodExample.ts`.

## 2026-11-04 — First-reported quarter actuals, with restatements kept

**Decision:** `agent/actuals.py` writes one `fact` row per metric, period, and accession, then rebuilds `quarter_actual` from those rows. A quarter's income-statement actual is the value on the 10-Q whose own period end is that quarter, using the earliest filing date. A later filing that repeats the period stays in `fact` and does not replace `quarter_actual`. Q4 is `derive_q4` of the 10-K annual amount minus those three first-reported quarters, even when the 10-K also tags a Q4 duration. Cash-flow lines are year-to-date on a 10-Q, so Q1–Q3 go through `cash_flow_quarters` and Q4 is the same derivation. `fact_as_of(cutoff_date)` is the latest stored value on or before a cutoff.

Companyfacts has no dimensions, so this step only stores tags with no member. A segment line stays absent until a filing instance is read. The same `store_reported_facts` function accepts those rows later. It does not sum members, and it does not fetch.

**Alternatives considered:** Overwriting `fact` with the latest comparative would make the cutoff query easy and would drop the restatement M3-T8 has to keep. Treating a Q4 duration inside the 10-K as the actual would skip the derivation M1-T7 exists to provide. Reading segment lines out of companyfacts is not possible; the feed does not carry them.

## 2026-11-04 — Quarter fixture, listbox, and site tests

**Decision:** Until published quarter JSON exists, `site/src/quarters.ts` is a label-only stand-in. It has no dollar amounts. Q4 2025 has `hasForecast: false` because a forecast needs four earlier quarters, the same cutoff `config/forecast.json` uses. Q1 2026, Q2 2026, and Q3 2026 have a forecast. The last record is the latest quarter, and the page selects it on load.

The control is a disclosure listbox in the masthead. The open list is part of the masthead flow, above the double rule, aligned to the right on wide screens and to the left below 481px. It is not a native select and not a component-library widget. The selected row shows a tick and the visually hidden word "Selected". The tick is ink, not green. Green stays the verification mark.

When `hasForecast` is false, the lede is exactly: "No forecast for this quarter: it needs four earlier quarters of history." That sentence appears once. The section under it says to select a later quarter or wait until four earlier quarters are on file.

Site interaction tests use Vitest 5.1.0, `@testing-library/react` 16.3.3, `@testing-library/user-event` 14.6.8, and jsdom 30.1.3, locked in `site/package-lock.json`. `npm test` is `vitest run`. The `site build` job runs `npm test` and then `npm run build`. It still requests no secrets and does not deploy.

**Why:** M5-T2 needs a latest quarter, a way to select an earlier one, and the four-quarter empty state before M4-T1 publishes data. An overlay menu covered the headline at 375px. Putting the list in the masthead keeps the headline readable and keeps the control looking like a ledger row rather than a floating card.

**Alternatives considered:**

- A native `<select>`. Rejected because the platform control looks like a template and cannot take the ledger rules and the tick.
- A dropdown library. Rejected because this page has one control, and a library widget brings its own chrome.
- Hardcoding the wireframe amounts (`$24.1B` and the rest). Rejected because section 6 says those numbers are placeholders. M5-T4 draws them from published data.
- Painting the selection tick in tied green. Rejected because green is the audit tick. A selection mark in ink does not look like a verified figure.
- Leaving the menu as an overlay. Rejected after the 375px check: the list covered the headline.

**What this means for later tasks:** M4-T1 replaces `quarterFixture` with the published quarters. M5-T4 replaces the "once they are published" lede with the real forecast, actual, and variance, and adds the waterfall under the existing heading. Do not put dollar amounts in `quarters.ts`. Do not enable Pages from this task.

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

## 2026-11-04 — Site toolchain, Pages base path, and dark-mode colors

**Decision:** The dashboard lives in `site/` and uses npm. `site/package-lock.json` is the lockfile. `npm ci` installs it. `npm run build` is `tsc -b && vite build`. Node 22 is the version CI uses. Locked on this date: Vite 8.3.5, React 19.3.1, TypeScript 7.0.2, `@vitejs/plugin-react` 6.2.1, `@fontsource/ibm-plex-sans` 5.3.0, `@fontsource/source-serif-4` 5.3.1.

`vite.config.ts` sets `base` to `/tesla-fpa-agent/`, the GitHub Pages project path for this repository. Asset URLs in `index.html` use `%BASE_URL%`. This task does not enable Pages and does not change repository settings.

Fonts are self-hosted from the latin subsets, not loaded from a third-party stylesheet. IBM Plex Sans 400 and 500 are the interface face. Source Serif 4 400 is the narrative face. `body` sets `font-variant-numeric: tabular-nums`. `.narrative` sets Source Serif 4, line-height 1.55, and a 680px measure. UI copy stays in Plex. The memo and the Q&A are the only text that should use `.narrative`.

Light tokens are the section 6 hexes: Paper `#F4F6F8`, Ink `#18212B`, ledger rule `#CBD3DC`, cobalt `#2448C8`, green `#0E7A5A`, amber `#A85B00`, and white `#FFFFFF` for a raised surface. Measured contrast of the three accents on paper is 6.84, 4.91, and 4.66. Ink on paper is 15.01. All clear WCAG AA for normal text.

Dark mode keeps those hues and lightens the accents:

| Token | Hex | Contrast on `#121820` | Contrast on the raised sheet `#1B2430` |
|---|---|---|---|
| Paper | `#121820` |  |  |
| Ink | `#E6EBF0` | 14.87 | 13.05 |
| Cobalt | `#7D95E8` | 6.23 | 5.47 |
| Green | `#15B787` | 6.93 | 6.08 |
| Amber | `#E67C00` | 6.16 | 5.40 |
| Ledger rule | `#2A3848` | 1.49 |  |
| Quiet ink | `#9AABBC` | 7.58 | 6.65 |

The light quiet ink is `#4A596A` (6.62 on paper, 7.17 on white). The dark raised sheet is `#1B2430`, a step off the paper, not white. The dark rule is about as quiet as `#CBD3DC` on light paper (1.40). Green is the small masthead tick only. It is not a page-sized accent.

The page is a document, not the Vite starter. The masthead reads "Tesla FP&A Agent". The heading is the section 5 headline. The empty state says the pipeline has not written a quarter. The footer is the required disclaimer, stored in `site/src/config.ts`. `profileLinks` in that file are empty strings. There is no quarter picker and no waterfall, and the wireframe dollar amounts are not in the source.

`.github/workflows/test.yml` adds a `site build` job on the same pull-request trigger. It runs `npm ci` and `npm run build` with Node 22. `actions/setup-node` is pinned to v7.1.0 (`949feb2413d6458794dcd2491c4babbbce0c15c1`). The job requests no secrets. The root `.gitignore` ignores `node_modules/`, and the secret scan skips `node_modules` and `dist` so it does not walk dependencies or build output. Source is still scanned.

**Why:** M5-T1 asks for a Vite, React, and TypeScript app, a Pages base path, the section 6 palette and type, dark mode, and tabular figures, and it asks for `npm run build` to succeed. Section 6 also requires AA contrast and forbids a template look. Putting the build in the existing test workflow is how that acceptance command runs on the pull request. The workflow still does not deploy.

**Alternatives considered:**

- pnpm or Yarn. Rejected because the task names `npm run build` as the acceptance command.
- A font stylesheet from a CDN. Rejected because the built site should not depend on a third-party host, and the latin files are small.
- Leaving the Vite starter page and swapping only the CSS variables. Rejected because the starter reads as a template, which section 6 forbids.
- Applying Source Serif 4 to the lede and the empty state. Rejected because section 6 reserves that face for the analyst memo and the Q&A answers. The class is ready for those tasks.
- Skipping the site job and relying on a local build. Rejected because `main` has to keep passing the acceptance check after this merges.
- Enabling GitHub Pages so the base path could be checked on a live URL. Rejected because Jacob has not approved a settings change. The preview was checked locally at `/tesla-fpa-agent/`.

**What this means for later tasks:** Run `npm ci` in `site/` before `npm run build`. Keep `base` as `/tesla-fpa-agent/`. M5-T2 adds the quarter picker. The header text and the disclaimer are already the required strings. Keep one footer. M5-T4 adds the quarter line and the waterfall under the existing heading. Do not hardcode the wireframe amounts. Use `.narrative` only for the memo and the answers. Fill `profileLinks` only when Jacob supplies URLs. Do not enable Pages from a site task.

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
