"""MAF @tool functions for assessment: question generation, answer evaluation, and readiness scoring."""
from __future__ import annotations

import hashlib
from typing import Annotated, Literal

from agent_framework import tool
from pydantic import BaseModel, Field, computed_field

from grounding.factory import IQProviderFactory
from workflow.state import QuestionResponse


# ---------------------------------------------------------------------------
# Domain models specific to assessment tools
# ---------------------------------------------------------------------------


class PracticeQuestion(BaseModel):
    """A single practice question generated for a skill and certification."""

    question_id: str  # Deterministic: sha1(cert_id + skill + difficulty)[:12]
    cert_id: str
    skill: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    question_text: str
    correct_answer: str
    distractors: list[str]  # 3 plausible wrong answers
    explanation: str

    @computed_field  # type: ignore[misc]
    @property
    def options(self) -> list[str]:
        """Return all answer choices (correct answer + distractors) in a stable order.

        The correct answer is always placed at index 0 so that deterministic
        tests can reference it by position without needing to shuffle.  The
        frontend MAY shuffle the options before displaying them to the learner.
        """
        return [self.correct_answer] + self.distractors


class EvaluateAnswerResult(BaseModel):
    """Result of evaluating a learner's answer against the correct answer."""

    question_id: str
    learner_answer: str
    correct_answer: str
    is_correct: bool
    score: float = Field(ge=0.0, le=1.0)
    feedback: str


class ReadinessScoreResult(BaseModel):
    """Aggregated readiness score computed from a set of question responses."""

    total_questions: int
    correct_answers: int
    overall_score: float = Field(ge=0.0, le=100.0)
    passed: bool
    passing_threshold: float = Field(ge=0.0, le=100.0)
    skill_breakdown: dict[str, float]  # skill → score (0.0–1.0)
    weak_areas: list[str]  # skills with score < 0.6


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DIFFICULTY_TEMPLATES: dict[str, dict[str, str]] = {
    "beginner": {
        "prefix": "What is the primary purpose of",
        "suffix": "in Azure certification {cert_id}?",
        "correct_template": "It provides foundational capabilities for {skill} within Azure.",
        "explanation_template": (
            "{skill} is a core concept in {cert_id}. "
            "At the beginner level it covers basic definitions, use cases, and how the service fits into the Azure ecosystem."
        ),
    },
    "intermediate": {
        "prefix": "When implementing",
        "suffix": "for {cert_id}, which approach is most appropriate for production workloads?",
        "correct_template": "Apply best-practice configurations for {skill}, including monitoring, scaling, and access controls.",
        "explanation_template": (
            "At intermediate level, {skill} requires understanding operational patterns, "
            "not just definitions. The {cert_id} exam tests practical implementation knowledge."
        ),
    },
    "advanced": {
        "prefix": "In a complex enterprise scenario requiring",
        "suffix": "({cert_id}), what is the recommended architectural approach to ensure high availability and cost efficiency?",
        "correct_template": (
            "Design a multi-region, auto-scaling solution for {skill} with "
            "redundancy, observability, and cost guardrails."
        ),
        "explanation_template": (
            "Advanced {skill} questions in {cert_id} focus on architecture trade-offs: "
            "HA vs cost, vendor lock-in, and enterprise compliance requirements."
        ),
    },
}

_DISTRACTOR_TEMPLATES = [
    "Use the default single-region configuration with no monitoring.",
    "Rely on manual processes and avoid automation to reduce complexity.",
    "Skip access controls since the workload is internal-only.",
]


def _make_question_id(cert_id: str, skill: str, difficulty: str) -> str:
    """Generate a deterministic question ID from cert, skill, and difficulty."""
    raw = f"{cert_id}:{skill}:{difficulty}"
    return "Q-" + hashlib.sha1(raw.encode()).hexdigest()[:10].upper()


def _build_question(cert_id: str, skill: str, difficulty: str) -> PracticeQuestion:
    """Construct a deterministic PracticeQuestion from templates."""
    tmpl = _DIFFICULTY_TEMPLATES[difficulty]
    question_text = f"{tmpl['prefix']} {skill} {tmpl['suffix'].format(cert_id=cert_id)}"
    correct = tmpl["correct_template"].format(skill=skill)
    explanation = tmpl["explanation_template"].format(skill=skill, cert_id=cert_id)

    return PracticeQuestion(
        question_id=_make_question_id(cert_id, skill, difficulty),
        cert_id=cert_id,
        skill=skill,
        difficulty=difficulty,  # type: ignore[arg-type]
        question_text=question_text,
        correct_answer=correct,
        distractors=_DISTRACTOR_TEMPLATES[:],
        explanation=explanation,
    )


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


