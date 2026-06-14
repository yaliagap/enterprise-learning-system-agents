"""Mock Fabric IQ provider: serves skill gaps, progress, and team readiness from fixtures."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from grounding.base import (
    CertificationInfo,
    FabricIQProvider,
    LearnerProfile,
    SkillGapAnalysis,
)
from observability.otel import trace_iq_call

_FIXTURES_DIR = Path(__file__).parent.parent.parent / "data" / "fixtures"


# ---------------------------------------------------------------------------
# Fixture loaders (cached per process)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _learner_profiles() -> dict[str, dict]:
    """Return a mapping of learner_id → profile dict."""
    path = _FIXTURES_DIR / "learner_profiles.json"
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return {p["learner_id"]: p for p in data["learners"]}


@lru_cache(maxsize=1)
def _certification_catalog() -> dict[str, dict]:
    """Return a mapping of cert_id → certification dict."""
    path = _FIXTURES_DIR / "certification_catalog.json"
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return {c["cert_id"]: c for c in data["certifications"]}


@lru_cache(maxsize=1)
def _team_aggregates() -> dict[str, dict]:
    """Return a mapping of team_id → aggregate dict."""
    path = _FIXTURES_DIR / "team_aggregates.json"
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    # Support both a top-level list and a dict with a "teams" key
    if isinstance(data, list):
        return {t["team_id"]: t for t in data}
    if "teams" in data:
        return {t["team_id"]: t for t in data["teams"]}
    # Single-team file keyed directly
    if "team_id" in data:
        return {data["team_id"]: data}
    return data


# ---------------------------------------------------------------------------
# Helper: compute skill gap from fixture data
# ---------------------------------------------------------------------------


def _compute_skill_gap(profile: dict, cert: dict) -> SkillGapAnalysis:
    """Derive a SkillGapAnalysis from a learner profile and cert record."""
    current_skills: set[str] = set(profile.get("current_skills", []))
    required_skills: list[str] = cert.get("skill_modules", []) + cert.get("skill_tags", [])

    missing: list[str] = [s for s in required_skills if s not in current_skills]
    total = len(required_skills) or 1
    coverage = round((1 - len(missing) / total) * 100, 1)

    recommended_total: int = cert.get("recommended_hours", 40)
    hours_studied: float = float(profile.get("study_hours_per_week", 0)) * 4  # rough 4-week proxy
    hours_remaining = max(0.0, recommended_total - hours_studied)

    return SkillGapAnalysis(
        learner_id=profile["learner_id"],
        cert_id=cert["cert_id"],
        missing_skills=missing,
        coverage_pct=coverage,
        recommended_hours_remaining=round(hours_remaining, 1),
    )


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockFabricIQProvider(FabricIQProvider):
    """Fabric IQ backed by learner_profiles.json and certification_catalog.json fixtures.

    All data is loaded lazily and cached for the lifetime of the process,
    ensuring deterministic (NFR-003) and fast responses.
    """

    # ------------------------------------------------------------------
    # FabricIQProvider interface
    # ------------------------------------------------------------------

    def skill_gaps(self, learner_id: str) -> SkillGapAnalysis:
        """Return a skill gap analysis for the learner's primary target cert.

        Raises:
            KeyError: if *learner_id* is not found in fixtures.
        """
        with trace_iq_call("fabric_iq", "get_skill_gap_analysis"):
            profiles = _learner_profiles()
            catalog = _certification_catalog()

            if learner_id not in profiles:
                raise KeyError(f"Learner '{learner_id}' not found in fixtures.")

            profile = profiles[learner_id]
            target_certs: list[str] = profile.get("target_certs", [])
            if not target_certs:
                raise ValueError(f"Learner '{learner_id}' has no target_certs defined.")

            # Use the first target cert as the primary gap analysis target
            primary_cert_id = target_certs[0]
            if primary_cert_id not in catalog:
                raise KeyError(f"Cert '{primary_cert_id}' not found in catalog.")

            return _compute_skill_gap(profile, catalog[primary_cert_id])

    def learner_profile(self, learner_id: str) -> LearnerProfile:
        """Return the enriched learner profile for *learner_id*.

        Raises:
            KeyError: if *learner_id* is not found in fixtures.
        """
        with trace_iq_call("fabric_iq", "get_learner_profile"):
            profiles = _learner_profiles()
            if learner_id not in profiles:
                raise KeyError(f"Learner '{learner_id}' not found in fixtures.")

            p = profiles[learner_id]
            target_certs: list[str] = p.get("target_certs", [])
            primary_cert = target_certs[0] if target_certs else "unknown"

            # Derive skill_gaps inline from the profile's current_skills vs. the
            # primary cert's required modules (lightweight; no catalog lookup needed
            # for the profile model itself).
            catalog = _certification_catalog()
            cert = catalog.get(primary_cert, {})
            required = cert.get("skill_modules", []) + cert.get("skill_tags", [])
            current: set[str] = set(p.get("current_skills", []))
            gaps = [s for s in required if s not in current]

            roles: list[str] = p.get("roles", [])
            primary_role = roles[0] if roles else p.get("role", "unknown")

            return LearnerProfile(
                learner_id=p["learner_id"],
                employee_id=p["learner_id"],  # same identifier in our fixtures
                role=primary_role,
                seniority=p.get("seniority", ""),
                target_certification=primary_cert,
                skill_gaps=gaps,
                readiness_score=p.get("readiness_score", 0),
                hours_studied=float(p.get("study_hours_per_week", 0)) * 4,
                # Enriched fields
                roles=roles,
                current_skills=p.get("current_skills", []),
                strongest_domains=p.get("strongest_domains", []),
                completed_certs=p.get("completed_certs", []),
                goals=p.get("goals", []),
            )

    def team_readiness(self, team_id: str) -> dict:
        """Return the raw team aggregate record for *team_id*.

        Raises:
            KeyError: if *team_id* is not found in team_aggregates.json.
        """
        with trace_iq_call("fabric_iq", "get_team_readiness"):
            teams = _team_aggregates()
            if team_id not in teams:
                raise KeyError(f"Team '{team_id}' not found in team_aggregates.json.")
            return teams[team_id]
