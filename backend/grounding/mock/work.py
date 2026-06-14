"""Mock Work IQ provider: returns learner availability from calendar_signals.json with 2h/day fallback."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from grounding.base import StudyAvailability, WorkIQProvider
from observability.otel import trace_iq_call

_FIXTURES_DIR = Path(__file__).parent.parent.parent / "data" / "fixtures"
_LOG = logging.getLogger(__name__)

# Default availability returned when employee is unknown or the provider is
# disabled.  Per design, the absence of Work IQ data MUST NOT block the core
# study-plan flow (spec: Out-of-Scope for P3; design fallback rule).
_DEFAULT_AVAILABILITY = StudyAvailability(
    employee_id="default",
    available_hours_per_day=2.0,
    preferred_slot="flexible",
    focus_hours_per_week=10.0,
    meeting_hours_per_week=0.0,
    source="default",
    preferred_study_days=["Monday", "Wednesday", "Friday"],
    session_duration_hours=1.0,
)


@lru_cache(maxsize=1)
def _calendar_signals() -> dict[str, dict]:
    """Return a mapping of learner_id → calendar signal dict (cached)."""
    path = _FIXTURES_DIR / "calendar_signals.json"
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return {s["learner_id"]: s for s in data["calendar_signals"]}


def _pick_preferred_slot(focus_blocks: list[str]) -> str:
    """Return the first focus-time block label, or 'flexible' if empty."""
    return focus_blocks[0] if focus_blocks else "flexible"


class MockWorkIQProvider(WorkIQProvider):
    """Work IQ backed by calendar_signals.json.

    Fallback contract (MANDATORY per design):
    - If the employee_id is not found in the fixture → return default 2h/day.
    - If the fixture file is missing or malformed → log a warning and return default.
    - This method MUST NOT raise for any input — the study-plan step depends on this.
    """

    def availability(self, employee_id: str) -> StudyAvailability:
        """Return study availability for *employee_id*.

        Always returns a valid StudyAvailability.  Falls back to the 2h/day
        default rather than raising, per design requirements.
        """
        with trace_iq_call("work_iq", "get_availability"):
            try:
                signals = _calendar_signals()
            except Exception as exc:  # noqa: BLE001
                _LOG.warning(
                    "Work IQ: failed to load calendar_signals.json (%s); "
                    "returning default availability for %s.",
                    exc,
                    employee_id,
                )
                return _DEFAULT_AVAILABILITY.model_copy(update={"employee_id": employee_id})

            signal = signals.get(employee_id)
            if signal is None:
                _LOG.info(
                    "Work IQ: employee '%s' not found in calendar signals; "
                    "returning default 2h/day availability.",
                    employee_id,
                )
                return _DEFAULT_AVAILABILITY.model_copy(update={"employee_id": employee_id})

            # Derive a per-day budget from the weekly focus hours, capped to a
            # reasonable maximum so the study-plan step never over-schedules.
            focus_per_week: float = float(signal.get("focus_hours_per_week", 10.0))
            # 5 working days; floor at 0, cap at deep_work_capacity from fixture
            deep_work_cap: float = float(signal.get("deep_work_capacity_hours_per_day", 2.0))
            available_per_day = min(round(focus_per_week / 5, 1), deep_work_cap)

            focus_blocks: list[str] = signal.get("focus_time_blocks", [])

            return StudyAvailability(
                employee_id=employee_id,
                available_hours_per_day=available_per_day,
                preferred_slot=_pick_preferred_slot(focus_blocks),
                focus_hours_per_week=focus_per_week,
                meeting_hours_per_week=float(signal.get("meeting_hours_per_week", 0.0)),
                source="fixture",
                preferred_study_days=signal.get("preferred_study_days", ["Monday", "Wednesday", "Friday"]),
                session_duration_hours=float(signal.get("session_duration_hours", 1.0)),
            )

    def engagement_profile(self, employee_id: str) -> "EngagementProfile":
        """Return the Work IQ engagement profile for *employee_id*.

        Raises KeyError if the employee is not found in fixture data.
        This method intentionally raises (unlike availability()) so the
        Engagement Agent surfaces missing-data assumptions in reasoning.
        """
        from agents.tools.work_iq_tools import EngagementProfile  # noqa: PLC0415

        signals = _calendar_signals()
        signal = signals.get(employee_id)
        if signal is None:
            raise KeyError(f"No engagement profile for employee '{employee_id}'")
        return EngagementProfile(
            employee_id=employee_id,
            focusPeakStart=signal["focusPeakStart"],
            focusPeakEnd=signal["focusPeakEnd"],
            meetingWindowStart=signal["meetingWindowStart"],
            meetingWindowEnd=signal["meetingWindowEnd"],
            preferredChannel=signal["preferredChannel"],
            avgStreakDays=int(signal["avgStreakDays"]),
            responseRateByChannel=signal["responseRateByChannel"],
            teamType=signal["teamType"],
        )
