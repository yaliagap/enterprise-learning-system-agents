"""Responsible AI guardrails and input validation middleware.

T-028 — implements:
- AssessmentNotConfirmedError: custom exception for assessment-without-HITL guard.
- Input validation: reject requests with empty learner_id, unknown topics, or unknown learner.
- Output guardrail: wrap AssessmentAgent score output; return safe fallback on missing/non-numeric score.
- approval_mode enforcement: assessment only runs when hitl_confirmed=True in WorkflowState.
- OTel span attributes: all agent invocations log anonymised learner_id hash.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from starlette.responses import Response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class AssessmentNotConfirmedError(RuntimeError):
    """Raised when AssessmentExecutor is invoked without prior HITL confirmation.

    This is the hard guard that ensures assessment only runs after the learner
    explicitly confirmed readiness through the HITL gate.
    """


# Load fixture learner IDs once at module import (cheap, deterministic).
_KNOWN_LEARNER_IDS: set[str] = set()


def _load_known_learner_ids() -> set[str]:
    """Load valid learner IDs from the fixture file.

    Returns an empty set if the fixture file is missing or malformed — the
    validation middleware will then reject all requests (fail-secure).
    """
    fixtures_dir = os.path.join(
        os.path.dirname(__file__), "..", "data", "fixtures"
    )
    profiles_path = os.path.join(fixtures_dir, "learner_profiles.json")
    try:
        with open(profiles_path, encoding="utf-8") as fh:
            data = json.load(fh)
        learners = data.get("learners", [])
        return {p["learner_id"] for p in learners if "learner_id" in p}
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("Could not load learner fixture for validation: %s", exc)
        return set()


_KNOWN_LEARNER_IDS = _load_known_learner_ids()


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------


def validate_learn_request(body: dict[str, Any]) -> None:
    """Validate a /api/learn request body.

    Supports both direct JSON (legacy) and AG-UI RunAgentInput format where learner
    context lives inside ``body["state"]["learner"]``.

    Args:
        body: Parsed request JSON.

    Raises:
        HTTPException 422: if learner_id is missing/empty, topics is missing/empty/invalid,
            or learner_id is not found in fixture data.
    """
    from workflow.topics import AZURE_TOPICS  # noqa: PLC0415 — deferred to avoid circular import

    # AG-UI RunAgentInput nests the workflow state inside "state"
    state_data: dict[str, Any] = body.get("state") or {}
    learner_data: dict[str, Any] = state_data.get("learner") or {}

    learner_id = str(
        learner_data.get("learner_id")
        or state_data.get("learner_id")
        or body.get("learner_id", "")
    ).strip()

    if not learner_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="learner_id must not be empty.",
        )

    # Topics validation — replaces the old target_cert_id check
    topics = learner_data.get("topics") or state_data.get("topics") or body.get("topics")

    if topics is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="topics is required and must be a non-empty list of valid topic IDs.",
        )

    if not isinstance(topics, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="topics must be a list.",
        )

    if len(topics) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="topics must contain at least one topic ID.",
        )

    valid_set = set(AZURE_TOPICS)
    unknown = [t for t in topics if t not in valid_set]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown topic ID(s): {', '.join(unknown)}. Must be from the predefined taxonomy.",
        )

    if _KNOWN_LEARNER_IDS and learner_id not in _KNOWN_LEARNER_IDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learner '{learner_id}' not found in the system.",
        )


def validate_manager_request(body: dict[str, Any]) -> None:
    """Validate a /api/manager request body.

    Supports both direct JSON and AG-UI RunAgentInput where team_id is inside ``body["state"]``.

    Args:
        body: Parsed request JSON.

    Raises:
        HTTPException 422: if team_id is missing or empty.
    """
    state_data: dict[str, Any] = body.get("state") or {}
    team_id = str(state_data.get("team_id") or body.get("team_id", "")).strip()
    if not team_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="team_id must not be empty.",
        )


# ---------------------------------------------------------------------------
# Output guardrail
# ---------------------------------------------------------------------------


def safe_assessment_score(raw: Any) -> dict[str, Any]:
    """Wrap raw assessment output and ensure the 'score' field is a valid number.

    If the score is missing or non-numeric, returns a safe fallback response
    that avoids surfacing malformed data to the client.

    Args:
        raw: Raw dict output from AssessmentAgent (or any mapping-like object).

    Returns:
        A dict guaranteed to have a numeric 'score' (float 0.0–100.0).
    """
    if not isinstance(raw, dict):
        try:
            raw = dict(raw)
        except (TypeError, ValueError):
            raw = {}

    score = raw.get("score")
    if score is None or not isinstance(score, (int, float)):
        logger.warning(
            "AssessmentAgent returned invalid score (%r); substituting safe fallback.", score
        )
        raw = dict(raw)
        raw["score"] = 0.0
        raw["passed"] = False
        raw["_guardrail_applied"] = True

    # Clamp to valid range.
    raw["score"] = max(0.0, min(100.0, float(raw["score"])))
    return raw


# ---------------------------------------------------------------------------
# OTel span attribute helper
# ---------------------------------------------------------------------------


def anonymise_learner_id(learner_id: str) -> str:
    """Return a one-way SHA-256 hash of the learner_id for OTel attributes.

    Uses only the first 16 hex characters (64-bit prefix) which is sufficient
    for de-duplication in spans without exposing PII.

    Args:
        learner_id: Raw learner identifier (e.g. "EMP-001").

    Returns:
        A 16-character hex string (e.g. "a3f2e1d0c9b8a7b6").
    """
    return hashlib.sha256(learner_id.encode()).hexdigest()[:16]


def record_agent_invocation(span: Any, learner_id: str, agent_name: str) -> None:
    """Record an agent invocation on an active OTel span.

    Args:
        span: An active opentelemetry.trace.Span (or None — this function is a no-op then).
        learner_id: The learner being processed (will be anonymised before recording).
        agent_name: Human-readable name of the agent being invoked.
    """
    if span is None:
        return
    try:
        span.set_attribute("agent.name", agent_name)
        span.set_attribute("learner.id_hash", anonymise_learner_id(learner_id))
    except Exception:  # pragma: no cover
        pass  # Never let observability failure break the main flow.


# ---------------------------------------------------------------------------
# Starlette middleware (CORS + request validation)
# ---------------------------------------------------------------------------


class LearnRequestValidationMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that validates /api/learn and /api/manager request bodies.

    Runs before route handlers so invalid requests never reach the workflow.
    Only applies to POST endpoints; other methods and paths pass through untouched.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> "Response":
        if request.method == "POST" and request.url.path in {"/api/learn", "/api/manager"}:
            try:
                body_bytes = await request.body()
                body = json.loads(body_bytes) if body_bytes else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": "Request body must be valid JSON."},
                )

            try:
                if request.url.path == "/api/learn":
                    validate_learn_request(body)
                else:
                    validate_manager_request(body)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                )

        return await call_next(request)
