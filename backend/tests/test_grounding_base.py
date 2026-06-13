"""Tests for enriched LearnerProfile and CertificationInfo models.

TDD: T1.2 — tests written against the target contract.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from grounding.base import CertificationInfo, LearnerProfile


# ---------------------------------------------------------------------------
# LearnerProfile — new fields
# ---------------------------------------------------------------------------


class TestLearnerProfileNewFields:
    """Capability 1: LearnerProfile enrichment."""

    def test_full_json_data_populates_all_new_fields(self) -> None:
        """All five new fields are populated from full JSON data."""
        profile = LearnerProfile(
            learner_id="EMP-001",
            employee_id="EMP-001",
            role="Cloud Engineer",
            target_certification="AZ-104",
            skill_gaps=["identity", "governance"],
            readiness_score=58,
            hours_studied=24.0,
            roles=["Cloud Engineer", "DevOps Engineer"],
            seniority="mid",
            current_skills=["python", "ci-cd", "docker"],
            completed_certs=["AZ-900"],
            goals=["Pass AZ-104 by Q3"],
        )
        assert profile.roles == ["Cloud Engineer", "DevOps Engineer"]
        assert profile.seniority == "mid"
        assert profile.current_skills == ["python", "ci-cd", "docker"]
        assert profile.completed_certs == ["AZ-900"]
        assert profile.goals == ["Pass AZ-104 by Q3"]

    def test_legacy_entry_defaults_new_fields_without_exception(self) -> None:
        """Legacy entries (missing new fields) default gracefully — no exception raised."""
        # Minimum required fields only; all new fields absent → defaults
        profile = LearnerProfile(
            learner_id="LEGACY-001",
            employee_id="LEGACY-001",
            role="Network Engineer",
            target_certification="AZ-700",
            skill_gaps=[],
            readiness_score=50,
            hours_studied=0.0,
            # seniority, roles, current_skills, completed_certs, goals intentionally omitted
        )
        assert profile.roles == []
        assert profile.seniority == ""
        assert profile.current_skills == []
        assert profile.completed_certs == []
        assert profile.goals == []

    def test_legacy_fields_still_present_after_enrichment(self) -> None:
        """Legacy fields (role, skill_gaps, readiness_score, hours_studied) remain intact."""
        profile = LearnerProfile(
            learner_id="EMP-002",
            employee_id="EMP-002",
            role="Data Engineer",
            target_certification="DP-203",
            skill_gaps=["real-time-ingestion", "stream-analytics"],
            readiness_score=71,
            hours_studied=32.0,
            roles=["Data Engineer"],
            seniority="senior",
            current_skills=["sql", "pyspark"],
            completed_certs=["AZ-900", "AZ-104"],
            goals=["Pass DP-203"],
        )
        assert profile.role == "Data Engineer"
        assert profile.skill_gaps == ["real-time-ingestion", "stream-analytics"]
        assert profile.readiness_score == 71
        assert profile.hours_studied == 32.0
        # New fields alongside
        assert profile.roles == ["Data Engineer"]
        assert profile.seniority == "senior"

    def test_new_fields_accept_empty_collections(self) -> None:
        """Empty lists and empty string are valid for all new fields."""
        profile = LearnerProfile(
            learner_id="EMP-X",
            employee_id="EMP-X",
            role="Student",
            target_certification="AZ-900",
            skill_gaps=[],
            readiness_score=0,
            hours_studied=0.0,
            roles=[],
            seniority="",
            current_skills=[],
            completed_certs=[],
            goals=[],
        )
        assert profile.roles == []
        assert profile.seniority == ""


# ---------------------------------------------------------------------------
# CertificationInfo — new fields
# ---------------------------------------------------------------------------


class TestCertificationInfoNewFields:
    """CertificationInfo enrichment: description, level, ms_learn_url."""

    def test_new_fields_accept_values(self) -> None:
        cert = CertificationInfo(
            cert_id="AZ-900",
            name="Azure Fundamentals",
            skills=["cloud-concepts"],
            recommended_hours=32,
            passing_score=700,
            prerequisites=[],
            description="Entry-level Azure certification.",
            level="Fundamentals",
            ms_learn_url="https://learn.microsoft.com/en-us/certifications/azure-fundamentals/",
        )
        assert cert.description == "Entry-level Azure certification."
        assert cert.level == "Fundamentals"
        assert cert.ms_learn_url == "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/"

    def test_new_fields_default_to_empty_string(self) -> None:
        """Existing CertificationInfo without new fields still constructs correctly."""
        cert = CertificationInfo(
            cert_id="AZ-104",
            name="Azure Administrator",
            skills=["compute", "storage"],
            recommended_hours=40,
            passing_score=700,
            prerequisites=["AZ-900"],
        )
        assert cert.description == ""
        assert cert.level == ""
        assert cert.ms_learn_url == ""
