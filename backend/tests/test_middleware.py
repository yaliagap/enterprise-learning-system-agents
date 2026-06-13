"""Tests for api/middleware.py — validate_learn_request with topics validation.

TDD Phase 2 tests (RED -> GREEN).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.middleware import validate_learn_request


def _make_body(topics: object = None, learner_id: str = "EMP-001") -> dict:
    """Build a minimal AG-UI RunAgentInput body for /api/learn."""
    body: dict = {
        "state": {
            "learner": {
                "learner_id": learner_id,
                "employee_id": learner_id,
                "role": "Cloud Engineer",
            }
        }
    }
    if topics is not None:
        body["state"]["learner"]["topics"] = topics
    return body


def test_valid_topics_passes_validation() -> None:
    """A body with a valid, non-empty topics array must pass without raising."""
    body = _make_body(topics=["az204-azure-compute"])
    # Should not raise
    validate_learn_request(body)


def test_valid_topics_multiple_passes() -> None:
    """Multiple valid topic IDs must all pass validation."""
    body = _make_body(topics=["az104-networking", "az104-compute", "az104-storage"])
    validate_learn_request(body)


def test_missing_topics_raises_422() -> None:
    """A body with no 'topics' field must raise HTTP 422."""
    body = _make_body()  # topics not set
    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)
    assert exc_info.value.status_code == 422


def test_empty_topics_raises_422() -> None:
    """A body with topics=[] (empty list) must raise HTTP 422."""
    body = _make_body(topics=[])
    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)
    assert exc_info.value.status_code == 422


def test_unknown_topic_id_raises_422() -> None:
    """A topics array containing an unknown ID must raise HTTP 422 and name the bad ID."""
    body = _make_body(topics=["az204-azure-compute", "az999-fake-topic"])
    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)
    assert exc_info.value.status_code == 422
    assert "az999-fake-topic" in str(exc_info.value.detail)


def test_topics_not_a_list_raises_422() -> None:
    """A topics value that is not a list must raise HTTP 422."""
    body = _make_body(topics="az204-azure-compute")  # string, not list
    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)
    assert exc_info.value.status_code == 422


def test_empty_learner_id_raises_422() -> None:
    """An empty learner_id must still raise HTTP 422 (unchanged behaviour)."""
    body = _make_body(topics=["az204-azure-compute"], learner_id="")
    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)
    assert exc_info.value.status_code == 422
