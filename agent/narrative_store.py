"""The narrative cache: verified narratives kept in the repo between runs.

GitHub Actions starts every run with an empty DuckDB, so without a cache each
run would ask the model again, and a past memo could change. ``export_verified``
writes every verified ``narrative`` row to ``data/narrative_cache.json``.
``import_cache`` restores those rows into a fresh database, still verified, so
``narrate`` reuses them on the same input hash and makes no model call.

The file holds model text, claims, token counts, validation issues and, from
M8-T1, what the verifier found in the first draft (``first_review``). It never
holds ``OPENAI_API_KEY`` or ``SEC_USER_AGENT``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from pydantic import ValidationError

from agent.deliveries import repo_root
from agent.narrative import NarrativeDraft

CACHE_PATH = repo_root() / "data" / "narrative_cache.json"
_FIELDS = (
    "quarter",
    "kind",
    "input_hash",
    "prompt_version",
    "model",
    "payload",
    "input_tokens",
    "output_tokens",
    "issues",
)


class NarrativeCacheError(ValueError):
    """The cache file is present but cannot be read as verified narratives."""


def export_verified(connection: duckdb.DuckDBPyConnection, path: Path) -> int:
    """Write every verified narrative to ``path``, sorted by quarter. Returns the count.

    The output is pretty JSON with sorted keys, so the same narratives always give
    the same bytes. An unverified row is left out, so the next run drafts it again.
    """
    rows = connection.execute(
        """
        SELECT quarter, kind, input_hash, prompt_version, model, payload,
               input_tokens, output_tokens, issues, first_review
        FROM narrative
        WHERE verified
        ORDER BY quarter
        """
    ).fetchall()
    entries = [
        {
            "quarter": quarter,
            "kind": kind,
            "input_hash": input_hash,
            "prompt_version": prompt_version,
            "model": model,
            "payload": json.loads(str(payload)),
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "issues": json.loads(str(issues)),
            "first_review": None if first_review is None else json.loads(str(first_review)),
        }
        for (
            quarter,
            kind,
            input_hash,
            prompt_version,
            model,
            payload,
            input_tokens,
            output_tokens,
            issues,
            first_review,
        ) in rows
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(entries, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return len(entries)


def import_cache(connection: duckdb.DuckDBPyConnection, path: Path) -> int:
    """Insert the cached narratives into ``narrative``, marked verified. Returns the count.

    A missing file is not an error: the first run has no cache. Every entry is
    checked before any row is written, so a bad file changes nothing.
    """
    if not path.is_file():
        return 0
    entries = _read_entries(path)
    now = datetime.now(UTC).replace(tzinfo=None)
    for entry in entries:
        connection.execute(
            """
            INSERT OR REPLACE INTO narrative (
                quarter, kind, input_hash, prompt_version, model, payload,
                input_tokens, output_tokens, issues, created_at, verified, first_review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?)
            """,
            [
                entry["quarter"],
                entry["kind"],
                entry["input_hash"],
                entry["prompt_version"],
                entry["model"],
                json.dumps(entry["payload"]),
                entry["input_tokens"],
                entry["output_tokens"],
                json.dumps(entry["issues"]),
                now,
                # Older cache files have no first_review; NULL means "not recorded".
                None
                if entry.get("first_review") is None
                else json.dumps(entry["first_review"], sort_keys=True),
            ],
        )
    return len(entries)


def _read_entries(path: Path) -> list[dict[str, Any]]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NarrativeCacheError(f"{path} is not valid JSON: {exc.msg}") from exc
    if not isinstance(loaded, list):
        raise NarrativeCacheError(f"{path} must hold a list of narratives")
    for index, entry in enumerate(loaded):
        if not isinstance(entry, dict) or any(field not in entry for field in _FIELDS):
            raise NarrativeCacheError(f"{path}: entry {index} is missing a field")
        try:
            NarrativeDraft.model_validate(entry["payload"])
        except ValidationError as exc:
            raise NarrativeCacheError(f"{path}: entry {index} is not a valid narrative") from exc
    return loaded
