"""Unit tests for get_learner_schedule_preferences tool: TASK-09.

Covers:
- Known employee (EMP-001): all fields populated, capacity >= 1.0, is_fallback=False
- Unknown employee: is_fallback=True, fallback days, capacity >= 1.0
- Capacity floor: session_duration_hours=0 -> cap=3.0; session_duration_hours=0.25 days=2 -> cap=1.0

Run from backend/:
    pytest tests/test_study_plan_tools.py -v
"""
from __future__ import annotations

import pytest

from workflow.state import LearnerSchedulePreferences


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _call_tool(employee_id: str) -> LearnerSchedulePreferences:
    """Call the tool function directly (bypasses @tool decorator overhead)."""
    from agents.tools.work_iq_tools import get_learner_schedule_preferences

    # The @tool decorator wraps the function; call the underlying function directly.
    fn = getattr(get_learner_schedule_preferences, "__wrapped__", get_learner_schedule_preferences)
    # Also handle agent_framework's tool wrapper which may store fn in .func or .__func__
    for attr in ("func", "__func__", "_func", "fn"):
        maybe = getattr(fn, attr, None)
        if callable(maybe):
            fn = maybe
            break
    return fn(employee_id)


# ---------------------------------------------------------------------------
# Known employees
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("employee_id", ["EMP-001", "EMP-002", "EMP-003", "EMP-004", "EMP-005"])
def test_known_employee_returns_all_fields(employee_id: str) -> None:
    """Known employees must return all required fields populated."""
    result = _call_tool(employee_id)
    assert isinstance(result, LearnerSchedulePreferences)
    assert result.employee_id == employee_id
    assert len(result.preferred_study_days) > 0
    assert result.session_duration_hours > 0
    assert result.preferred_slot != ""
    assert result.capacity_hours_per_week >= 1.0
    assert result.source == "fixture"


def test_emp001_is_not_fallback() -> None:
    """EMP-001 must not be marked as fallback."""
    result = _call_tool("EMP-001")
    assert result.is_fallback is False


def test_emp001_capacity_ge_1() -> None:
    """EMP-001 capacity_hours_per_week must be >= 1.0."""
    result = _call_tool("EMP-001")
    assert result.capacity_hours_per_week >= 1.0


# ---------------------------------------------------------------------------
# Unknown employee
# ---------------------------------------------------------------------------


def test_unknown_employee_is_fallback() -> None:
    """Unknown employee must return is_fallback=True."""
    result = _call_tool("UNKNOWN-99")
    assert result.is_fallback is True


def test_unknown_employee_default_days() -> None:
    """Unknown employee must use fallback preferred_study_days."""
    result = _call_tool("UNKNOWN-99")
    assert result.preferred_study_days == ["Monday", "Wednesday", "Friday"]


def test_unknown_employee_capacity_ge_1() -> None:
    """Unknown employee capacity_hours_per_week must be >= 1.0 (floor applies)."""
    result = _call_tool("UNKNOWN-99")
    assert result.capacity_hours_per_week >= 1.0


# ---------------------------------------------------------------------------
# Capacity floor (parametrized)
# ---------------------------------------------------------------------------


def _tool_with_mocked_availability(
    session_duration_hours: float,
    preferred_study_days: list[str],
    source: str = "fixture",
) -> LearnerSchedulePreferences:
    """Helper that patches MockWorkIQProvider to return a custom StudyAvailability."""
    from unittest.mock import MagicMock, patch

    from grounding.base import StudyAvailability

    mock_av = StudyAvailability(
        employee_id="MOCK",
        available_hours_per_day=2.0,
        preferred_slot="morning",
        focus_hours_per_week=10.0,
        meeting_hours_per_week=0.0,
        source=source,
        preferred_study_days=preferred_study_days,
        session_duration_hours=session_duration_hours,
    )
    mock_work = MagicMock()
    mock_work.availability.return_value = mock_av
    mock_factory = MagicMock()
    mock_factory.return_value.work.return_value = mock_work

    with patch("agents.tools.work_iq_tools.IQProviderFactory", mock_factory):
        return _call_tool("MOCK")


def test_capacity_floor_zero_duration() -> None:
    """session_duration_hours=0 must yield capacity_hours_per_week=3.0 (default cap)."""
    result = _tool_with_mocked_availability(
        session_duration_hours=0,
        preferred_study_days=["Monday", "Wednesday", "Friday"],
        source="default",
    )
    assert result.capacity_hours_per_week == 3.0


def test_capacity_floor_small_duration_few_days() -> None:
    """session_duration_hours=0.25 with 2 days -> raw cap=0.5 -> floor to 1.0."""
    result = _tool_with_mocked_availability(
        session_duration_hours=0.25,
        preferred_study_days=["Monday", "Wednesday"],
    )
    assert result.capacity_hours_per_week == 1.0


def test_capacity_no_floor_needed() -> None:
    """session_duration_hours=2.0 with 4 days -> raw cap=8.0 -> no floor applied."""
    result = _tool_with_mocked_availability(
        session_duration_hours=2.0,
        preferred_study_days=["Monday", "Tuesday", "Wednesday", "Thursday"],
    )
    assert result.capacity_hours_per_week == 8.0


def test_session_duration_zero_returns_1_in_model() -> None:
    """When session_duration_hours=0 in availability, the model should use 1.0 as the value."""
    result = _tool_with_mocked_availability(
        session_duration_hours=0,
        preferred_study_days=["Monday", "Wednesday", "Friday"],
        source="default",
    )
    # session_duration_hours in result should be 1.0 (fallback from "if av.session_duration_hours > 0 else 1.0")
    assert result.session_duration_hours == 1.0