@tool
def generate_practice_question(
    skill: Annotated[str, Field(description="The skill module to generate a question for, e.g. 'azure-architecture-services'.")],
    cert_id: Annotated[str, Field(description="Target certification ID, e.g. 'AZ-104'.")],
    difficulty: Annotated[
        Literal["beginner", "intermediate", "advanced"],
        Field(description="Question difficulty level: 'beginner', 'intermediate', or 'advanced'."),
    ] = "intermediate",
) -> PracticeQuestion:
    """Generate a deterministic practice question for a given skill and certification."""
    # Validate the skill belongs to the cert via the Foundry IQ catalog.
    foundry = IQProviderFactory().foundry()
    certs = foundry.cert_catalog()
    cert_info = next((c for c in certs if c.cert_id == cert_id), None)

    if cert_info is None:
        # Unknown cert: generate the question anyway but note no catalog validation.
        return _build_question(cert_id, skill, difficulty)

    # If the skill isn't in the catalog, use the first listed skill as a fallback
    # to ensure we always return a valid question rather than raising.
    valid_skills = cert_info.skills
    resolved_skill = skill if skill in valid_skills else (valid_skills[0] if valid_skills else skill)

    return _build_question(cert_id, resolved_skill, difficulty)


@tool
def evaluate_answer(
    question_id: Annotated[str, Field(description="The question_id returned by generate_practice_question.")],
    answer: Annotated[str, Field(description="The learner's answer text.")],
    correct_answer: Annotated[str, Field(description="The correct answer text from the generated question.")],
) -> EvaluateAnswerResult:
    """Evaluate a learner's answer against the correct answer and return a scored result."""
    # Deterministic scoring: exact match or substring containment.
    # Normalise whitespace and case for a lenient but reproducible comparison.
    def _normalise(text: str) -> str:
        return " ".join(text.lower().split())

    norm_answer = _normalise(answer)
    norm_correct = _normalise(correct_answer)

    # Exact match → full score
    if norm_answer == norm_correct:
        is_correct = True
        score = 1.0
        feedback = "Correct. Your answer matches the expected response exactly."
    # Partial match: answer contains the key phrase or vice-versa → partial score
    elif norm_answer in norm_correct or norm_correct in norm_answer:
        # Treat as correct if the overlap covers at least 60% of the correct answer words
        correct_words = set(norm_correct.split())
        answer_words = set(norm_answer.split())
        overlap = len(correct_words & answer_words) / max(len(correct_words), 1)
        if overlap >= 0.6:
            is_correct = True
            score = round(0.7 + 0.3 * overlap, 2)
            feedback = "Mostly correct. Your answer captures the key idea."
        else:
            is_correct = False
            score = round(overlap * 0.5, 2)
            feedback = f"Partially correct. Expected: {correct_answer}"
    else:
        is_correct = False
        score = 0.0
        feedback = f"Incorrect. The correct answer is: {correct_answer}"

    return EvaluateAnswerResult(
        question_id=question_id,
        learner_answer=answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
        score=score,
        feedback=feedback,
    )


@tool
def calculate_readiness_score(
    responses: Annotated[
        list[QuestionResponse],
        Field(description="List of QuestionResponse records from the learner's assessment attempt."),
    ],
    passing_threshold: Annotated[
        float,
        Field(description="Minimum score (0–100) required to pass. Defaults to 70.", ge=0.0, le=100.0),
    ] = 70.0,
) -> ReadinessScoreResult:
    """Calculate overall readiness score and per-skill breakdown from a list of question responses."""
    if not responses:
        return ReadinessScoreResult(
            total_questions=0,
            correct_answers=0,
            overall_score=0.0,
            passed=False,
            passing_threshold=passing_threshold,
            skill_breakdown={},
            weak_areas=[],
        )

    total = len(responses)
    correct = sum(1 for r in responses if r.is_correct)
    overall = round((correct / total) * 100, 2)

    # Per-skill score: average score across all responses for each skill
    skill_scores: dict[str, list[float]] = {}
    for r in responses:
        skill_scores.setdefault(r.skill, []).append(r.score)

    skill_breakdown: dict[str, float] = {
        skill: round(sum(scores) / len(scores), 3)
        for skill, scores in skill_scores.items()
    }

    weak_areas = [skill for skill, avg in skill_breakdown.items() if avg < 0.6]

    return ReadinessScoreResult(
        total_questions=total,
        correct_answers=correct,
        overall_score=overall,
        passed=overall >= passing_threshold,
        passing_threshold=passing_threshold,
        skill_breakdown=skill_breakdown,
        weak_areas=weak_areas,
    )
