"""Tests for workflow/scoring.py — all spec scenarios from assessment-scoring domain.

Run from backend/:
    pytest tests/test_scoring.py -v
"""
from __future__ import annotations

import pytest

from workflow.scoring import (
    PASS_THRESHOLD,
    compute_overall_score,
    detect_weak_areas,
    score_multi_select,
    score_multiple_choice,
    score_question,
    score_true_false,
)
from workflow.state import AssessmentQuestion, QuestionResult


# ---------------------------------------------------------------------------
# score_multiple_choice
# ---------------------------------------------------------------------------


def test_mc_correct() -> None:
    """Multiple choice: single correct answer → 1.0."""
    assert score_multiple_choice(["A"], ["A"]) == 1.0


def test_mc_wrong() -> None:
    """Multiple choice: wrong answer → 0.0."""
    assert score_multiple_choice(["B"], ["A"]) == 0.0


def test_mc_empty_user() -> None:
    """Multiple choice: no answer selected → 0.0."""
    assert score_multiple_choice([], ["A"]) == 0.0


# ---------------------------------------------------------------------------
# score_true_false
# ---------------------------------------------------------------------------


def test_tf_correct() -> None:
    """True/false: correct answer → 1.0."""
    assert score_true_false(["True"], ["True"]) == 1.0


def test_tf_wrong() -> None:
    """True/false: wrong answer → 0.0."""
    assert score_true_false(["False"], ["True"]) == 0.0


# ---------------------------------------------------------------------------
# score_multi_select — partial credit formula
# ---------------------------------------------------------------------------


def test_multi_select_all_correct() -> None:
    """Multi-select: all correct, none wrong → 1.0."""
    assert score_multi_select(["A", "B", "C"], ["A", "B", "C"]) == pytest.approx(1.0)


def test_multi_select_all_wrong() -> None:
    """Multi-select: none correct, wrong selected → 0.0 (clamped)."""
    # 0 correct_selected/3 - 2 incorrect_selected/3 = -0.67 → max(0, ...) = 0.0
    assert score_multi_select(["X", "Y"], ["A", "B", "C"]) == 0.0


def test_multi_select_partial_1_correct_1_incorrect_of_2() -> None:
    """Partial: 1 correct + 1 incorrect of 2 total correct → max(0, 1/2 - 1/2) = 0.0."""
    # Spec scenario: 1 correct, 1 incorrect of 2 total correct → 0%
    result = score_multi_select(["A", "X"], ["A", "B"])
    assert result == pytest.approx(0.0)


def test_multi_select_partial_2_correct_0_incorrect_of_3() -> None:
    """Partial: 2 correct + 0 incorrect of 3 total correct → 2/3 ≈ 0.667."""
    # Spec scenario: 2 correct, 0 incorrect of 3 total correct → 66.7%
    result = score_multi_select(["A", "B"], ["A", "B", "C"])
    assert result == pytest.approx(2 / 3, rel=1e-3)


def test_multi_select_partial_2_correct_1_incorrect_of_3() -> None:
    """Spec scenario: 2 correct + 1 incorrect of 3 total → max(0, 2/3 - 1/3) = 0.333."""
    result = score_multi_select(["A", "B", "X"], ["A", "B", "C"])
    assert result == pytest.approx(1 / 3, rel=1e-3)


# ---------------------------------------------------------------------------
# score_question — dispatch
# ---------------------------------------------------------------------------


def test_score_question_dispatches_mc() -> None:
    assert score_question("multiple_choice", ["A"], ["A"]) == 1.0


def test_score_question_dispatches_tf() -> None:
    assert score_question("true_false", ["False"], ["False"]) == 1.0


def test_score_question_dispatches_multi_select() -> None:
    assert score_question("multi_select", ["A", "B"], ["A", "B", "C"]) == pytest.approx(2 / 3, rel=1e-3)


def test_score_question_unknown_type() -> None:
    """Unknown question_type should raise ValueError."""
    with pytest.raises(ValueError):
        score_question("essay", ["answer"], ["answer"])


# ---------------------------------------------------------------------------
# compute_overall_score
# ---------------------------------------------------------------------------


def _make_result(qid: str, score: float) -> QuestionResult:
    return QuestionResult(
        question_id=qid,
        user_answers=["A"],
        correct_answers=["A"],
        is_correct=score == 1.0,
        partial_score=score,
        explanation="",
    )


def test_all_correct_100_pct() -> None:
    """15 questions all correct → overall score 100.0 → passed True."""
    results = [_make_result(f"q{i}", 1.0) for i in range(15)]
    score = compute_overall_score(results)
    assert score == pytest.approx(100.0)
    assert score >= PASS_THRESHOLD


def test_all_wrong_0_pct() -> None:
    """15 questions all wrong → overall score 0.0 → passed False."""
    results = [_make_result(f"q{i}", 0.0) for i in range(15)]
    score = compute_overall_score(results)
    assert score == pytest.approx(0.0)
    assert score < PASS_THRESHOLD


def test_exactly_at_threshold() -> None:
    """Mean score of 0.70 → overall 70.0 → passed True."""
    # 10.5 out of 15 = 0.70 → use 10 full + 5 zeros + 1 half
    # Simplest: 15 questions each with partial_score = 0.70
    results = [_make_result(f"q{i}", 0.70) for i in range(15)]
    score = compute_overall_score(results)
    assert score == pytest.approx(70.0, rel=1e-3)
    assert score >= PASS_THRESHOLD


def test_one_below_threshold() -> None:
    """Mean score of 0.699 → overall 69.9 → passed False."""
    results = [_make_result(f"q{i}", 0.699) for i in range(15)]
    score = compute_overall_score(results)
    assert score < PASS_THRESHOLD


# ---------------------------------------------------------------------------
# detect_weak_areas
# ---------------------------------------------------------------------------


def _make_question(qid: str, domain: str) -> AssessmentQuestion:
    return AssessmentQuestion(
        id=qid,
        text="Question text",
        question_type="multiple_choice",
        options=["A", "B"],
        correct_answers=["A"],
        domain=domain,
        exam_weight_pct=0.1,
        explanation="",
        difficulty="easy",
    )


def test_detect_weak_areas_identifies_below_threshold() -> None:
    """Domains with mean score < 0.70 must be returned as weak areas."""
    questions = [
        _make_question("q1", "Compute"),
        _make_question("q2", "Compute"),
        _make_question("q3", "Storage"),
        _make_question("q4", "Storage"),
    ]
    results = [
        _make_result("q1", 0.5),   # Compute: 0.5
        _make_result("q2", 0.5),   # Compute: 0.5 → avg 0.5 → weak
        _make_result("q3", 1.0),   # Storage: 1.0
        _make_result("q4", 1.0),   # Storage: 1.0 → avg 1.0 → strong
    ]
    weak = detect_weak_areas(questions, results)
    assert "Compute" in weak
    assert "Storage" not in weak


def test_detect_weak_areas_none_when_all_strong() -> None:
    """No weak areas returned when all domains score >= threshold."""
    questions = [_make_question("q1", "Identity"), _make_question("q2", "Identity")]
    results = [_make_result("q1", 0.9), _make_result("q2", 0.8)]
    assert detect_weak_areas(questions, results) == []


def test_detect_weak_areas_exactly_at_threshold_not_weak() -> None:
    """Domain at exactly 0.70 average is NOT a weak area."""
    questions = [_make_question("q1", "Networking")]
    results = [_make_result("q1", 0.70)]
    assert detect_weak_areas(questions, results) == []
