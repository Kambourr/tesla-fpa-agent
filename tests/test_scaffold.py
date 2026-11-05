"""Acceptance checks for the repository scaffold.

These tests lock the M1-T1 contract: Python 3.11+, pytest, the lockfile,
ignore rules, the env template, and a pull-request test workflow.
"""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import duckdb
import openai
import pandas
import pydantic
import pydantic_settings
import pytest

import agent

REPO_ROOT = Path(__file__).resolve().parents[1]

ENV_ASSIGNMENTS = (
    "OPENAI_API_KEY=",
    "OPENAI_MODEL=",
    "SEC_USER_AGENT=",
    "PUBLISH_FORWARD_FORECAST=false",
)

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"x-access-token:[A-Za-z0-9._\-]+"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)

SKIP_PARTS = {
    ".git",
    ".venv",
    ".vite",
    "node_modules",
    "dist",
    "dist-ssr",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


def _git_check_ignore(path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_interpreter_is_python_311_or_newer() -> None:
    assert sys.version_info >= (3, 11)
    assert pytest.__version__


def test_stack_imports() -> None:
    """The lockfile installs the libraries named in the brief, plus pytest."""
    assert duckdb.__name__ == "duckdb"
    assert pandas.__name__ == "pandas"
    assert openai.__name__ == "openai"
    assert pydantic.__name__ == "pydantic"
    assert pydantic_settings.__name__ == "pydantic_settings"


def test_pyproject_requires_python_311_and_matches_package_version() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    assert project["requires-python"] == ">=3.11"
    assert project["version"] == agent.__version__
    assert "pytest" in (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_lockfile_pins_pytest_and_the_project() -> None:
    lock_text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "tesla-fpa-agent"' in lock_text
    assert 'name = "pytest"' in lock_text
    for package in ("duckdb", "pandas", "openai", "pydantic", "pydantic-settings", "ruff"):
        assert f'name = "{package}"' in lock_text


def test_gitignore_hides_secrets_and_cache_and_keeps_manual_data() -> None:
    ignored = (
        ".env",
        ".env.local",
        "data/cache/companyfacts.json",
        "data/cache/nested/filing.json",
    )
    tracked = (
        ".env.example",
        "data/manual/deliveries.csv",
        "data/manual/.gitkeep",
        "pyproject.toml",
        "uv.lock",
    )
    for path in ignored:
        result = _git_check_ignore(path)
        assert result.returncode == 0, f"{path} should be ignored"
    for path in tracked:
        result = _git_check_ignore(path)
        assert result.returncode == 1, f"{path} should stay tracked"


def test_env_example_lists_the_contract_with_empty_secrets() -> None:
    lines = [
        line.strip()
        for line in (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert lines == list(ENV_ASSIGNMENTS)
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        assert pattern.search(text) is None
    assert "@" not in text


def test_test_workflow_runs_pytest_on_pull_requests() -> None:
    text = (REPO_ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert "pull_request:" in text
    assert 'python-version: "3.11"' in text
    assert "uv sync --locked" in text
    assert "uv run pytest" in text
    assert "OPENAI_API_KEY" not in text
    assert "SEC_USER_AGENT" not in text
    for pattern in SECRET_PATTERNS:
        assert pattern.search(text) is None


def _committable_files() -> list[Path]:
    """Tracked files plus untracked files git would add: what could reach GitHub.

    Walking the whole directory also read git-ignored caches and the agents'
    temporary worktrees under .claude/, which change during a run and made this
    test fail at random when a file vanished mid-walk.
    """
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8")
        names = [name for name in listed.split("\0") if name]
        return [REPO_ROOT / name for name in names]
    except (OSError, subprocess.CalledProcessError):
        return [path for path in REPO_ROOT.rglob("*") if path.is_file()]


def test_source_tree_has_no_secret_material() -> None:
    offenders: list[str] = []
    for path in _committable_files():
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{path.relative_to(REPO_ROOT)} matches {pattern.pattern}")
    assert offenders == []
