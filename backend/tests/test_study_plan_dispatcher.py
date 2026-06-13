"""Integration tests for study plan dispatcher components: TASK-10.

Covers:
- StudyPlanExecutor.handle happy path: valid JSON -> state populated
- Fallback on bad JSON: no exception, fallback sessions created
- priority_domains persisted by CuratorExecutor.handle_cert_selected

Run from backend/:
    pytest tests/test_study_plan_dispatcher.py -v
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from workflow.state import (
    CertOption,
    CurationResult,
    DomainWeight,
    LearningPathItem,
    WorkflowState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**kwargs) -> WorkflowState:
    state = WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=["az204-azure-compute"],
        role="Cloud Engineer",
    )
    for k, v in kwargs.items():
        object.__setattr__(state, k, v)
    return state


def _make_learning_path(exam: str = "AZ-204") -> list[LearningPathItem]:
    return [
        LearningPathItem(
            resource_id="res-001",
            title="Azure Compute Fundamentals",
            cert_id=exam,
            estimated_hours=5.0,
            source_url="https://learn.microsoft.com/",
            domain_name="Compute",
            exam_weight=0.25,
        ),
        LearningPathItem(
            resource_id="res-002",
            title="Azure Storage Solutions",
            cert_id=exam,
            estimated_hours=4.0,
            source_url="https://learn.microsoft.com/",
            domain_name="Storage",
            exam_weight=0.20,
        ),
    ]


def _make_ctx(ctx_store: dict | None = None) -> MagicMock:
    store: dict = ctx_store if ctx_store is not None else {}
    ctx = MagicMock()
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()
    ctx.get_state = MagicMock(side_effect=lambda key: store.get(key))
    ctx.set_state = MagicMock(side_effect=lambda key, value: store.update({key: value}))
    return ctx


def _valid_study_plan_json(today: str = "2026-06-13") -> str:
    return json.dumps({
        "plan_header": {
            "cert": "AZ-204",
            "slot": "morning",
            "weekly_capacity_hours": 6.0,
            "estimated_weeks": 2,
        },
        "study_plan": [
            {
                "session_id": f"session-{today.replace('-', '')}-01",
                "date": today,
                "hours": 2.0,
                "topics": ["Azure Compute"],
                "resource_ids": ["res-001"],
            },
            {
                "session_id": f"session-{today.replace('-', '')}-02",
                "date": today,
                "hours": 2.0,
                "topics": ["Azure Storage"],
                "resource_ids": ["res-002"],
            },
        ],
        "study_milestones": [
            {
                "milestone_id": "milestone-01",
                "domain_name": "Compute",
                "exam_weight": 0.25,
                "target_week": 1,
                "target_date": today,
                "resource_ids": ["res-001"],
                "session_ids": [f"session-{today.replace('-', '')}-01"],
            },
        ],
    })


def _valid_curation_json(exam: str = "AZ-204") -> str:
    return json.dumps({
        "exam": exam,
        "user_level": "intermediate",
        "priority_domains": [
            {"domain_name": "Compute", "exam_weight": 0.25},
            {"domain_name": "Storage", "exam_weight": 0.20},
        ],
        "recommended_learning_paths": [
            {
                "resource_id": "res-001",
                "title": "Azure Compute Fundamentals",
                "cert_id": exam,
                "estimated_hours": 5.0,
                "source_url": "https://learn.microsoft.com/",
                "domain_name": "Compute",
                "exam_weight": 0.25,
            }
        ],
        "coverage_summary": f"Complete path for {exam}.",
    })


# ---------------------------------------------------------------------------
# StudyPlanExecutor: happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_study_plan_executor_happy_path() -> None:
    """StudyPlanExecutor.handle with valid JSON must populate study_plan and study_milestones."""
    from workflow.dispatcher import LearnerMessage, StudyPlanExecutor

    state = _make_state(
        recommended_cert_id="AZ-204",
        learning_path=_make_learning_path(),
    )

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value=_valid_study_plan_json())

    executor = StudyPlanExecutor.__new__(StudyPlanExecutor)
    executor.id = "study_plan"
    executor._agent = mock_agent

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    assert len(state.study_plan) > 0
    assert len(state.study_milestones) > 0
    assert state.current_agent == "study_plan"


@pytest.mark.asyncio
async def test_study_plan_executor_sessions_have_session_id() -> None:
    """All sessions in study_plan must have non-empty session_id."""
    from workflow.dispatcher import LearnerMessage, StudyPlanExecutor

    state = _make_state(
        recommended_cert_id="AZ-204",
        learning_path=_make_learning_path(),
    )

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value=_valid_study_plan_json())

    executor = StudyPlanExecutor.__new__(StudyPlanExecutor)
    executor.id = "study_plan"
    executor._agent = mock_agent

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    for session in state.study_plan:
        assert session.session_id != "", f"Session {session} has empty session_id"


@pytest.mark.asyncio
async def test_study_plan_executor_emits_state_snapshot() -> None:
    """StudyPlanExecutor.handle must emit at least one StateSnapshotEvent."""
    from ag_ui.core import StateSnapshotEvent
    from workflow.dispatcher import LearnerMessage, StudyPlanExecutor

    state = _make_state(
        recommended_cert_id="AZ-204",
        learning_path=_make_learning_path(),
    )

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value=_valid_study_plan_json())

    executor = StudyPlanExecutor.__new__(StudyPlanExecutor)
    executor.id = "study_plan"
    executor._agent = mock_agent

    emitted: list[Any] = []
    ctx = _make_ctx()

    async def capture(event: Any) -> None:
        emitted.append(event)

    ctx.yield_output = capture
    ctx.send_message = AsyncMock()

    await executor.handle(LearnerMessage(state=state), ctx)

    snapshot_events = [e for e in emitted if isinstance(e, StateSnapshotEvent)]
    assert len(snapshot_events) >= 1


@pytest.mark.asyncio
async def test_study_plan_executor_sends_next_message() -> None:
    """StudyPlanExecutor.handle must call ctx.send_message to continue the pipeline."""
    from workflow.dispatcher import LearnerMessage, StudyPlanExecutor

    state = _make_state(
        recommended_cert_id="AZ-204",
        learning_path=_make_learning_path(),
    )

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value=_valid_study_plan_json())

    executor = StudyPlanExecutor.__new__(StudyPlanExecutor)
    executor.id = "study_plan"
    executor._agent = mock_agent

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    ctx.send_message.assert_called_once()


# ---------------------------------------------------------------------------
# StudyPlanExecutor: fallback on bad JSON
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_study_plan_executor_fallback_on_bad_json() -> None:
    """StudyPlanExecutor.handle must not raise on bad agent output and must produce fallback sessions."""
    from workflow.dispatcher import LearnerMessage, StudyPlanExecutor

    state = _make_state(
        recommended_cert_id="AZ-204",
        learning_path=_make_learning_path(),
    )

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value="this is not valid JSON at all")

    executor = StudyPlanExecutor.__new__(StudyPlanExecutor)
    executor.id = "study_plan"
    executor._agent = mock_agent

    ctx = _make_ctx()
    # Must not raise
    await executor.handle(LearnerMessage(state=state), ctx)

    assert len(state.study_plan) >= 1


@pytest.mark.asyncio
async def test_study_plan_executor_fallback_on_none_result() -> None:
    """StudyPlanExecutor.handle must not raise when agent returns None."""
    from workflow.dispatcher import LearnerMessage, StudyPlanExecutor

    state = _make_state(
        recommended_cert_id="AZ-204",
        learning_path=_make_learning_path(),
    )

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value=None)

    executor = StudyPlanExecutor.__new__(StudyPlanExecutor)
    executor.id = "study_plan"
    executor._agent = mock_agent

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    assert len(state.study_plan) >= 1


@pytest.mark.asyncio
async def test_study_plan_executor_fallback_on_exception() -> None:
    """StudyPlanExecutor.handle must not raise when agent.run() raises."""
    from workflow.dispatcher import LearnerMessage, StudyPlanExecutor

    state = _make_state(
        recommended_cert_id="AZ-204",
        learning_path=_make_learning_path(),
    )

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(side_effect=RuntimeError("agent unavailable"))

    executor = StudyPlanExecutor.__new__(StudyPlanExecutor)
    executor.id = "study_plan"
    executor._agent = mock_agent

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    assert len(state.study_plan) >= 1


# ---------------------------------------------------------------------------
# CuratorExecutor: priority_domains persisted after Run 2
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_curator_run2_persists_priority_domains() -> None:
    """CuratorExecutor.handle_cert_selected must populate state.priority_domains."""
    from workflow.dispatcher import CertSelectedMessage, CuratorExecutor

    state = _make_state(
        cert_options=[
            CertOption(
                cert_id="AZ-204",
                name="Azure Developer Associate",
                description="",
                ms_learn_url="",
                recommendation_pct=85.0,
            )
        ],
        selected_cert_id="AZ-204",
    )

    mock_agent_run2 = MagicMock()
    mock_agent_run2.run = AsyncMock(return_value=_valid_curation_json("AZ-204"))

    # Mock the MCP context manager
    mock_mcp_tool = MagicMock()
    mock_mcp_tool.__aenter__ = AsyncMock(return_value=mock_mcp_tool)
    mock_mcp_tool.__aexit__ = AsyncMock(return_value=False)

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run2 = mock_agent_run2
    executor._client = MagicMock()
    executor._mcp_tool = mock_mcp_tool

    ctx = _make_ctx()
    await executor.handle_cert_selected(CertSelectedMessage(state=state, selected_cert_id="AZ-204"), ctx)

    assert len(state.priority_domains) > 0
    domain_names = [d.domain_name for d in state.priority_domains]
    assert "Compute" in domain_names


@pytest.mark.asyncio
async def test_curator_run2_reconstructs_priority_domains_when_empty() -> None:
    """When curation result has empty priority_domains, reconstruct from learning_path."""
    from workflow.dispatcher import CertSelectedMessage, CuratorExecutor

    empty_priority_curation = json.dumps({
        "exam": "AZ-204",
        "user_level": "intermediate",
        "priority_domains": [],  # Empty — triggers reconstruction
        "recommended_learning_paths": [
            {
                "resource_id": "res-001",
                "title": "Azure Compute",
                "cert_id": "AZ-204",
                "estimated_hours": 5.0,
                "source_url": "https://learn.microsoft.com/",
                "domain_name": "Compute",
                "exam_weight": 0.30,
            }
        ],
        "coverage_summary": "Path for AZ-204.",
    })

    state = _make_state(
        cert_options=[
            CertOption(
                cert_id="AZ-204",
                name="Azure Developer Associate",
                description="",
                ms_learn_url="",
                recommendation_pct=85.0,
            )
        ],
    )

    mock_agent_run2 = MagicMock()
    mock_agent_run2.run = AsyncMock(return_value=empty_priority_curation)

    mock_mcp_tool = MagicMock()
    mock_mcp_tool.__aenter__ = AsyncMock(return_value=mock_mcp_tool)
    mock_mcp_tool.__aexit__ = AsyncMock(return_value=False)

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run2 = mock_agent_run2
    executor._client = MagicMock()
    executor._mcp_tool = mock_mcp_tool

    ctx = _make_ctx()
    await executor.handle_cert_selected(CertSelectedMessage(state=state, selected_cert_id="AZ-204"), ctx)

    # priority_domains must be reconstructed from learning_path
    assert len(state.priority_domains) > 0
    assert state.priority_domains[0].domain_name == "Compute"
