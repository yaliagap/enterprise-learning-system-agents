"""Abstract base classes (ports) and Pydantic return types for all three IQ provider families."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic return models
# ---------------------------------------------------------------------------


class FoundryIQResult(BaseModel):
    """A single resource returned by a Foundry IQ semantic search."""

    resource_id: str
    title: str
    content: str
    source_url: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    citation: str  # Human-readable citation string, e.g. "RES-001 — Azure Fundamentals"


class LearnerProfile(BaseModel):
    """Learner profile loaded from learner_profiles.json."""

    learner_id: str
    employee_id: str  # Alias for learner_id used in cross-fixture joins
    role: str  # Primary role label (legacy — kept for back-compat; equals roles[0] when populated)
    seniority: str = ""
    target_certification: str  # First/primary target cert
    skill_gaps: list[str]
    readiness_score: int = Field(ge=0, le=100)
    hours_studied: float = Field(ge=0.0)

    # Enriched fields — populated from learner_profiles.json
    roles: list[str] = Field(default_factory=list)
    current_skills: list[str] = Field(default_factory=list)
    completed_certs: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)


class CertificationInfo(BaseModel):
    """Certification entry from certification_catalog.json."""

    cert_id: str
    name: str
    skills: list[str]
    recommended_hours: int
    passing_score: int
    prerequisites: list[str]
    description: str = ""
    level: str = ""
    ms_learn_url: str = ""


class StudyAvailability(BaseModel):
    """Work IQ availability snapshot for a single employee."""

    employee_id: str
    available_hours_per_day: float = Field(ge=0.0)
    preferred_slot: str  # e.g. "evening", "morning"
    focus_hours_per_week: float = Field(ge=0.0)
    meeting_hours_per_week: float = Field(ge=0.0)
    source: str = "fixture"  # "fixture" | "default" for fallback cases
    preferred_study_days: list[str] = Field(default_factory=list)
    session_duration_hours: float = Field(default=1.0, ge=0.0)


class SkillGapAnalysis(BaseModel):
    """Computed skill gap between a learner and a target certification."""

    learner_id: str
    cert_id: str
    missing_skills: list[str]
    coverage_pct: float = Field(ge=0.0, le=100.0)
    recommended_hours_remaining: float = Field(ge=0.0)


# ---------------------------------------------------------------------------
# Abstract provider ports
# ---------------------------------------------------------------------------


class FoundryIQProvider(ABC):
    """Port for Foundry IQ: semantic resource retrieval backed by ChromaDB."""

    @abstractmethod
    def search(
        self,
        query: str,
        cert_ids: list[str] | None = None,
        k: int = 5,
    ) -> list[FoundryIQResult]:
        """Return the top-k resources most relevant to *query*.

        Args:
            query: Natural-language search string.
            cert_ids: Optional list of cert IDs to filter candidates.
            k: Maximum number of results to return.

        Returns:
            List of FoundryIQResult, ordered by descending relevance_score.
        """

    @abstractmethod
    def cert_catalog(self) -> list[CertificationInfo]:
        """Return the full certification catalog."""


class FabricIQProvider(ABC):
    """Port for Fabric IQ: learner analytics and team readiness from fixtures."""

    @abstractmethod
    def skill_gaps(self, learner_id: str) -> SkillGapAnalysis:
        """Return skill gap analysis for *learner_id* against their primary target cert."""

    @abstractmethod
    def learner_profile(self, learner_id: str) -> LearnerProfile:
        """Return the enriched learner profile for *learner_id*."""

    @abstractmethod
    def team_readiness(self, team_id: str) -> dict:
        """Return the raw team aggregate record for *team_id*."""


class WorkIQProvider(ABC):
    """Port for Work IQ: calendar-driven availability signals."""

    @abstractmethod
    def availability(self, employee_id: str) -> StudyAvailability:
        """Return study availability for *employee_id*.

        Implementations MUST never raise for unknown IDs; return a safe
        default (2 h/day) instead so the study-plan step is never blocked.
        """
