# Decisions

Newest entry at the top. Every non-obvious choice goes here: the decision, the alternatives considered, and why. A deviation from `docs/BRIEF.md` is logged here first. The brief is not edited to hide an override.

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
