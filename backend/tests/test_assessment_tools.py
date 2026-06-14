"""Tests for assessment_tools.py — get_learner_performance and save_assessment_attempt.

T-05: Uses tmp_path + monkeypatch for fixture file isolation.
Real backend/data/fixtures/learner_performance.json is never touched.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_fixture(path: Path, records: list[dict]) -> None:
    """Write a minimal learner_performance.json to *path*."""
    data = {
        "_metadata": {"synthetic": True},
        "records": records,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _make_record(
    learner_id: str = "EMP-001",
    cert_id: str = "AZ-104",
    attempt_number: int = 1,
    score: float = 62.0,
    domain_scores: dict | None = None,
    weak_areas: list | None = None,
) -> dict:
    return {
        "learner_id": learner_id,
        "cert_id": cert_id,
        "attempt_number": attempt_number,
        "score": score,
        "domain_scores": domain_scores or {"Networking": 48.0, "Storage": 75.0},
        "weak_areas": weak_areas or ["Networking"],
        "completed_at": "2026-05-20T14:30:00Z",
    }


# ---------------------------------------------------------------------------
# Fixture patching helper
# ---------------------------------------------------------------------------


@pytest.fixture()
def patched_perf_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Patch _PERF_FILE in assessment_tools to point at a tmp_path file."""
    perf_file = tmp_path / "learner_performance.json"
    import agents.tools.assessment_tools as at_mod
    monkeypatch.setattr(at_mod, "_PERF_FILE", perf_file)
    monkeypatch.setattr(at_mod, "_FIXTURES_DIR", tmp_path)
    return perf_file


# ---------------------------------------------------------------------------
# Tests: get_learner_performance
# ---------------------------------------------------------------------------


def test_get_learner_performance_no_file_returns_no_history(patched_perf_file: Path) -> None:
    """When fixture file is absent, get_learner_performance returns has_history=False."""
    from agents.tools.assessment_tools import get_learner_performance

    result = get_learner_performance("EMP-001", "AZ-104")

    assert result["has_history"] is False
    assert result["attempt_count"] == 0
    assert result["last_attempt"] is None


def test_get_learner_performance_with_matching_record(patched_perf_file: Path) -> None:
    """When fixture has a record for learner+cert, returns has_history=True with correct data."""
    from agents.tools.assessment_tools import get_learner_performance

    domain_scores = {"Networking": 48.0, "Storage": 75.0}
    weak_areas = ["Networking"]
    _write_fixture(
        patched_perf_file,
        [_make_record(domain_scores=domain_scores, weak_areas=weak_areas)],
    )

    result = get_learner_performance("EMP-001", "AZ-104")

    assert result["has_history"] is True
    assert result["attempt_count"] == 1
    assert result["last_attempt"] is not None
    assert result["last_attempt"]["domain_scores"]["Networking"] == 48.0
    assert "Networking" in result["last_attempt"]["weak_areas"]
    assert result["last_attempt"]["overall_score"] == 62.0


def test_get_learner_performance_multiple_records_returns_last(patched_perf_file: Path) -> None:
    """When multiple records exist for the same learner+cert, returns the one with highest attempt_number."""
    from agents.tools.assessment_tools import get_learner_performance

    records = [
        _make_record(attempt_number=1, score=58.0, domain_scores={"Networking": 40.0}, weak_areas=["Networking"]),
        _make_record(attempt_number=2, score=75.0, domain_scores={"Networking": 80.0}, weak_areas=[]),
    ]
    _write_fixture(patched_perf_file, records)

    result = get_learner_performance("EMP-001", "AZ-104")

    assert result["has_history"] is True
    assert result["attempt_count"] == 2
    assert result["last_attempt"]["overall_score"] == 75.0
    assert result["last_attempt"]["domain_scores"]["Networking"] == 80.0


