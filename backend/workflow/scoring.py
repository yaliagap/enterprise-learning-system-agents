"""Pure scoring functions for the assessment domain.

No MAF or LLM dependencies — all logic is deterministic and unit-testable.
"""
from __future__ import annotations

from workflow.state import AssessmentQuestion, QuestionResult

PASS_THRESHOLD: float = 70.0


# ---------------------------------------------------------------------------
# Per-question scoring
# ---------------------------------------------------------------------------


def score_multiple_choice(user_answers: list[str], correct_answers: list[str]) -> float:
    """Score a multiple-choice question: 1.0 if the single answer matches, else 0.0."""
    if not user_answers or not correct_answers:
        return 0.0
    return 1.0 if user_answers[0] == correct_answers[0] else 0.0


def score_true_false(user_answers: list[str], correct_answers: list[str]) -> float:
    """Score a true/false question: 1.0 if the answer matches, else 0.0."""
    if not user_answers or not correct_answers:
        return 0.0
    return 1.0 if user_answers[0] == correct_answers[0] else 0.0


def score_multi_select(user_answers: list[str], correct_answers: list[str]) -> float:
    """Score a multi-select question with partial credit.

    Formula: max(0, correct_selected / total_correct - incorrect_selected / total_correct)
    """
    if not correct_answers:
        return 0.0

    user_set = set(user_answers)
    correct_set = set(correct_answers)
    total_correct = len(correct_set)

    correct_selected = len(user_set & correct_set)
    incorrect_selected = len(user_set - correct_set)

    raw = correct_selected / total_correct - incorrect_selected / total_correct
    return max(0.0, raw)


def score_question(
    question_type: str,
    user_answers: list[str],
    correct_answers: list[str],
) -> float:
    """Dispatch scoring by question type.

    Args:
        question_type: One of "multiple_choice", "true_false", "multi_select".
        user_answers: The answers selected by the learner.
        correct_answers: The expected correct answers.

    Returns:
        A float in [0.0, 1.0] representing the per-question score.

    Raises:
        ValueError: If question_type is not a recognised type.
    """
    if question_type == "multiple_choice":
        return score_multiple_choice(user_answers, correct_answers)
    elif question_type == "true_false":
        return score_true_false(user_answers, correct_answers)
    elif question_type == "multi_select":
        return score_multi_select(user_answers, correct_answers)
    else:
        raise ValueError(f"Unknown question_type: {question_type!r}")


# ---------------------------------------------------------------------------
# Overall score
# ---------------------------------------------------------------------------


def compute_overall_score(results: list[QuestionResult]) -> float:
    """Compute the overall assessment score as the mean of per-question partial_scores × 100.

    Args:
        results: List of QuestionResult objects with partial_score in [0, 1].

    Returns:
        A float in [0.0, 100.0].
    """
    if not results:
        return 0.0
    return (sum(r.partial_score for r in results) / len(results)) * 100.0


# ---------------------------------------------------------------------------
# Weak area detection
# ---------------------------------------------------------------------------


def detect_weak_areas(
    questions: list[AssessmentQuestion],
    results: list[QuestionResult],
    threshold: float = 0.7,
) -> list[str]:
    """Identify domains where the learner's average per-question score is below threshold.

    Args:
        questions: The full question set with domain information.
        results: Scored results aligned by question_id.
        threshold: Domain score threshold below which a domain is considered weak (default 0.7).

    Returns:
        A list of domain names that scored below the threshold.
    """
    # Build a lookup of question_id → domain
    domain_by_id: dict[str, str] = {q.id: q.domain for q in questions}

    # Accumulate scores per domain
    domain_scores: dict[str, list[float]] = {}
    for result in results:
        domain = domain_by_id.get(result.question_id)
        if domain is None:
            continue
        domain_scores.setdefault(domain, []).append(result.partial_score)

    weak: list[str] = []
    for domain, scores in domain_scores.items():
        avg = sum(scores) / len(scores)
        if avg < threshold:
            weak.append(domain)

    return weak
