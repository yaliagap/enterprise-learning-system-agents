"""Smoke tests for MAF tool functions.

Tests call the underlying tool logic directly (bypassing the @tool decorator
wrapper) so they remain fast and framework-independent.  The grounding layer
uses real MockProviders — no patching.

Run from the backend/ directory:

    pytest tests/test_tools.py -v
"""
from __future__ import annotations

from grounding.base import FoundryIQResult, LearnerProfile
from agents.tools.assessment_tools import (
    PracticeQuestion,
    ReadinessScoreResult,
    _build_question,
    calculate_readiness_score,
)
from agents.tools.fabric_iq_tools import get_learner_profile
from agents.tools.foundry_iq_tools import search_learning_resources
from workflow.state import QuestionResponse


def test_search_learning_resources_returns_pydantic() -> None:
    """search_learning_resources tool must return a result containing FoundryIQResult items."""
    result = search_learning_resources(query="Azure Functions deployment", top_k=3)

    assert result.results, "Expected at least one result"
    for item in result.results:
        assert isinstance(item, FoundryIQResult), (
            f"Each result item must be FoundryIQResult, got {type(item)}"
        )


def test_get_learner_profile_returns_pydantic() -> None:
    """get_learner_profile tool must return a LearnerProfile for EMP-001."""
    profile = get_learner_profile(learner_id="EMP-001")

    assert isinstance(profile, LearnerProfile), (
        f"Expected LearnerProfile, got {type(profile)}"
    )
    assert profile.learner_id == "EMP-001"
    assert profile.target_certification, "target_certification must not be empty"


def test_generate_practice_question_returns_structured() -> None:
    """generate_practice_question must return a dict-compatible object with required fields.

    Verified fields: question_id, question_text, options, correct_answer, skill.
    This test also catches the AssessmentPanel gap identified in PR-8: the
    frontend needs question_text + options in the state snapshot.
    """
    question = _build_question(cert_id="AZ-204", skill="serverless-compute", difficulty="intermediate")

    assert isinstance(question, PracticeQuestion), (
        f"Expected PracticeQuestion, got {type(question)}"
    )

    # Verify all fields required by the AssessmentPanel are present
    assert question.question_id, "question_id must not be empty"
    assert question.question_text, "question_text must not be empty"
    assert question.correct_answer, "correct_answer must not be empty"
    assert question.skill, "skill must not be empty"

    # options is the critical field for AssessmentPanel rendering (PR-8 gap fix)
    assert hasattr(question, "options"), "PracticeQuestion must expose an 'options' field"
    options = question.options
    assert isinstance(options, list), "options must be a list"
    assert len(options) >= 2, "options must contain at least 2 choices"
    assert question.correct_answer in options, "correct_answer must appear in options"

    # Serialise to dict to confirm the field survives model_dump (as used in AG-UI state)
    dumped = question.model_dump()
    assert "question_text" in dumped, "question_text must be in model_dump()"
    assert "options" in dumped, "options must be in model_dump()"
    assert "correct_answer" in dumped, "correct_answer must be in model_dump()"
    assert "skill" in dumped, "skill must be in model_dump()"
    assert "question_id" in dumped, "question_id must be in model_dump()"


def test_calculate_readiness_score_pass_threshold() -> None:
    """4-out-of-5 correct answers must produce a score >= 70 (passing threshold)."""
    responses = [
        QuestionResponse(question_id=f"Q-{i:03d}", skill="serverless-compute", is_correct=True, score=1.0)
        for i in range(4)
    ] + [
        QuestionResponse(question_id="Q-004", skill="serverless-compute", is_correct=False, score=0.0)
    ]

    result = calculate_readiness_score(responses=responses, passing_threshold=70.0)

    assert isinstance(result, ReadinessScoreResult)
    assert result.total_questions == 5
    assert result.correct_answers == 4
    assert result.overall_score == 80.0, (
        f"4/5 correct = 80.0 expected, got {result.overall_score}"
    )
    assert result.passed, "80.0 >= 70.0 should result in passed=True"
