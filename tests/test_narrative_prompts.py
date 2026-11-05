"""Prompt files and the structured narrative schema. No model calls."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent.narrative import Claim, NarrativeDraft, load_prompts

QUESTION_MARKERS = (
    "revenue variance versus forecast",
    "gross margin",
    "regulatory credits",
    "energy storage",
    "operating expenses",
    "free cash flow",
    "hardest to forecast",
    "accurate has the model been overall",
    "bear scenario",
    "watch next quarter",
)


def test_prompts_have_a_version_the_cache_can_hash() -> None:
    bundle = load_prompts()
    again = load_prompts()
    assert bundle.version == "2026-11-05.1"
    assert bundle.content_sha256 == again.content_sha256
    assert bundle.cache_material == f"{bundle.version}\n{bundle.content_sha256}"
    assert bundle.temperature == 0.2


def test_ten_questions_and_the_backtest_pair() -> None:
    bundle = load_prompts()
    assert len(bundle.questions) == 10
    for question, marker in zip(bundle.questions, QUESTION_MARKERS, strict=True):
        assert marker in question.text
    backtest = [question.number for question in bundle.questions if question.uses_backtest]
    assert backtest == [7, 8]
    seventh, eighth = bundle.questions[6], bundle.questions[7]
    assert "all 12 published quarters" in seventh.text
    assert "all 12 published quarters" in eighth.text


def test_memo_rules_name_the_word_counts_and_refuse_advice() -> None:
    text = load_prompts().memo_instructions
    assert "150 to 250" in text
    assert "60 to 120" in text
    assert "investment advice" in text
    assert "Questions 7 and 8" in text


def test_narrative_requires_a_memo_answers_and_claim_fields() -> None:
    claim = {
        "metric": "revenue",
        "period": "2024-Q3",
        "value": 25.2,
        "unit": "USD billions",
        "sentence_ref": "1",
    }
    draft = NarrativeDraft.model_validate(
        {
            "memo": {"text": "Revenue was 25.2.", "claims": [claim]},
            "answers": [{"question_number": 1, "text": "Volume.", "claims": []}],
        }
    )
    assert draft.memo.claims[0] == Claim.model_validate(claim)
    with pytest.raises(ValidationError):
        NarrativeDraft.model_validate({"answers": []})
    with pytest.raises(ValidationError):
        NarrativeDraft.model_validate({"memo": {"text": "x", "claims": []}})
    incomplete = dict(claim)
    del incomplete["sentence_ref"]
    with pytest.raises(ValidationError):
        Claim.model_validate(incomplete)


def test_a_changed_prompt_file_changes_the_hash(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parent.parent / "prompts"
    for name in ("manifest.json", "memo.md", "questions.json"):
        (tmp_path / name).write_bytes((source / name).read_bytes())
    original = load_prompts(tmp_path).content_sha256
    memo = tmp_path / "memo.md"
    memo.write_text(memo.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert load_prompts(tmp_path).content_sha256 != original


def test_prompt_files_carry_no_email() -> None:
    source = Path(__file__).resolve().parent.parent / "prompts"
    for path in source.iterdir():
        assert "@" not in path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
