"""Integration smoke tests — topics-driven request contract.

Validates that:
1. A request with valid topic IDs passes middleware and reaches SeedExecutor
   (WorkflowState.model_validate succeeds with topics in learner context).
2. Middleware rejects a request with invalid topic IDs (HTTP 422).
3. Middleware rejects a request with an empty topics array (HTTP 422).

These tests exercise the full validation stack end-to-end at the unit level
(no running HTTP server required).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.middleware import validate_learn_request
from workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_learn_body(topics: object, learner_id: str = "EMP-001") -> dict:
    """Construct a minimal AG-UI RunAgentInput body for /api/learn."""
    body: dict = {
        "state": {
            "learner": {
                "learner_id": learner_id,
                "employee_id": learner_id,
                "role": "developer",
            }
        }
    }
    if isinstance(topics, list) or isinstance(topics, str):
        body["state"]["learner"]["topics"] = topics  # type: ignore[index]
    elif topics is not None:
        body["state"]["learner"]["topics"] = topics  # type: ignore[index]
    return body


# ---------------------------------------------------------------------------
# Test 1 — valid topics reach SeedExecutor
# ---------------------------------------------------------------------------


def test_valid_topics_pass_middleware_and_seed() -> None:
    """A request with valid topic IDs must pass middleware and allow WorkflowState.seed()."""
    valid_topics = ["az204-azure-compute", "az204-storage-solutions"]
    body = _make_learn_body(topics=valid_topics)

    # Step 1: middleware must NOT raise
    validate_learn_request(body)

    # Step 2: WorkflowState.seed() (what SeedExecutor calls) must succeed
    state = WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=valid_topics,
        role="developer",
    )

    assert state.learner.topics == valid_topics
    assert state.recommended_cert_id is None
    assert state.recommended_cert_name is None
    assert state.workflow_status == "planning"


def test_seed_populates_topics_on_workflow_state() -> None:
    """WorkflowState seeded from topics must expose topics on learner context."""
    topics = ["az104-networking", "az104-compute", "az104-storage"]
    state = WorkflowState.seed(
        learner_id="EMP-002",
        employee_id="EMP-002",
        topics=topics,
        role="cloud engineer",
    )
    assert set(state.learner.topics) == set(topics)
    # Cert fields start as None — curator populates them later
    assert state.recommended_cert_id is None
    assert state.recommended_cert_name is None
    assert state.learning_path == []


# ---------------------------------------------------------------------------
# Test 2 — invalid topic IDs are rejected by middleware
# ---------------------------------------------------------------------------


def test_middleware_rejects_invalid_topic_ids() -> None:
    """Middleware must return HTTP 422 for a request containing unknown topic IDs."""
    body = _make_learn_body(topics=["az204-azure-compute", "az999-fake-topic"])

    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)

    assert exc_info.value.status_code == 422
    # The unknown ID must be named in the error detail
    assert "az999-fake-topic" in str(exc_info.value.detail)


def test_middleware_rejects_all_invalid_topics_and_names_them() -> None:
    """When multiple unknown IDs are submitted, all must appear in the 422 detail."""
    body = _make_learn_body(topics=["bad-topic-1", "bad-topic-2"])

    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)

    assert exc_info.value.status_code == 422
    detail = str(exc_info.value.detail)
    assert "bad-topic-1" in detail
    assert "bad-topic-2" in detail


# ---------------------------------------------------------------------------
# Test 3 — empty topics array is rejected by middleware
# ---------------------------------------------------------------------------


def test_middleware_rejects_empty_topics_array() -> None:
    """Middleware must return HTTP 422 when topics is an empty list."""
    body = _make_learn_body(topics=[])

    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)

    assert exc_info.value.status_code == 422


def test_middleware_rejects_missing_topics_field() -> None:
    """Middleware must return HTTP 422 when the topics field is absent entirely."""
    body: dict = {
        "state": {
            "learner": {
                "learner_id": "EMP-001",
                "employee_id": "EMP-001",
                "role": "developer",
                # No 'topics' key
            }
        }
    }

    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)

    assert exc_info.value.status_code == 422
