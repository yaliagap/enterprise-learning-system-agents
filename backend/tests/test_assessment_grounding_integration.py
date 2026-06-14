"""T-10: Integration smoke test for the grounded assessment flow.

Tests the full flow with real file I/O against a tmp_path copy of the seed fixture.
No LLM calls, no MCP calls — pure data layer + domain logic.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.assessment import _largest_remainder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _copy_fixture_to(tmp_path: Path, src: Path) -> Path:
    """Copy src fixture to tmp_path and return the destination path."""
    dest = tmp_path / src.name
    dest.write_bytes(src.read_bytes())
    return dest


def _get_fixture_path() -> Path:
    """Return the real learner_performance.json fixture path."""
    return Path(__file__).parent.parent / "data" / "fixtures" / "learner_performance.json"


# ---------------------------------------------------------------------------
# 1. get_learner_performance — no history → has_history=False
# ---------------------------------------------------------------------------


def test_get_learner_performance_no_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """For a learner not in the fixture, get_learner_performance returns has_history=False."""
    import agents.tools.assessment_tools as at_mod

    perf_file = tmp_path / "learner_performance.json"
    monkeypatch.setattr(at_mod, "_PERF_FILE", perf_file)
    monkeypatch.setattr(at_mod, "_FIXTURES_DIR", tmp_path)

    # Copy real fixture to tmp_path so we have seed data
    real_fixture = _get_fixture_path()
    if real_fixture.exists():
        perf_file.write_bytes(real_fixture.read_bytes())

    from agents.tools.assessment_tools import get_learner_performance

    result = get_learner_performance("NEW-LEARNER", "AZ-900")

    assert result["has_history"] is False
    assert result["attempt_count"] == 0
    assert result["last_attempt"] is None


# ---------------------------------------------------------------------------
# 2. get_learner_performance — EMP-001/AZ-104 → has_history=True + weak_areas
# ---------------------------------------------------------------------------


def test_get_learner_performance_emp001_az104(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EMP-001/AZ-104 returns has_history=True with correct data from seed fixture."""
    import agents.tools.assessment_tools as at_mod

    perf_file = tmp_path / "learner_performance.json"
    monkeypatch.setattr(at_mod, "_PERF_FILE", perf_file)
    monkeypatch.setattr(at_mod, "_FIXTURES_DIR", tmp_path)

    real_fixture = _get_fixture_path()
    if not real_fixture.exists():
        pytest.skip("learner_performance.json fixture not found")
    perf_file.write_bytes(real_fixture.read_bytes())

    from agents.tools.assessment_tools import get_learner_performance

    result = get_learner_performance("EMP-001", "AZ-104")

    assert result["has_history"] is True
    assert result["attempt_count"] >= 1
    assert result["last_attempt"] is not None
    assert len(result["last_attempt"]["weak_areas"]) >= 1
    domain_scores = result["last_attempt"]["domain_scores"]
    assert len(domain_scores) > 0


# ---------------------------------------------------------------------------
# 3. _largest_remainder with AZ-104 weights → sum to 15
# ---------------------------------------------------------------------------


def test_largest_remainder_az104_weights() -> None:
    """_largest_remainder with realistic AZ-104 weights allocates exactly 15 questions."""
    # Approximate AZ-104 official weights
    az104_weights = {
        "Manage Azure identities and governance": 0.20,
        "Implement and manage storage": 0.15,
        "Deploy and manage Azure compute resources": 0.20,
        "Implement and manage virtual networking": 0.25,
        "Monitor and maintain Azure resources": 0.20,
    }
    result = _largest_remainder(az104_weights, total=15)
    assert sum(result.values()) == 15
    assert len(result) == 5
    for count in result.values():
        assert count >= 1  # Every domain gets at least 1 question


# ---------------------------------------------------------------------------
# 4. Executor handle_answers domain derivation
# ---------------------------------------------------------------------------


