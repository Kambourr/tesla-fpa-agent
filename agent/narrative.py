"""Prompt bundle and the structured response the model must return.

The prompt version is part of the narration cache key. The content hash
changes when a prompt file changes, even if the version string was left
behind. M3-T3 hashes ``cache_material`` with the input tables and the model.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
LOW_TEMPERATURE_MAX = 0.3


class Claim(BaseModel):
    """One number tied to one sentence. The verifier checks these later."""

    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1)
    period: str = Field(min_length=1)
    value: float
    unit: str = Field(min_length=1)
    sentence_ref: str = Field(min_length=1)


class Memo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    claims: list[Claim]


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_number: int = Field(ge=1, le=10)
    text: str = Field(min_length=1)
    claims: list[Claim]


class NarrativeDraft(BaseModel):
    """The object structured outputs must fill. Memo and answers are required."""

    model_config = ConfigDict(extra="forbid")

    memo: Memo
    answers: list[Answer]


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(ge=1, le=10)
    text: str = Field(min_length=1)
    uses_backtest: bool


class PromptBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    temperature: float
    memo_instructions: str = Field(min_length=1)
    questions: list[Question]
    content_sha256: str = Field(min_length=64, max_length=64)

    @field_validator("temperature")
    @classmethod
    def temperature_stays_low(cls, value: float) -> float:
        if value < 0 or value > LOW_TEMPERATURE_MAX:
            raise ValueError(f"temperature must be from 0 to {LOW_TEMPERATURE_MAX}")
        return value

    @model_validator(mode="after")
    def questions_match_section_4(self) -> "PromptBundle":
        numbers = [question.number for question in self.questions]
        if numbers != list(range(1, 11)):
            raise ValueError("questions must be numbered 1 through 10, in order")
        backtest = {question.number for question in self.questions if question.uses_backtest}
        if backtest != {7, 8}:
            raise ValueError("only questions 7 and 8 use the 12-quarter backtest")
        return self

    @property
    def cache_material(self) -> str:
        """Stable text for the cache hash: version, then the content hash."""
        return f"{self.version}\n{self.content_sha256}"


def load_prompts(directory: Path | None = None) -> PromptBundle:
    """Read the prompt files. Does not call the model."""
    root = PROMPTS_DIR if directory is None else directory
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    memo = (root / str(manifest["memo_path"])).read_text(encoding="utf-8")
    questions = json.loads((root / str(manifest["questions_path"])).read_text(encoding="utf-8"))
    content_sha256 = _hash_prompt_files(root, manifest)
    return PromptBundle(
        version=manifest["version"],
        temperature=manifest["temperature"],
        memo_instructions=memo,
        questions=questions,
        content_sha256=content_sha256,
    )


def _hash_prompt_files(root: Path, manifest: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update((root / "manifest.json").read_bytes())
    digest.update((root / str(manifest["memo_path"])).read_bytes())
    digest.update((root / str(manifest["questions_path"])).read_bytes())
    return digest.hexdigest()