def test_get_learner_performance_wrong_cert_id_returns_no_history(patched_perf_file: Path) -> None:
    """When fixture has records for different cert_id, returns has_history=False."""
    from agents.tools.assessment_tools import get_learner_performance

    _write_fixture(patched_perf_file, [_make_record(cert_id="AZ-104")])

    result = get_learner_performance("EMP-001", "AZ-900")

    assert result["has_history"] is False


def test_get_learner_performance_corrupted_json_returns_no_history(patched_perf_file: Path) -> None:
    """When fixture file contains invalid JSON, returns has_history=False without raising."""
    from agents.tools.assessment_tools import get_learner_performance

    patched_perf_file.write_text("NOT VALID JSON }{", encoding="utf-8")

    result = get_learner_performance("EMP-001", "AZ-104")

    assert result["has_history"] is False


# ---------------------------------------------------------------------------
# Tests: save_assessment_attempt
# ---------------------------------------------------------------------------


def test_save_assessment_attempt_creates_file_with_first_record(patched_perf_file: Path) -> None:
    """save_assessment_attempt creates the file and adds the first record with attempt_number=1."""
    from agents.tools.assessment_tools import save_assessment_attempt

    assert not patched_perf_file.exists()

    result = save_assessment_attempt(
        "EMP-NEW",
        "AZ-104",
        72.5,
        {"Networking": 65.0, "Storage": 80.0},
        ["Networking"],
    )

    assert result["status"] == "saved"
    assert result["attempt_number"] == 1
    assert patched_perf_file.exists()

    data = json.loads(patched_perf_file.read_text(encoding="utf-8"))
    records = [r for r in data["records"] if r["learner_id"] == "EMP-NEW"]
    assert len(records) == 1
    assert records[0]["attempt_number"] == 1
    assert records[0]["score"] == 72.5


def test_save_assessment_attempt_appends_second_record(patched_perf_file: Path) -> None:
    """Second save_assessment_attempt call appends and returns attempt_number=2."""
    from agents.tools.assessment_tools import save_assessment_attempt

    save_assessment_attempt("EMP-001", "AZ-104", 60.0, {"Networking": 50.0}, ["Networking"])
    result2 = save_assessment_attempt("EMP-001", "AZ-104", 75.0, {"Networking": 80.0}, [])

    assert result2["attempt_number"] == 2

    data = json.loads(patched_perf_file.read_text(encoding="utf-8"))
    records = [r for r in data["records"] if r["learner_id"] == "EMP-001" and r["cert_id"] == "AZ-104"]
    assert len(records) == 2
    # First record must still be there unchanged
    first = next(r for r in records if r["attempt_number"] == 1)
    assert first["score"] == 60.0


def test_save_assessment_attempt_domain_scores_round_trip(patched_perf_file: Path) -> None:
    """domain_scores and weak_areas are persisted and readable back."""
    from agents.tools.assessment_tools import save_assessment_attempt, get_learner_performance

    domain_scores = {"Identity": 45.0, "Storage": 78.0, "Networking": 52.0}
    weak_areas = ["Identity", "Networking"]

    save_assessment_attempt("EMP-RT", "AZ-104", 65.0, domain_scores, weak_areas)

    result = get_learner_performance("EMP-RT", "AZ-104")
    assert result["has_history"] is True
    assert result["last_attempt"]["domain_scores"]["Identity"] == 45.0
    assert "Networking" in result["last_attempt"]["weak_areas"]


def test_save_then_get_learner_performance_round_trip(patched_perf_file: Path) -> None:
    """Full round-trip: save_assessment_attempt then get_learner_performance returns saved data."""
    from agents.tools.assessment_tools import save_assessment_attempt, get_learner_performance

    save_assessment_attempt(
        "EMP-TRIP",
        "AZ-900",
        80.0,
        {"Cloud Concepts": 85.0},
        [],
    )

    result = get_learner_performance("EMP-TRIP", "AZ-900")

    assert result["has_history"] is True
    assert result["attempt_count"] == 1
    assert result["last_attempt"]["overall_score"] == 80.0
    assert result["last_attempt"]["weak_areas"] == []
