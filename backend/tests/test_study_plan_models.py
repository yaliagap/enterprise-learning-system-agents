"""Unit tests for study plan Pydantic models: TASK-08.

Covers:
- LearnerSchedulePreferences construction and round-trip
- StudyMilestone construction, defaults, and validation
- StudyPlanSession has session_id field defaulting to ""
- WorkflowState.seed() has priority_domains=[], schedule_context=None, study_milestones=[]
- LearnerSchedulePreferences with is_fallback=True serializes correctly

Run from backend/:
    pytest tests/test_study_plan_models.py -v
"""
from __future__ import annotations

import pytest

from workflow.state import (
    LearnerSchedulePreferences,
    StudyMilestone,
    StudyPlanSession,
    WorkflowState,
)


# ---------------------------------------------------------------------------
# LearnerSchedulePreferences
# ---------------------------------------------------------------------------


def test_learner_schedule_preferences_constructs() -> None:
    """LearnerSchedulePreferences must construct with all required fields."""
    prefs = LearnerSchedulePreferences(
        employee_id="EMP-001",
        preferred_study_days=["Monday", "Wednesday", "Friday"],
        session_duration_hours=2.0,
        preferred_slot="morning",
        capacity_hours_per_week=6.0,
        source="fixture",
        is_fallback=False,
    )
    assert prefs.employee_id == "EMP-001"
    assert prefs.preferred_study_days == ["Monday", "Wednesday", "Friday"]
    assert prefs.session_duration_hours == 2.0
    assert prefs.preferred_slot == "morning"
    assert prefs.capacity_hours_per_week == 6.0
    assert prefs.source == "fixture"
    assert prefs.is_fallback is False


def test_learner_schedule_preferences_round_trip() -> None:
    """LearnerSchedulePreferences must round-trip via model_dump / model_validate."""
    prefs = LearnerSchedulePreferences(
        employee_id="EMP-002",
        preferred_study_days=["Tuesday", "Thursday"],
        session_duration_hours=1.5,
        preferred_slot="evening",
        capacity_hours_per_week=3.0,
        source="fixture",
    )
    dumped = prefs.model_dump()
    restored = LearnerSchedulePreferences.model_validate(dumped)
    assert restored.employee_id == prefs.employee_id
    assert restored.preferred_study_days == prefs.preferred_study_days
    assert restored.session_duration_hours == prefs.session_duration_hours
    assert restored.capacity_hours_per_week == prefs.capacity_hours_per_week


def test_learner_schedule_preferences_is_fallback_true() -> None:
    """LearnerSchedulePreferences with is_fallback=True must serialize the flag correctly."""
    prefs = LearnerSchedulePreferences(
        employee_id="UNKNOWN",
        preferred_study_days=["Monday", "Wednesday", "Friday"],
        session_duration_hours=1.0,
        preferred_slot="flexible",
        capacity_hours_per_week=3.0,
        source="default",
        is_fallback=True,
    )
    dumped = prefs.model_dump()
    assert dumped["is_fallback"] is True
    assert dumped["source"] == "default"

    restored = LearnerSchedulePreferences.model_validate(dumped)
    assert restored.is_fallback is True


def test_learner_schedule_preferences_is_fallback_defaults_false() -> None:
    """is_fallback must default to False when not provided."""
    prefs = LearnerSchedulePreferences(
        employee_id="EMP-003",
        preferred_study_days=["Monday"],
        session_duration_hours=1.0,
        preferred_slot="afternoon",
        capacity_hours_per_week=1.0,
        source="fixture",
    )
    assert prefs.is_fallback is False


# ---------------------------------------------------------------------------
# StudyMilestone
# ---------------------------------------------------------------------------


def test_study_milestone_constructs() -> None:
    """StudyMilestone must construct with all required fields."""
    ms = StudyMilestone(
        milestone_id="milestone-01",
        domain_name="Azure Storage",
        exam_weight=0.25,
        target_week=2,
        target_date="2026-06-20",
        resource_ids=["res-001", "res-002"],
        session_ids=["session-20260614-01"],
    )
    assert ms.milestone_id == "milestone-01"
    assert ms.domain_name == "Azure Storage"
    assert ms.exam_weight == 0.25
    assert ms.target_week == 2
    assert ms.target_date == "2026-06-20"
    assert ms.resource_ids == ["res-001", "res-002"]
    assert ms.session_ids == ["session-20260614-01"]


def test_study_milestone_status_defaults_pending() -> None:
    """StudyMilestone status must default to 'pending'."""
    ms = StudyMilestone(
        milestone_id="milestone-01",
        domain_name="Compute",
        exam_weight=0.30,
        target_week=1,
        target_date="2026-06-20",
    )
    assert ms.status == "pending"


def test_study_milestone_target_week_ge_1() -> None:
    """StudyMilestone target_week must be >= 1; 0 should raise ValidationError."""
    with pytest.raises(Exception):
        StudyMilestone(
            milestone_id="milestone-01",
            domain_name="Compute",
            exam_weight=0.30,
            target_week=0,
            target_date="2026-06-20",
        )


def test_study_milestone_resource_ids_default_empty() -> None:
    """StudyMilestone resource_ids and session_ids should default to empty lists."""
    ms = StudyMilestone(
        milestone_id="milestone-02",
        domain_name="Networking",
        exam_weight=0.20,
        target_week=3,
        target_date="2026-06-27",
    )
    assert ms.resource_ids == []
    assert ms.session_ids == []


# ---------------------------------------------------------------------------
# StudyPlanSession
# ---------------------------------------------------------------------------


def test_study_plan_session_has_session_id_field() -> None:
    """StudyPlanSession must have a session_id field defaulting to ''."""
    session = StudyPlanSession(
        date="2026-06-14",
        hours=2.0,
        topics=["Azure Compute"],
        resource_ids=["res-001"],
    )
    assert hasattr(session, "session_id")
    assert session.session_id == ""


def test_study_plan_session_session_id_can_be_set() -> None:
    """StudyPlanSession session_id can be explicitly set."""
    session = StudyPlanSession(
        session_id="session-20260614-01",
        date="2026-06-14",
        hours=2.0,
        topics=["Azure Compute"],
        resource_ids=["res-001"],
    )
    assert session.session_id == "session-20260614-01"


# ---------------------------------------------------------------------------
# WorkflowState.seed
# ---------------------------------------------------------------------------


def test_workflow_state_seed_has_new_fields() -> None:
    """WorkflowState.seed() must initialize priority_domains=[], schedule_context=None, study_milestones=[]."""
    state = WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=["az900-cloud-concepts"],
        role="Cloud Engineer",
    )
    assert state.priority_domains == []
    assert state.schedule_context is None
    assert state.study_milestones == []
