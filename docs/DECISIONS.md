# Decisions

Newest entry at the top. Every non-obvious choice goes here: the decision, the alternatives considered, and why. A deviation from `docs/BRIEF.md` is logged here first. The brief is not edited to hide an override.

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