def test_handle_answers_domain_derivation_synthetic() -> None:
    """Synthetic per_question_results → domain_scores computed correctly by executor logic."""
    # Simulate the domain derivation logic from handle_answers
    from workflow.state import AssessmentQuestion, QuestionResult

    domains = ["Networking", "Storage", "Compute"]
    questions = [
        AssessmentQuestion(
            id=f"q{i}",
            text=f"Q{i}",
            question_type="multiple_choice",
            options=["A", "B", "C", "D"],
            correct_answers=["A"],
            domain=domains[i % 3],
            exam_weight_pct=0.1,
            explanation="E",
            difficulty="easy",
        )
        for i in range(15)
    ]

    # Set Networking=0%, Storage=100%, Compute=50%
    def _score_for(domain: str) -> float:
        if domain == "Networking":
            return 0.0
        if domain == "Storage":
            return 1.0
        return 0.5  # Compute

    per_question_results = [
        QuestionResult(
            question_id=q.id,
            user_answers=["A"],
            correct_answers=["A"],
            is_correct=_score_for(q.domain) == 1.0,
            partial_score=_score_for(q.domain),
            explanation="E",
        )
        for q in questions
    ]

    qid_to_domain = {q.id: q.domain for q in questions}
    domain_to_scores: dict[str, list[float]] = {}
    for r in per_question_results:
        d = qid_to_domain.get(r.question_id, "General")
        domain_to_scores.setdefault(d, []).append(r.partial_score)

    domain_scores = {
        d: round(sum(v) / len(v) * 100, 1)
        for d, v in domain_to_scores.items()
    }

    assert domain_scores["Networking"] == pytest.approx(0.0)
    assert domain_scores["Storage"] == pytest.approx(100.0)
    assert domain_scores["Compute"] == pytest.approx(50.0)

    # weak_areas = domains < 70
    weak_areas = [d for d, s in domain_scores.items() if s < 70.0]
    assert "Networking" in weak_areas
    assert "Compute" in weak_areas
    assert "Storage" not in weak_areas


# ---------------------------------------------------------------------------
# 5. Persistence round-trip: save → get
# ---------------------------------------------------------------------------


def test_persistence_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """save_assessment_attempt then get_learner_performance returns the saved data."""
    import agents.tools.assessment_tools as at_mod

    perf_file = tmp_path / "learner_performance.json"
    monkeypatch.setattr(at_mod, "_PERF_FILE", perf_file)
    monkeypatch.setattr(at_mod, "_FIXTURES_DIR", tmp_path)

    # Copy real fixture so EMP-001/AZ-104 has 1 existing attempt
    real_fixture = _get_fixture_path()
    if real_fixture.exists():
        perf_file.write_bytes(real_fixture.read_bytes())

    from agents.tools.assessment_tools import get_learner_performance, save_assessment_attempt

    # Save a new attempt for EMP-001/AZ-104
    save_result = save_assessment_attempt(
        "EMP-001",
        "AZ-104",
        72.0,
        {
            "Manage Azure identities and governance": 75.0,
            "Implement and manage virtual networking": 70.0,
        },
        [],
    )

    assert save_result["status"] == "saved"
    # EMP-001/AZ-104 already had 1 attempt in the fixture → new one is #2
    attempt_num = save_result["attempt_number"]
    assert attempt_num >= 2

    # Get learner performance — should reflect the new attempt as "last" (highest attempt_number)
    result = get_learner_performance("EMP-001", "AZ-104")
    assert result["has_history"] is True
    assert result["attempt_count"] >= 2
    # The last attempt should be the one we just saved (highest attempt_number)
    assert result["last_attempt"]["overall_score"] == 72.0
    assert result["last_attempt"]["weak_areas"] == []

    # Real fixture must NOT have been modified
    real_fixture_data = json.loads(real_fixture.read_bytes())
    real_records = [
        r for r in real_fixture_data["records"]
        if r["learner_id"] == "EMP-001" and r["cert_id"] == "AZ-104"
    ]
    # Real fixture should still have only 1 record for EMP-001/AZ-104
    assert len(real_records) == 1


# ---------------------------------------------------------------------------
# 6. First-time learner path → has_history=False
# ---------------------------------------------------------------------------


def test_first_time_learner_no_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """First-time learner path: get_learner_performance returns has_history=False."""
    import agents.tools.assessment_tools as at_mod

    perf_file = tmp_path / "learner_performance.json"
    monkeypatch.setattr(at_mod, "_PERF_FILE", perf_file)
    monkeypatch.setattr(at_mod, "_FIXTURES_DIR", tmp_path)

    # Copy real fixture to isolate
    real_fixture = _get_fixture_path()
    if real_fixture.exists():
        perf_file.write_bytes(real_fixture.read_bytes())

    from agents.tools.assessment_tools import get_learner_performance

    result = get_learner_performance("NEW-LEARNER", "AZ-900")

    assert result["has_history"] is False
    assert result["attempt_count"] == 0

    # Without history, _largest_remainder should still work with base weights
    az900_weights = {"Cloud Concepts": 0.25, "Core Services": 0.35, "Security": 0.25, "Pricing": 0.15}
    counts = _largest_remainder(az900_weights, total=15)
    assert sum(counts.values()) == 15
