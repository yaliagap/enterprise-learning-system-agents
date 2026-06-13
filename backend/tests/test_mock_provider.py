"""Tests for MockFabricIQProvider mapping of enriched LearnerProfile fields.

TDD: T1.6 — tests written before implementation update.
"""
from __future__ import annotations

from grounding.mock.fabric import MockFabricIQProvider


class TestMockProviderFieldMapping:
    """Capability 1: mock provider populates new LearnerProfile fields."""

    def setup_method(self) -> None:
        self.provider = MockFabricIQProvider()

    def test_full_entry_populates_roles(self) -> None:
        """EMP-001 has roles in fixture — provider must surface them."""
        profile = self.provider.learner_profile("EMP-001")
        assert isinstance(profile.roles, list)
        assert len(profile.roles) >= 1
        assert "Cloud Engineer" in profile.roles or profile.roles[0] != ""

    def test_full_entry_populates_seniority(self) -> None:
        profile = self.provider.learner_profile("EMP-001")
        assert profile.seniority == "mid"

    def test_full_entry_populates_current_skills(self) -> None:
        profile = self.provider.learner_profile("EMP-001")
        assert isinstance(profile.current_skills, list)
        assert len(profile.current_skills) >= 1

    def test_full_entry_populates_completed_certs(self) -> None:
        profile = self.provider.learner_profile("EMP-001")
        assert isinstance(profile.completed_certs, list)
        # EMP-001 has completed_certs: ["AZ-900"]
        assert "AZ-900" in profile.completed_certs

    def test_full_entry_populates_goals(self) -> None:
        profile = self.provider.learner_profile("EMP-001")
        assert isinstance(profile.goals, list)
        assert len(profile.goals) >= 1

    def test_role_equals_roles_zero_when_roles_nonempty(self) -> None:
        """Back-compat: role == roles[0] when roles list is non-empty."""
        profile = self.provider.learner_profile("EMP-001")
        if profile.roles:
            assert profile.role == profile.roles[0]

    def test_emp002_senior_data_engineer(self) -> None:
        """EMP-002 is a senior Data Engineer — check seniority and roles."""
        profile = self.provider.learner_profile("EMP-002")
        assert profile.seniority == "senior"
        assert "Data Engineer" in profile.roles

    def test_all_learners_do_not_raise(self) -> None:
        """Every learner in the fixture must load without raising."""
        from grounding.mock.fabric import _learner_profiles
        profiles = _learner_profiles()
        for learner_id in profiles:
            # Must not raise
            self.provider.learner_profile(learner_id)
