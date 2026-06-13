"""Smoke tests for the IQ grounding layer (mock providers).

All tests use real MockProviders — no patching.  The providers are
deterministic (NFR-003) so the same query always returns the same result.
Run from the backend/ directory:

    pytest tests/test_grounding.py -v
"""
from __future__ import annotations

from grounding.base import LearnerProfile, StudyAvailability, FoundryIQResult
from grounding.mock.fabric import MockFabricIQProvider
from grounding.mock.foundry import MockFoundryIQProvider
from grounding.mock.work import MockWorkIQProvider


def test_foundry_iq_search_returns_results() -> None:
    """MockFoundryIQProvider must return at least one result for a realistic query."""
    provider = MockFoundryIQProvider()
    results = provider.search("Azure Functions deployment", k=5)

    assert isinstance(results, list), "search() must return a list"
    assert len(results) >= 1, "Expected at least one result for a real query"
    for item in results:
        assert isinstance(item, FoundryIQResult), "Each result must be a FoundryIQResult"
        assert item.resource_id, "resource_id must not be empty"
        assert item.title, "title must not be empty"
        assert 0.0 <= item.relevance_score <= 1.0, "relevance_score must be in [0, 1]"


def test_fabric_iq_learner_profile_loads() -> None:
    """MockFabricIQProvider must return a LearnerProfile for a known learner ID."""
    provider = MockFabricIQProvider()
    profile = provider.learner_profile("EMP-001")

    assert isinstance(profile, LearnerProfile), "Must return a LearnerProfile"
    assert profile.learner_id == "EMP-001"
    assert profile.role, "role must not be empty"
    assert profile.target_certification, "target_certification must not be empty"
    assert isinstance(profile.skill_gaps, list), "skill_gaps must be a list"
    assert 0 <= profile.readiness_score <= 100, "readiness_score must be in [0, 100]"


def test_work_iq_fallback_returns_default() -> None:
    """MockWorkIQProvider must return 2.0 available_hours_per_day for an unknown employee ID."""
    provider = MockWorkIQProvider()
    availability = provider.availability("UNKNOWN-EMPLOYEE-9999")

    assert isinstance(availability, StudyAvailability), "Must return a StudyAvailability"
    assert availability.available_hours_per_day == 2.0, (
        f"Expected fallback of 2.0 h/day, got {availability.available_hours_per_day}"
    )
    # Must not raise — fallback contract is mandatory per design
    assert availability.employee_id == "UNKNOWN-EMPLOYEE-9999"
