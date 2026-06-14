"""FastAPI application with AG-UI SSE endpoints for learner and manager workflows.

T-024 — implements:
- POST /api/learn — accepts { learner_id, target_cert_id }, runs learner pipeline via AG-UI SSE.
- POST /api/manager — accepts { team_id }, runs ManagerInsightsAgent, returns AG-UI SSE.
- GET /health — returns { status: "ok", version: "1.0.0" }.
- AG-UI endpoint wired via add_agent_framework_fastapi_endpoint (agent-framework-ag-ui adapter).
- CORS configured for ALLOWED_ORIGINS (default: http://localhost:3000).

AG-UI event flow:
    RUN_STARTED -> TEXT_MESSAGE_* -> STATE_SNAPSHOT/STATE_DELTA -> TOOL_CALL_* -> RUN_FINISHED

Seed state flow:
    The ag-ui adapter passes RunAgentInput.state (a dict) in input_data["state"] but does not
    write it into the MAF workflow context before calling workflow.run().  LearnerWorkflow
    overrides run() to pre-seed that dict under the "workflow_state" key so SeedExecutor
    can recover it and construct a LearnerMessage.
"""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logging.getLogger("agent_framework._mcp").setLevel(logging.DEBUG)
logging.getLogger("agent_framework.tool_execution").setLevel(logging.DEBUG)

from ag_ui.core import BaseEvent
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware import LearnRequestValidationMiddleware

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CORS origins
# ---------------------------------------------------------------------------

_ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Enterprise Learning System API",
    description=(
        "AI-powered enterprise learning and certification platform. "
        "Exposes AG-UI SSE streams for learner pipeline and manager insights."
    ),
    version="1.0.0",
)

# CORS — allow the Next.js dev server and any additional configured origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input validation middleware — rejects invalid payloads before they reach the workflow.
app.add_middleware(LearnRequestValidationMiddleware)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness probe.  Returns 200 with version info."""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/readiness", tags=["health"])
async def readiness() -> dict[str, str]:
    """Readiness probe for Foundry Hosted Agent. Returns 200 when app is ready."""
    return {"status": "ready"}


# ---------------------------------------------------------------------------
# AG-UI SSE endpoints (wired at startup)
# ---------------------------------------------------------------------------
# We build the workflows lazily at module import so the agent factories and IQ
# providers initialise exactly once.  The AG-UI adapter wraps each workflow and
# adds the POST endpoint + SSE streaming logic.


def _make_learner_workflow_class() -> type:
    """Return a LearnerWorkflow class that subclasses AgentFrameworkWorkflow.

    Deferred to avoid importing agent_framework_ag_ui at module level (it
    triggers Azure credential initialisation which may fail in test envs).
    """
    from agent_framework_ag_ui import AgentFrameworkWorkflow  # noqa: PLC0415

    class LearnerWorkflow(AgentFrameworkWorkflow):
        """AgentFrameworkWorkflow subclass that pre-seeds WorkflowState.

        The ag-ui adapter passes RunAgentInput.state (a dict) in input_data["state"]
        but never writes it into the MAF workflow context before calling workflow.run().
        This subclass overrides run() to inject that dict under the "workflow_state"
        key via workflow._state.set() so SeedExecutor can recover it via ctx.get_state().
        """

        async def run(self, input_data: dict[str, Any]) -> AsyncGenerator[BaseEvent]:
            raw_state = input_data.get("state")
            if raw_state and isinstance(raw_state, dict):
                thread_id = self._thread_id_from_input(input_data)
                workflow = self._resolve_workflow(thread_id)
                # State.set() writes to _pending; State.get() reads _pending first,
                # so the value is visible to ctx.get_state() in SeedExecutor immediately.
                workflow._state.set("workflow_state", raw_state)
                logger.debug("[LearnerWorkflow] Pre-seeded workflow_state from input_data")
            async for event in super().run(input_data):
                yield event

    return LearnerWorkflow


def _setup_agui_endpoints() -> None:
    """Wire both AG-UI endpoints onto the FastAPI app.

    Called once at module import time.  Errors here are logged and re-raised
    so the server fails loud rather than silently serving broken endpoints.
    """
    from agent_framework_ag_ui import (  # noqa: PLC0415
        AgentFrameworkWorkflow,
        add_agent_framework_fastapi_endpoint,
    )
    from workflow.dispatcher import (  # noqa: PLC0415
        build_learner_workflow,
        build_manager_workflow,
    )
    from workflow.state import WorkflowState  # noqa: PLC0415

    # --- Learner pipeline ---
    LearnerWorkflow = _make_learner_workflow_class()
    learner_workflow = build_learner_workflow()
    learner_agui = LearnerWorkflow(
        workflow=learner_workflow,
        name="learner-pipeline",
        description="Full learner pipeline with HITL gate and retry loop.",
    )
    add_agent_framework_fastapi_endpoint(
        app=app,
        agent=learner_agui,
        path="/api/learn",
        state_schema=WorkflowState,
        tags=["learner"],
    )
    logger.info("AG-UI endpoint registered: POST /api/learn")

    # Foundry Hosted Agent — Invocations protocol entry point.
    # Foundry routes external requests to /invocations in the container;
    # we register the same handler here so the AG-UI frontend works unchanged
    # whether it connects to localhost or the Foundry endpoint.
    add_agent_framework_fastapi_endpoint(
        app=app,
        agent=learner_agui,
        path="/invocations",
        state_schema=WorkflowState,
        tags=["hosted-agent"],
    )
    logger.info("AG-UI endpoint registered: POST /invocations (Foundry Invocations protocol)")

    # --- Manager insights ---
    manager_workflow = build_manager_workflow()
    manager_agui = AgentFrameworkWorkflow(
        workflow=manager_workflow,
        name="manager-insights",
        description="Manager team insights with privacy guardrails.",
    )
    add_agent_framework_fastapi_endpoint(
        app=app,
        agent=manager_agui,
        path="/api/manager",
        tags=["manager"],
    )
    logger.info("AG-UI endpoint registered: POST /api/manager")


try:
    _setup_agui_endpoints()
except Exception as _setup_err:  # pragma: no cover
    logger.exception("Failed to wire AG-UI endpoints: %s", _setup_err)
    raise
