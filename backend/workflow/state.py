"""Shared Pydantic v2 models: WorkflowState and all nested types used across agents."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Assessment question types
# ---------------------------------------------------------------------------

QuestionTypeLiteral = Literal["multiple_choice", "multi_select", "true_false"]
DifficultyLiteral = Literal["easy", "medium", "hard"]
BloomLevelLiteral = Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


# ---------------------------------------------------------------------------
# Nested domain models
# ---------------------------------------------------------------------------


class LearnerContext(BaseModel):
    """Identity and goal context for a single learner workflow run."""

    learner_id: str
    employee_id: str
    role: str
    roles: list[str] = Field(default_factory=list)
    seniority: str = ""
    topics: list[str] = Field(min_length=1, max_length=10)
    experience_level: str | None = None
    goals: list[str] | None = None
    current_skills: list[str] = Field(default_factory=list)
    strongest_domains: list[str] = Field(default_factory=list)


class GroundingReference(BaseModel):
    title: str
    url: str
    type: str = "web"
    score: float | None = None


class KBActivity(BaseModel):
    query: str
    response_text: str = ""
    references: list[GroundingReference] = []


class LearningPathItem(BaseModel):
    """A single resource that belongs to the learner's curated learning path."""

    resource_id: str
    title: str
    cert_id: str
    estimated_hours: float = Field(default=0.0, ge=0.0)
    source_url: str
    domain_name: str | None = None
    exam_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    citations: list[str] = Field(default_factory=list)
    necessary_learn: bool = True

    @field_validator("estimated_hours", mode="before")
    @classmethod
    def coerce_hours(cls, v: object) -> float:
        return float(v) if v is not None else 0.0


class DomainWeight(BaseModel):
    """Exam domain with its weight — used within CurationResult."""

    domain_name: str
    exam_weight: float = Field(ge=0.0, le=1.0)
    level: str = ""
    products: list[str] = Field(default_factory=list)
    icon_url: str = ""


class CurationResult(BaseModel):
    """Structured output from the Curator agent after cert inference."""

    exam: str
    user_level: str
    priority_domains: list[DomainWeight]
    recommended_learning_paths: list[LearningPathItem]
    coverage_summary: str
    references: list[GroundingReference] = []
    path_efficiency_reasoning: str = ""


class LearnerSchedulePreferences(BaseModel):
    """Consolidated schedule preferences for a learner derived from Work IQ."""

    employee_id: str
    preferred_study_days: list[str]
    session_duration_hours: float = Field(ge=0.0)
    preferred_slot: str
    capacity_hours_per_week: float = Field(ge=0.0)
    source: str  # "fixture" | "default"
    is_fallback: bool = False


class StudyMilestone(BaseModel):
    """A domain-level milestone within the learner's study plan."""

    milestone_id: str  # e.g. "milestone-01"
    domain_name: str
    exam_weight: float = Field(ge=0.0, le=1.0)
    target_week: int = Field(ge=1)
    target_date: str  # ISO 8601, end of target week
    resource_ids: list[str] = Field(default_factory=list)
    session_ids: list[str] = Field(default_factory=list)
    status: Literal["pending", "in_progress", "done"] = "pending"


class StudyPlanSession(BaseModel):
    """One scheduled study block within the learner's study plan."""

    session_id: str = ""
    date: str  # ISO 8601, e.g. "2026-07-01"
    hours: float = Field(ge=0.0)
    topics: list[str]
    resource_ids: list[str]
    topic_hours: list[float] = Field(default_factory=list)  # actual chunk hours per topic entry


class WorkIQSignals(BaseModel):
    """Work IQ engagement profile signals for a learner."""

    focusPeakStart: str
    focusPeakEnd: str
    meetingWindowStart: str
    meetingWindowEnd: str
    preferredChannel: str
    avgStreakDays: int = Field(ge=0)
    responseRateByChannel: dict[str, float]
    teamType: str


class EngagementAlert(BaseModel):
    """A single engagement alert in the learner's personalized proposal."""

    type: Literal["reminder", "milestone", "motivation", "risk"]
    channel: Literal["slack", "email"]
    timing: str
    triggerCondition: str
    previewText: str
    repeatCount: str
    reasoning: str


class EngagementProposal(BaseModel):
    """Structured engagement proposal produced by the Engagement Agent."""

    workIQSignals: WorkIQSignals
    alerts: list[EngagementAlert]
    totalAlerts: int
    totalMilestones: int
    totalWeeks: int
    activeChannels: int


class EngagementStatus(BaseModel):
    """Current engagement tracking state for the learner."""

    reminders_sent: int = Field(ge=0, default=0)
    last_contact: str | None = None  # ISO 8601 datetime or None
    preferred_slot: str  # e.g. "morning", "evening"
    next_reminder: str | None = None  # ISO 8601 datetime or None


class QuestionResponse(BaseModel):
    """A single answer recorded during an assessment attempt."""

    question_id: str
    skill: str
    is_correct: bool
    score: float = Field(ge=0.0, le=1.0)


class AssessmentQuestion(BaseModel):
    """A single assessment question generated by the LLM — includes correct answers (server-side only)."""

    id: str
    text: str
    question_type: QuestionTypeLiteral
    options: list[str]
    correct_answers: list[str]
    domain: str
    exam_weight_pct: float
    explanation: str
    difficulty: DifficultyLiteral
    bloom_level: BloomLevelLiteral = "Understand"
    is_scenario_based: bool = False
    scenario_context: str | None = None
    grounding_reference: GroundingReference | None = None


