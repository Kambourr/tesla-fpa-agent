# Commands for the Tesla FP&A pipeline. Run them from the repository root.
#
#   make run   runs every stage in order (ingest, model, variance, narrate, verify,
#              publish) and writes site/public/data/dashboard.json. It needs .env with
#              OPENAI_API_KEY and SEC_USER_AGENT, and it calls OpenAI.
#   make test  runs the Python tests, then the site tests.

.PHONY: run test

run:
	uv run python -m agent run

test:
	uv run pytest -q && cd site && npm test
