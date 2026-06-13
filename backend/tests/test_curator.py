"""Tests for the CuratorExecutor in workflow/dispatcher.py (two-run redesign).

Updated for PR 2 — CuratorExecutor now uses _agent_run1 (Run 1) and
_agent_run2 / handle_cert_selected (Run 2).

Run 1: LearnerMessage → awaiting_cert_selection + cert_options
Run 2: CertSelectedMessage → awaiting_path_confirmation + learning_path + fallback on failure
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow.state import CertOption, WorkflowState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(topics: list[str] | None = None) -> WorkflowState:
    return WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=topics or ["az204-azure-compute", "az204-storage-solutions"],
        role="Cloud Engineer",
    )


def _valid_run1_json(cert_id: str = "AZ-204") -> str:
    """Return a well-formed Run 1 JSON string."""
    return json.dumps({
        "cert_options": [
            {
                "cert_id": cert_id,
                "name": f"Microsoft Azure {cert_id}",
                "description": "Intermediate cert",
                "ms_learn_url": "https://learn.microsoft.com/",
                "recommendation_pct": 85.0,
                "already_obtained": False,
                "level": "associate",
            }
        ],
        "reasoning": "Best fit for Cloud Engineer role.",
    })


def _valid_run2_json(exam: str = "AZ-204") -> str:
    """Return a well-formed Run 2 JSON string matching CurationResult."""
    return json.dumps({
        "exam": exam,
        "user_level": "intermediate",
        "priority_domains": [
            {"domain_name": "Azure Compute Solutions", "exam_weight": 0.25}
        ],
        "recommended_learning_paths": [
            {
                "resource_id": "res-001",
                "title": "Develop Azure compute solutions",
                "cert_id": exam,
                "estimated_hours": 8.0,
                "source_url": "https://learn.microsoft.com/en-us/training/paths/create-azure-app-service-web-apps/",
                "domain_name": "Azure Compute Solutions",
                "exam_weight": 0.25,
            }
        ],
        "coverage_summary": "Covers core AZ-204 compute and storage topics.",
    })


def _make_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.set_state = MagicMock()
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()
    return ctx


# ---------------------------------------------------------------------------
# Run 1 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_curator_run1_valid_json_sets_cert_options() -> None:
    """When Run 1 mock returns valid JSON, cert_options must be populated."""
    from workflow.dispatcher import CuratorExecutor, LearnerMessage

    state = _make_state()

    mock_agent_run1 = MagicMock()
    mock_agent_run1.run = AsyncMock(return_value=_valid_run1_json("AZ-204"))

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run1 = mock_agent_run1

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    assert state.workflow_status == "awaiting_cert_selection"
    assert len(state.cert_options) == 1
    assert state.cert_options[0].cert_id == "AZ-204"
    # Run 1 must not send next message
    ctx.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_curator_run1_invalid_json_returns_empty_cert_options() -> None:
    """When Run 1 returns invalid/non-JSON, cert_options must be empty list."""
    from workflow.dispatcher import CuratorExecutor, LearnerMessage

    state = _make_state(topics=["az900-cloud-concepts"])

    mock_agent_run1 = MagicMock()
    mock_agent_run1.run = AsyncMock(return_value="This is plain text, not JSON at all.")

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run1 = mock_agent_run1

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    assert state.workflow_status == "awaiting_cert_selection"
    assert state.cert_options == []


@pytest.mark.asyncio
async def test_curator_run1_agent_exception_returns_empty_cert_options() -> None:
    """When Run 1 agent.run() raises, cert_options must be empty and no exception raised."""
    from workflow.dispatcher import CuratorExecutor, LearnerMessage

    state = _make_state(topics=["az204-azure-compute"])

    mock_agent_run1 = MagicMock()
    mock_agent_run1.run = AsyncMock(side_effect=RuntimeError("Foundry unavailable"))

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run1 = mock_agent_run1

    ctx = _make_ctx()
    # Must not raise
    await executor.handle(LearnerMessage(state=state), ctx)

    assert state.workflow_status == "awaiting_cert_selection"
    assert state.cert_options == []


# ---------------------------------------------------------------------------
# Run 2 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_curator_run2_valid_json_sets_learning_path() -> None:
    """When Run 2 mock returns valid JSON, learning_path + recommended_cert_id must be set."""
    from workflow.dispatcher import CertSelectedMessage, CuratorExecutor

    state = _make_state()
    object.__setattr__(state, "cert_options", [
        CertOption(cert_id="AZ-204", name="Developing Solutions for Azure",
                   recommendation_pct=85.0, already_obtained=False)
    ])
    object.__setattr__(state, "selected_cert_id", "AZ-204")
    object.__setattr__(state, "workflow_status", "awaiting_cert_selection")

    mock_agent_run2 = MagicMock()
    mock_agent_run2.run = AsyncMock(return_value=_valid_run2_json("AZ-204"))
    mock_mcp = MagicMock()
    mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
    mock_mcp.__aexit__ = AsyncMock(return_value=False)

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run2 = mock_agent_run2
    executor._mcp_tool = mock_mcp

    ctx = _make_ctx()
    await executor.handle_cert_selected(CertSelectedMessage(state=state, selected_cert_id="AZ-204"), ctx)

    assert state.workflow_status == "awaiting_path_confirmation"
    assert state.recommended_cert_id == "AZ-204"
    assert len(state.learning_path) >= 1


@pytest.mark.asyncio
async def test_curator_run2_agent_exception_uses_fallback() -> None:
    """When Run 2 agent.run() raises, fallback curation must be used gracefully."""
    from workflow.dispatcher import CertSelectedMessage, CuratorExecutor

    state = _make_state(topics=["az204-azure-compute"])
    object.__setattr__(state, "cert_options", [])
    object.__setattr__(state, "selected_cert_id", "AZ-204")
    object.__setattr__(state, "workflow_status", "awaiting_cert_selection")

    mock_agent_run2 = MagicMock()
    mock_agent_run2.run = AsyncMock(side_effect=RuntimeError("Foundry unavailable"))
    mock_mcp = MagicMock()
    mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
    mock_mcp.__aexit__ = AsyncMock(return_value=False)

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run2 = mock_agent_run2
    executor._mcp_tool = mock_mcp

    ctx = _make_ctx()
    # Must not raise — fallback kicks in
    await executor.handle_cert_selected(CertSelectedMessage(state=state, selected_cert_id="AZ-204"), ctx)

    assert state.workflow_status == "awaiting_path_confirmation"
    assert state.recommended_cert_id is not None
    assert state.learning_path