class AssessmentQuestionPublic(BaseModel):
    """Public projection of AssessmentQuestion — safe to send to the frontend via STATE_SNAPSHOT.

    Identical to AssessmentQuestion but WITHOUT correct_answers and explanation so that
    answers are never leaked to the client during an active exam.
    """

    id: str
    text: str
    question_type: QuestionTypeLiteral
    options: list[str]
    correct_answer_count: int = 0
    domain: str
    exam_weight_pct: float
    explanation: str
    difficulty: DifficultyLiteral
    bloom_level: BloomLevelLiteral = "Understand"
    is_scenario_based: bool = False
    scenario_context: str | None = None
    grounding_reference: GroundingReference | None = None


class QuestionResult(BaseModel):
    """Scoring result for a single question in an assessment attempt."""

    question_id: str
    user_answers: list[str]
    correct_answers: list[str]
    is_correct: bool
    partial_score: float = Field(ge=0.0, le=1.0)
    explanation: str


class UserAnswer(BaseModel):
    """A learner's answer to a single question."""

    question_id: str
    selected_answers: list[str]


class AssessmentAnswers(BaseModel):
    """Collection of all learner answers submitted at the end of an exam session."""

    answers: list[UserAnswer]


class AssessmentResult(BaseModel):
    """Complete result for one assessment attempt."""

    attempt: int = Field(ge=1)
    score: float = Field(ge=0.0, le=100.0)
    passed: bool
    passing_score: float = Field(ge=0.0, le=100.0)
    weak_areas: list[str]
    completed_at: str  # ISO 8601 datetime
    per_question_results: list[QuestionResult] = Field(default_factory=list)
    domain_scores: dict[str, float] = Field(default_factory=dict)
    reasoning_distribution: str | None = None


# ---------------------------------------------------------------------------
# Root workflow state
# ---------------------------------------------------------------------------

WorkflowStatusLiteral = Literal[
    "planning",
    "studying",
    "awaiting_assessment",
    "assessing",
    "exam_in_progress",
    "exam_failed",
    "passed",
    "failed",
    "max_retries_reached",
    "awaiting_cert_selection",
    "awaiting_path_confirmation",
]


class CertOption(BaseModel):
    """A certification recommendation produced by Run 1 of the Curator agent.

    Separate from CertificationInfo — carries recommendation-specific fields
    (recommendation_pct, already_obtained) that belong to the run context,
    not the static catalog.
    """

    cert_id: str
    name: str
    description: str = ""
    ms_learn_url: str = ""
    recommendation_pct: float = Field(ge=0.0, le=100.0)
    already_obtained: bool = False
    level: str = ""
    lp_uids: list[str] = Field(default_factory=list)


class WorkflowState(BaseModel):
    """Shared mutable state threaded through every step of the learning workflow.

    Each agent step reads and writes the slice of state it owns.  The full
    model is serialised as the AG-UI ``STATE_SNAPSHOT`` / ``STATE_DELTA``
    payload so the frontend can render incrementally.
    """

    # Core identity (always present, seeded by the dispatcher)
    learner: LearnerContext

    # Populated by the Curator agent after cert inference
    recommended_cert_id: str | None = None
    recommended_cert_name: str | None = None
    coverage_summary: str = ""
    grounding_references: list[GroundingReference] = []

    # Populated by the Curator agent
    learning_path: list[LearningPathItem] = Field(default_factory=list)

    # Populated by the Curator agent (Run 2) — priority exam domains
    priority_domains: list[DomainWeight] = Field(default_factory=list)

    # Populated by the StudyPlan agent via _ScheduleContextMiddleware
    schedule_context: LearnerSchedulePreferences | None = None

    # Populated by the StudyPlan agent
    study_plan: list[StudyPlanSession] = Field(default_factory=list)

    # Populated by the StudyPlan agent — domain-level milestones
    study_milestones: list[StudyMilestone] = Field(default_factory=list)

    # Populated by the Engagement agent
    engagement: EngagementStatus | None = None
    engagement_proposal: EngagementProposal | None = None

    # Populated by the Assessment agent (one entry per attempt)
    assessment_results: list[AssessmentResult] = Field(default_factory=list)

    # Retry / HITL control
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=1)
    hitl_confirmed: bool = False

    # Assessment questions (public projection — no correct answers)
    assessment_questions: list[AssessmentQuestionPublic] = Field(default_factory=list)

    # Learner answers submitted for the active exam session
    assessment_answers: AssessmentAnswers | None = None

    # Lifecycle state machine
    workflow_status: WorkflowStatusLiteral = "planning"

    # Cert recommendation fields — populated by Curator Run 1
    cert_options: list[CertOption] = Field(default_factory=list)
    selected_cert_id: str | None = None

    # Populated by the Curator agent (Run 2) — efficiency reasoning for necessary_learn markings
    path_efficiency_reasoning: str = ""

    # Attribution metadata — consumed by the frontend to label agent bubbles
    current_agent: str = ""
    kb_activity: KBActivity | None = None
    curator_response: dict | None = None

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @classmethod
    def seed(
        cls,
        learner_id: str,
        employee_id: str,
        topics: list[str],
        role: str,
        roles: list[str] | None = None,
        seniority: str = "",
        experience_level: str | None = None,
        goals: list[str] | None = None,
    ) -> "WorkflowState":
        """Create the initial state from learner identity inputs."""
        return cls(
            learner=LearnerContext(
                learner_id=learner_id,
                employee_id=employee_id,
                topics=topics,
                role=role,
                roles=roles or ([role] if role else []),
                seniority=seniority,
                experience_level=experience_level,
                goals=goals,
            )
        )

    @property
    def latest_assessment(self) -> AssessmentResult | None:
        """Return the most recent assessment result, or None if none exist."""
        return self.assessment_results[-1] if self.assessment_results else None

    @property
    def can_retry(self) -> bool:
        """True when the learner has not yet exhausted their retry budget."""
        return self.retry_count < self.max_retries
