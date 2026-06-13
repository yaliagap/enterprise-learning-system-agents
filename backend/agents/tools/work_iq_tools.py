"""MAF @tool functions that wrap Work IQ: study availability and calendar signals."""
from __future__ import annotations

from typing import Annotated, Any

from agent_framework import tool
from pydantic import BaseModel, Field

from grounding.base import StudyAvailability
from grounding.factory import IQProviderFactory
from workflow.state import LearnerSchedulePreferences


# ---------------------------------------------------------------------------
# Return models
# ---------------------------------------------------------------------------


class GetPreferredLearningSlotResult(BaseModel):
    """The preferred time-of-day slot for a given employee's study sessions."""

    employee_id: str
    preferred_slot: str  # e.g. "morning", "evening", "afternoon"
    source: str  # "fixture" or "default"


class GetTeamCalendarSummaryResult(BaseModel):
    """Aggregate calendar capacity summary for all members of a team."""

    team_id: str
    member_availabilities: list[StudyAvailability]
    team_average_hours_per_day: float
    bottleneck_employee_id: str | None = None  # employee with fewest available hours


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


@tool
def get_study_availability(
    employee_id: Annotated[str, Field(description="Employee identifier, e.g. 'EMP-001'.")],
) -> StudyAvailability:
    """Return the study availability snapshot for an employee, including daily hours and preferred slot."""
    work = IQProviderFactory().work()
    # WorkIQProvider.availability() never raises; returns 2h/day default for unknowns.
    return work.availability(employee_id)


@tool
def get_preferred_learning_slot(
    employee_id: Annotated[str, Field(description="Employee identifier, e.g. 'EMP-001'.")],
) -> GetPreferredLearningSlotResult:
    """Return the preferred time-of-day slot (morning/evening/afternoon) for an employee's study sessions."""
    work = IQProviderFactory().work()
    availability = work.availability(employee_id)
    return GetPreferredLearningSlotResult(
        employee_id=employee_id,
        preferred_slot=availability.preferred_slot,
        source=availability.source,
    )


@tool
def get_learner_schedule_preferences(
    employee_id: Annotated[str, Field(description="Employee identifier, e.g. 'EMP-001'.")],
) -> LearnerSchedulePreferences:
    """Return consolidated schedule preferences for an employee: preferred study days,
    session duration, time slot, and computed weekly study capacity."""
    work = IQProviderFactory().work()
    av = work.availability(employee_id)
    days = av.preferred_study_days or ["Monday", "Wednesday", "Friday"]
    cap = av.session_duration_hours * len(days)
    if cap <= 0:
        cap = 3.0
    cap = max(cap, 1.0)
    return LearnerSchedulePreferences(
        employee_id=employee_id,
        preferred_study_days=days,
        session_duration_hours=av.session_duration_hours if av.session_duration_hours > 0 else 1.0,
        preferred_slot=av.preferred_slot,
        capacity_hours_per_week=round(cap, 1),
        source=av.source,
        is_fallback=(av.source == "default"),
    )


@tool
def get_team_calendar_summary(
    team_id: Annotated[str, Field(description="Team identifier, e.g. 'TEAM-A'.")],
    member_ids: Annotated[
        list[str],
        Field(description="List of employee IDs that belong to the team, e.g. ['EMP-001', 'EMP-002']."),
    ],
) -> GetTeamCalendarSummaryResult:
    """Return an aggregate calendar capacity summary for all members of a team."""
    work = IQProviderFactory().work()
    availabilities: list[StudyAvailability] = [work.availability(eid) for eid in member_ids]

    if not availabilities:
        return GetTeamCalendarSummaryResult(
            team_id=team_id,
            member_availabilities=[],
            team_average_hours_per_day=0.0,
        )

    avg_hours = sum(a.available_hours_per_day for a in availabilities) / len(availabilities)

    # Identify bottleneck: the member with the fewest available hours
    bottleneck = min(availabilities, key=lambda a: a.available_hours_per_day)

    return GetTeamCalendarSummaryResult(
        team_id=team_id,
        member_availabilities=availabilities,
        team_average_hours_per_day=round(avg_hours, 2),
        bottleneck_employee_id=bottleneck.employee_id,
    )
