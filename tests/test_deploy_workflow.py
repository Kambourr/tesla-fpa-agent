"""Acceptance checks for the M4-T4 Pages workflow."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"


def _load() -> tuple[str, dict]:
    text = WORKFLOW.read_text(encoding="utf-8")
    # PyYAML 1.1 treats an unquoted "on" as boolean true. GitHub Actions uses that key.
    loaded = yaml.safe_load(text)
    return text, loaded


def test_deploy_workflow_is_valid_pages_yaml() -> None:
    text, loaded = _load()
    trigger = loaded[True]
    assert trigger["push"]["branches"] == ["main"]
    assert "pull_request" not in trigger
    assert loaded["permissions"]["contents"] == "read"
    assert loaded["permissions"]["pages"] == "write"
    assert loaded["permissions"]["id-token"] == "write"
    build_steps = loaded["jobs"]["build"]["steps"]
    build_runs = [step.get("run", "") for step in build_steps]
    assert "npm ci" in build_runs
    assert "npm run build" in build_runs
    uses = [step["uses"] for step in build_steps if "uses" in step]
    assert any(item.startswith("actions/upload-pages-artifact@") for item in uses)
    deploy = loaded["jobs"]["deploy"]
    assert deploy["needs"] == "build"
    assert deploy["environment"]["name"] == "github-pages"
    deploy_uses = deploy["steps"][0]["uses"]
    assert deploy_uses.startswith("actions/deploy-pages@")
    lowered = text.lower()
    assert "secrets." not in lowered
    assert "openai_api_key" not in lowered
    assert "sec_user_agent" not in lowered
    assert "echo " not in lowered
