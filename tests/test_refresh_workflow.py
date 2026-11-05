"""Acceptance checks for the M4-T3 refresh workflow and its deploy trigger."""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
REFRESH = WORKFLOWS / "refresh.yml"
DEPLOY = WORKFLOWS / "deploy.yml"
DATA_PATHS = {"site/public/data/dashboard.json", "data/narrative_cache.json"}
SHA_PIN = re.compile(r"^(- )?uses:\s*\S+@[0-9a-f]{40}\s+# v\d")


def _load(path: Path) -> tuple[str, dict]:
    text = path.read_text(encoding="utf-8")
    # PyYAML 1.1 reads an unquoted "on" key as boolean true. GitHub Actions uses that key.
    return text, yaml.safe_load(text)


def _steps(loaded: dict, job: str) -> list[dict]:
    return loaded["jobs"][job]["steps"]


def _run_step(loaded: dict, name: str) -> dict:
    matches = [step for step in _steps(loaded, "refresh") if step.get("name") == name]
    assert len(matches) == 1, f"expected one step named {name!r}"
    return matches[0]


def test_refresh_is_manual_with_force_input() -> None:
    _, loaded = _load(REFRESH)
    assert loaded["name"] == "Refresh data"
    trigger = loaded[True]
    assert "workflow_dispatch" in trigger
    force = trigger["workflow_dispatch"]["inputs"]["force"]
    assert force["type"] == "boolean"
    assert force["default"] is False


def test_schedule_is_only_a_comment() -> None:
    text, loaded = _load(REFRESH)
    assert "schedule" not in loaded[True]
    assert re.search(r"^\s*#\s*schedule:", text, re.MULTILINE)
    assert re.search(r'^\s*#\s*-\s*cron:\s*"17 14 5 1,4,7,10 \*"', text, re.MULTILINE)


def test_refresh_permissions_and_concurrency() -> None:
    _, loaded = _load(REFRESH)
    assert loaded["permissions"] == {"contents": "write"}
    assert loaded["concurrency"]["group"] == "refresh"
    assert loaded["concurrency"]["cancel-in-progress"] is False


def test_run_step_reads_secrets_from_the_secrets_context() -> None:
    _, loaded = _load(REFRESH)
    run = _run_step(loaded, "Run the pipeline")
    assert run["env"]["OPENAI_API_KEY"] == "${{ secrets.OPENAI_API_KEY }}"
    assert run["env"]["SEC_USER_AGENT"] == "${{ secrets.SEC_USER_AGENT }}"
    assert run["env"]["PUBLISH_FORWARD_FORECAST"] == "false"
    assert "agent run" in run["run"]
    assert "--force" in run["run"]


def test_secret_check_step_runs_before_the_pipeline() -> None:
    _, loaded = _load(REFRESH)
    names = [step.get("name") for step in _steps(loaded, "refresh")]
    check = names.index("Check that the required secrets are set")
    assert check < names.index("Run the pipeline")
    check_run = _run_step(loaded, "Check that the required secrets are set")["run"]
    assert 'if [ -z "$OPENAI_API_KEY" ]' in check_run
    assert 'if [ -z "$SEC_USER_AGENT" ]' in check_run


def test_file_never_prints_or_embeds_secret_values() -> None:
    text, _ = _load(REFRESH)
    assert not re.search(r"echo\s+\$\{?(OPENAI_API_KEY|SEC_USER_AGENT)", text)
    assert not re.search(r"\bsk-[A-Za-z0-9_-]{8,}", text)
    assert "set -x" not in text


def test_commit_step_adds_only_the_two_data_paths() -> None:
    _, loaded = _load(REFRESH)
    commit_run = _run_step(loaded, "Commit the refreshed data")["run"]
    added = re.findall(r"git add (.+)", commit_run)
    assert added, "the commit step must stage files"
    staged = {path for line in added for path in line.split()}
    assert staged == DATA_PATHS
    assert "git add -A" not in commit_run
    assert "git add ." not in commit_run
    assert 'git config user.name "github-actions[bot]"' in commit_run
    assert (
        'git config user.email "41898282+github-actions[bot]@users.noreply.github.com"'
        in commit_run
    )
    assert 'git commit -m "Refresh data from the latest filings"' in commit_run
    assert "git diff --cached --quiet" in commit_run


def test_deploy_runs_after_a_successful_refresh() -> None:
    _, loaded = _load(DEPLOY)
    trigger = loaded[True]
    assert trigger["push"]["branches"] == ["main"]
    assert "pull_request" not in trigger
    run_trigger = trigger["workflow_run"]
    assert run_trigger["workflows"] == ["Refresh data"]
    assert run_trigger["types"] == ["completed"]
    build = loaded["jobs"]["build"]
    assert build["if"] == (
        "github.event_name == 'push' || github.event.workflow_run.conclusion == 'success'"
    )
    checkout = build["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["ref"] == "main"


def test_every_action_is_pinned_to_a_full_commit_sha() -> None:
    for path in sorted(WORKFLOWS.glob("*.yml")):
        _, loaded = _load(path)
        for job in loaded["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step:
                    ref = step["uses"].split("@", 1)[1]
                    assert re.fullmatch(r"[0-9a-f]{40}", ref), f"{path.name}: {step['uses']}"
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if "uses:" in line]
        for line in lines:
            assert SHA_PIN.match(line.strip()), f"{path.name}: {line.strip()}"
