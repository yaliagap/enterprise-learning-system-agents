"""Tests for state.py additions — grounding_reference, domain_scores, reasoning_distribution.

Covers T-03: backward compat + new fields on AssessmentQuestion, AssessmentQuestionPublic,
AssessmentResult, and GroundingReference reuse.
"""
from __future__ import annotations

import pytest

from workflow.state import (
    AssessmentQuestion,
    AssessmentQuestionPublic,
    AssessmentResult,
    GroundingReference,
    QuestionResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_question_kwargs() -> dict:
    return dict(
        id="q1",
        text="What is Azure?",
        question_type="multiple_choice",
        options=["A", "B", "C", "D"],
        correct_answers=["A"],
        domain="Cloud Concepts",
        exam_weight_pct=0.1,
        explanation="A is correct.",
        difficulty="easy",
        bloom_level="Understand",
    )


def _make_result(**kwargs) -> AssessmentResult:
    defaults = dict(
        attempt=1,
        score=65.0,
        passed=False,
        passing_score=70.0,
        weak_areas=["Cloud Concepts"],
        completed_at="2026-06-13T00:00:00Z",
    )
    defaults.update(kwargs)
    return AssessmentResult(**defaults)


# ---------------------------------------------------------------------------
# 1. AssessmentQuestion backward compat (no grounding_reference)
# ---------------------------------------------------------------------------


def test_assessment_question_backward_compat() -> None:
    """AssessmentQuestion must instantiate without grounding_reference (backward compat)."""
    q = AssessmentQuestion(**_base_question_kwargs())
    assert q.grounding_reference is None


# ---------------------------------------------------------------------------
# 2. AssessmentQuestion with grounding_reference — roundtrip
# ---------------------------------------------------------------------------


def test_assessment_question_with_grounding_reference_roundtrip() -> None:
    """AssessmentQuestion with grounding_reference serializes and deserializes correctly."""
    ref = GroundingReference(
        title="Azure Overview",
        url="https://learn.microsoft.com/en-us/azure/overview",
        type="web",
    )
    kwargs = _base_question_kwargs()
    kwargs["grounding_reference"] = ref
    q = AssessmentQuestion(**kwargs)

    assert q.grounding_reference is not None
    assert q.grounding_reference.url == "https://learn.microsoft.com/en-us/azure/overview"

    # Roundtrip via model_dump / model_validate
    dumped = q.model_dump()
    assert dumped["grounding_reference"]["url"] == "https://learn.microsoft.com/en-us/azure/overview"

    restored = AssessmentQuestion.model_validate(dumped)
    assert restored.grounding_reference is not None
    assert restored.grounding_reference.url == ref.url


# ---------------------------------------------------------------------------
# 3. AssessmentQuestionPublic with grounding_reference
# ---------------------------------------------------------------------------


def test_assessment_question_public_has_grounding_reference_field() -> None:
    """AssessmentQuestionPublic must accept and expose grounding_reference."""
    ref = GroundingReference(
        title="MS Learn Networking",
        url="https://learn.microsoft.com/en-us/azure/virtual-network/",
    )
    pub = AssessmentQuestionPublic(
        id="q1",
        text="What is a VNet?",
        question_type="multiple_choice",
        options=["A", "B", "C", "D"],
        correct_answer_count=1,
        domain="Networking",
        exam_weight_pct=0.15,
        explanation="A virtual network.",
        difficulty="medium",
        grounding_reference=ref,
    )
    assert pub.grounding_reference is not None
    assert pub.grounding_reference.url == ref.url


def test_assessment_question_public_grounding_reference_defaults_none() -> None:
    """AssessmentQuestionPublic.grounding_reference defaults to None."""
    pub = AssessmentQuestionPublic(
        id="q2",
        text="What is Azure?",
        question_type="multiple_choice",
        options=["A", "B", "C", "D"],
        domain="Cloud Concepts",
        exam_weight_pct=0.1,
        explanation="Azure is Microsoft's cloud.",
        difficulty="easy",
    )
    assert pub.grounding_reference is None


# ---------------------------------------------------------------------------
# 4. AssessmentResult backward compat — no domain_scores / reasoning_distribution
# ---------------------------------------------------------------------------


def test_assessment_result_backward_compat() -> None:
    """AssessmentResult must instantiate without domain_scores or reasoning_distribution."""
    result = _make_result()
    assert result.domain_scores == {}
    assert result.reasoning_distribution is None


# ---------------------------------------------------------------------------
# 5. AssessmentResult with both new fields — roundtrip
# ---------------------------------------------------------------------------


def test_assessment_result_with_new_fields_roundtrip() -> None:
    """AssessmentResult with domain_scores and reasoning_distribution serializes correctly."""
    result = _make_result(
        domain_scores={"Storage": 65.0, "Networking": 80.0},
        reasoning_distribution="Storage boosted due to gap of 5 points below threshold.",
    )

    assert result.domain_scores["Storage"] == 65.0
    assert result.reasoning_distribution is not None

    dumped = result.model_dump()
    assert dumped["domain_scores"]["Storage"] == 65.0
    assert "reasoning_distribution" in dumped

    restored = AssessmentResult.model_validate(dumped)
    assert restored.domain_scores["Networking"] == 80.0
    assert restored.reasoning_distribution == result.reasoning_distribution


# ---------------------------------------------------------------------------
# 6. GroundingReference reuse — no new model introduced
# ---------------------------------------------------------------------------


def test_grounding_reference_is_reused_not_new_model() -> None:
    """GroundingReference imported from state must be the shared model (no new model)."""
    # Verify it's the same class used by both question types
    ref = GroundingReference(title="Test", url="https://learn.microsoft.com/test")

    q = AssessmentQuestion(**{**_base_question_kwargs(), "grounding_reference": ref})
    pub = AssessmentQuestionPublic(
        id="q1",
        text="x",
        question_type="multiple_choice",
        options=["A", "B", "C", "D"],
        domain="d",
        exam_weight_pct=0.1,
        explanation="e",
        difficulty="easy",
        grounding_reference=ref,
    )

    assert type(q.grounding_reference) is GroundingReference
    assert type(pub.grounding_reference) is GroundingReference
    assert q.grounding_reference.url == pub.grounding_reference.url
