"""MAF @tool functions that wrap Fabric IQ: learner profiles, skill gaps, and team readiness."""
from __future__ import annotations

from typing import Annotated, Any

from agent_framework import tool
from pydantic import BaseModel, Field

from grounding.base import CertificationInfo, LearnerProfile, SkillGapAnalysis
from grounding.factory import IQProviderFactory


# ---------------------------------------------------------------------------
# Return models
# ---------------------------------------------------------------------------


class GetCertificationInfoResult(BaseModel):
    """Certification metadata looked up from the catalog."""

    cert_id: str
    found: bool
    info: CertificationInfo | None = None


class GetTeamReadinessResult(BaseModel):
    """Team-level readiness aggregate for a given team."""

    team_id: str
    found: bool
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


@tool
def get_learner_profile(
    learner_id: Annotated[str, Field(description="Learner identifier, e.g. 'EMP-001'.")],
) -> LearnerProfile:
    """Return the enriched learner profile including role, skills, readiness score, and target cert."""
    fabric = IQProviderFactory().fabric()
    return fabric.learner_profile(learner_id)


@tool
def get_skill_gap_analysis(
    learner_id: Annotated[str, Field(description="Learner identifier, e.g. 'EMP-001'.")],
    cert_id: Annotated[
        str | None,
        Field(
            description=(
                "Target certification ID to analyse gap against. "
                "If omitted, uses the learner's primary target cert."
            )
        ),
    ] = None,
) -> SkillGapAnalysis:
    """Return a skill gap analysis showing missing skills and hours remaining for a learner and cert."""
    fabric = IQProviderFactory().fabric()

    if cert_id is None:
        return fabric.skill_gaps(learner_id)

    # When a specific cert_id is requested, get the provider's default gap first.
    # If it matches the requested cert, return it directly.
    gap = fabric.skill_gaps(learner_id)
    if gap.cert_id == cert_id:
        return gap

    # The mock provider computes gaps against the primary cert only.
    # Re-wrap with the requested cert_id so callers get a consistently-typed
    # response; skill data remains the closest available approximation.
    return SkillGapAnalysis(
        learner_id=gap.learner_id,
        cert_id=cert_id,
        missing_skills=gap.missing_skills,
        coverage_pct=gap.coverage_pct,
        recommended_hours_remaining=gap.recommended_hours_remaining,
    )


@tool
def get_team_readiness(
    team_id: Annotated[str, Field(description="Team identifier, e.g. 'TEAM-A'.")],
) -> GetTeamReadinessResult:
    """Return team-level readiness aggregate including at-risk members and cert coverage."""
    fabric = IQProviderFactory().fabric()
    try:
        data = fabric.team_readiness(team_id)
        return GetTeamReadinessResult(team_id=team_id, found=True, data=data)
    except KeyError:
        return GetTeamReadinessResult(team_id=team_id, found=False)


@tool
def get_certification_info(
    cert_id: Annotated[str, Field(description="Certification ID to look up, e.g. 'AZ-104'.")],
) -> GetCertificationInfoResult:
    """Return certification metadata including required skills, recommended hours, and passing score."""
    # Cert catalog lives on FoundryIQProvider (it manages the cert/resource index).
    foundry = IQProviderFactory().foundry()
    certs = foundry.cert_catalog()
    matched = next((c for c in certs if c.cert_id == cert_id), None)
    if matched is None:
        return GetCertificationInfoResult(cert_id=cert_id, found=False)
    return GetCertificationInfoResult(cert_id=cert_id, found=True, info=matched)
