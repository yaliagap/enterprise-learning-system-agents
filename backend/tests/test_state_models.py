"""Tests for assessment-related state models added in T1.

Run from backend/:
    pytest tests/test_state_models.py -v
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from workflow.state import (
    AssessmentAnswers,
    AssessmentQuestion,
    AssessmentQuestionPublic,
    AssessmentResult,
    QuestionResult,
    UserAnswer,
    WorkflowState,
    WorkflowStatusLiteral,
)


# ---------------------------------------------------------------------------
# AssessmentQuestion
# ---------------------------------------------------------------------------


def test_assessment_question_valid() -> None:
    """AssessmentQuestion must accept all required fields with valid literals."""
    q = AssessmentQuestion(
        id="q1",
        text="What is Azure?",
        question_type="multiple_choice",
        options=["A cloud platform", "A database", "An OS", "A language"],
        correct_answers=["A cloud platform"],
        domain="Cloud Concepts",
        exam_weight_pct=0.25,
        explanation="Azure is Microsoft's cloud platform.",
        difficulty="easy",
    )
    assert q.id == "q1"
    assert q.question_type == "multiple_choice"
    assert q.difficulty == "easy"
    assert q.correct_answers == ["A cloud platform"]


def test_assessment_question_invalid_type() -> None:
    """AssessmentQuestion must raise ValidationError for invalid question_type."""
    with pytest.raises(ValidationError):
        AssessmentQuestion(
            id="q1",
            text="Essay question",
            question_type="essay",  # invalid
            options=[],
            correct_answers=["anything"],
            domain="General",
            exam_weight_pct=0.1,
            explanation="n/a",
            difficulty="easy",
        )


def test_assessment_question_invalid_difficulty() -> None:
    """AssessmentQuestion must raise ValidationError for invalid difficulty."""
    with pytest.raises(ValidationError):
        AssessmentQuestion(
            id="q2",
            text="Some question",
            question_type="true_false",
            options=["True", "False"],
            correct_answers=["True"],
            domain="Security",
            exam_weight_pct=0.1,
            explanation="n/a",
            difficulty="beginner",  # invalid — not in Literal
        )


# ---------------------------------------------------------------------------
# AssessmentQuestionPublic — correct_answers must NOT be present
# ---------------------------------------------------------------------------


def test_assessment_question_public_no_correct_answers() -> None:
    """AssessmentQuestionPublic must NOT have a correct_answers field."""
    pub = AssessmentQuestionPublic(
        id="q1",
        text="What is Azure?",
        question_type="multiple_choice",
        options=["A cloud platform", "A database", "An OS", "A language"],
        domain="Cloud Concepts",
        exam_weight_pct=0.25,
        explanation="Azure is Microsoft's cloud platform.",
        difficulty="easy",
    )
    assert not hasattr(pub, "correct_answers"), (
        "AssessmentQuestionPublic must NOT expose correct_answers"
    )


def test_assessment_question_public_rejects_correct_answers_field() -> None:
    """AssessmentQuestionPublic must not accept correct_answers as a constructor kwarg."""
    # Pydantic v2 with model_config extra="forbid" raises; with "ignore" it silently drops.
    # Either behaviour is acceptable — the field must not appear in the model output.
    pub = AssessmentQuestionPublic(
        id="q2",
        text="True or False?",
        question_type="true_false",
        options=["True", "False"],
        domain="Identity",
        exam_weight_pct=0.1,
        explanation="explanation",
        difficulty="medium",
    )
    dumped = pub.model_dump()
    assert "correct_answers" not in dumped


# ---------------------------------------------------------------------------
# QuestionResult
# ---------------------------------------------------------------------------


def test_question_result_fields() -> None:
    """QuestionResult must contain all required fields."""
    qr = QuestionResult(
        question_id="q1",
        user_answers=["A cloud platform"],
        correct_answers=["A cloud platform"],
        is_correct=True,
        partial_score=1.0,
        explanation="Correct!",
    )
    assert qr.question_id == "q1"
    assert qr.is_correct is True
    assert qr.partial_score == 1.0


# ---------------------------------------------------------------------------
# AssessmentAnswers / UserAnswer
# ---------------------------------------------------------------------------


def test_assessment_answers_model() -> None:
    """AssessmentAnswers must hold a list of UserAnswer objects."""
    answers = AssessmentAnswers(
        answers=[
            UserAnswer(question_id="q1", selected_answers=["A"]),
            UserAnswer(question_id="q2", selected_answers=["B", "C"]),
        ]
    )
    assert len(answers.answers) == 2
    assert answers.answers[0].question_id == "q1"


# ---------------------------------------------------------------------------
# WorkflowStatusLiteral — "exam_in_progress" must be valid
# ---------------------------------------------------------------------------


def test_exam_in_progress_is_valid_status() -> None:
    """WorkflowState must accept 'exam_in_progress' as workflow_status without error."""
    state = WorkflowState.seed(
        learner_id="EMP-TEST",
        employee_id="EMP-TEST",
        topics=["az900-cloud-concepts"],
        role="Student",
    )
    state.workflow_status = "exam_in_progress"  # type: ignore[assignment]
    # Re-validate via model_validate to confirm Pydantic accepts it
    revalidated = WorkflowState.model_validate(state.model_dump())
    assert revalidated.workflow_status == "exam_in_progress"


# ---------------------------------------------------------------------------
# AssessmentResult extensions
# ---------------------------------------------------------------------------


def test_assessment_result_has_per_question_results() -> None:
    """AssessmentResult must include per_question_results defaulting to empty list."""
    result = AssessmentResult(
        attempt=1,
        score=80.0,
        passed=True,
        passing_score=70.0,
        weak_areas=[],
        completed_at="2026-06-11T00:00:00Z",
    )
    assert hasattr(result, "per_question_results")
    assert result.per_question_results == []


def test_assessment_result_per_question_results_populated() -> None:
    """AssessmentResult per_question_results can hold QuestionResult entries."""
    qr = QuestionResult(
        question_id="q1",
        user_answers=["True"],
        correct_answers=["True"],
        is_correct=True,
        partial_score=1.0,
        explanation="Correct.",
    )
    result = AssessmentResult(
        attempt=1,
        score=100.0,
        passed=True,
        passing_score=70.0,
        weak_areas=[],
        completed_at="2026-06-11T00:00:00Z",
        per_question_results=[qr],
    )
    assert len(result.per_question_results) == 1


# ---------------------------------------------------------------------------
# WorkflowState new fields
# ---------------------------------------------------------------------------


def test_workflow_state_assessment_questions_default_empty() -> None:
    """WorkflowState.assessment_questions must default to empty list."""
    state = WorkflowState.seed(
        learner_id="EMP-X",
        employee_id="EMP-X",
        topics=["az900-cloud-concepts"],
        role="Student",
    )
    assert state.assessment_questions == []


def test_workflow_state_assessment_answers_default_none() -> None:
    """WorkflowState.assessment_answers must default to None."""
    state = WorkflowState.seed(
        learner_id="EMP-X",
        employee_id="EMP-X",
        topics=["az900-cloud-concepts"],
        role="Student",
    )
    assert state.assessment_answers is None
