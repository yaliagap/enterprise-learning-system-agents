"""Integration test T4.3 — full two-run curator multi-turn flow.

Tests the complete pipeline:
  Seed → CuratorRun1 → awaiting_cert_selection →
  SeedExecutor parses pick → CertSelectedMessage →
  CuratorRun2 → awaiting_path_confirmation

All agents are mocked via MagicMock. WorkflowContext is a minimal stub.

Run from backend/:
    pytest tests/test_integration_multiturn.py -v
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from workflow.state import CertOption, WorkflowState


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_cert_options() -> list[CertOption]:
    return [
        CertOption(
            cert_id="AI-900",
            name="Azure AI Fundamentals",
            description="Entry-level AI cert",
            ms_learn_url="https://learn.microsoft.com/",
            recommendation_pct=90.0,
            already_obtained=False,
            level="fundamentals",
        ),
        CertOption(
            cert_id="AI-102",
            name="Azure AI Engineer Associate",
            description="Associate-level AI cert",
            ms_learn_url="https://learn.microsoft.com/",
            recommendation_pct=70.0,
            already_obtained=False,
            level="associate",
        ),
    ]


def _valid_run1_json() -> str:
    certs = _make_cert_options()
    return json.dumps({
        "cert_options": [c.model_dump() for c in certs],
        "reasoning": "Junior AI Engineer → prefer fundamentals first.",
    })


def _valid_run2_json(cert_id: str = "AI-900") -> str:
    return json.dumps({
        "exam": cert_id,
        "user_level": "beginner",
        "priority_domains": [{"domain_name": "AI Fundamentals", "exam_weight": 0.5}],
        "recommended_learning_paths": [
            {
                "resource_id": "res-001",
                "title": f"Learn {cert_id} on MS Learn",
                "cert_id": cert_id,
                "estimated_hours": 8.0,
                "source_url": "https://learn.microsoft.com/azure-ai-fundamentals",
                "domain_name": "AI Fundamentals",
                "exam_weight": 0.5,
            }
        ],
        "coverage_summary": f"Full path for {cert_id}.",
    })


def _make_message_list(text: str) -> list:
    content = MagicMock()
    content.type = "text"
    content.text = text
    msg = MagicMock()
    msg.role = "user"
    msg.contents = [content]
    return [msg]


def _make_ctx(initial_state: WorkflowState) -> MagicMock:
    store: dict = {"workflow_state": initial_state.model_dump()}
    ctx = MagicMock()
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()
    ctx.get_state = MagicMock(side_effect=lambda key: store.get(key))
    ctx.set_state = MagicMock(side_effect=lambda key, value: store.update({key: value}))
    return ctx, store


# ---------------------------------------------------------------------------
# T4.3: Full two-run integration test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_two_run_curator_flow_end_to_end() -> None:
    """Full multi-turn flow: Seed→Run1→awaiting_cert_selection→Seed→Run2→awaiting_path_confirmation.

    Steps:
    1. Seed executor receives initial message (status=planning) → sends LearnerMessage → curator
    2. CuratorExecutor.handle (Run 1) populates cert_options, sets awaiting_cert_selection
    3. Seed executor receives cert pick → sends CertSelectedMessage → curator.handle_cert_selected
    4. CuratorExecutor.handle_cert_selected (Run 2) builds path, sets awaiting_path_confirmation
    """
    from workflow.dispatcher import (
        CertSelectedMessage,
        CuratorExecutor,
        LearnerMessage,
        SeedExecutor,
    )

    # --- Step 1: initial state ---
    state = WorkflowState.seed(
        learner_id="EMP-INTEGRATION",
        employee_id="EMP-INTEGRATION",
        topics=["ai-fundamentals"],
        role="AI Engineer",
        experience_level="junior",
    )
    assert state.workflow_status == "planning"

    # --- Setup CuratorExecutor Run 1 mock ---
    mock_run1_agent = MagicMock()
    mock_run1_agent.run = AsyncMock(return_value=_valid_run1_json())

    mock_run2_agent = MagicMock()
    mock_run2_agent.run = AsyncMock(return_value=_valid_run2_json("AI-900"))

    mock_mcp = MagicMock()
    mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
    mock_mcp.__aexit__ = AsyncMock(return_value=False)

    curator_executor = CuratorExecutor.__new__(CuratorExecutor)
    curator_executor.id = "curator"
    curator_executor._agent_run1 = mock_run1_agent
    curator_executor._agent_run2 = mock_run2_agent
    curator_executor._mcp_tool = mock_mcp

    # --- Step 2: CuratorExecutor Run 1 ---
    ctx_run1 = MagicMock()
    ctx_run1.yield_output = AsyncMock()
    ctx_run1.send_message = AsyncMock()
    store1: dict = {}
    ctx_run1.get_state = MagicMock(side_effect=lambda k: store1.get(k))
    ctx_run1.set_state = MagicMock(side_effect=lambda k, v: store1.update({k: v}))

    await curator_executor.handle(LearnerMessage(state=state), ctx_run1)

    # After Run 1: awaiting_cert_selection, cert_options populated
    assert state.workflow_status == "awaiting_cert_selection"
    assert len(state.cert_options) == 2
    assert state.cert_options[0].cert_id == "AI-900"
    # Run 1 must NOT send next message
    ctx_run1.send_message.assert_not_called()

    # --- Step 3: SeedExecutor parses cert pick ---
    seed_executor = SeedExecutor()

    ctx_seed = MagicMock()
    ctx_seed.yield_output = AsyncMock()
    ctx_seed.send_message = AsyncMock()
    store2: dict = {"workflow_state": state.model_dump()}
    ctx_seed.get_state = MagicMock(side_effect=lambda k: store2.get(k))
    ctx_seed.set_state = MagicMock(side_effect=lambda k, v: store2.update({k: v}))

    await seed_executor.handle(_make_message_list("AI-900"), ctx_seed)

    # SeedExecutor must have sent CertSelectedMessage
    ctx_seed.send_message.assert_called_once()
    cert_msg = ctx_seed.send_message.call_args[0][0]
    assert isinstance(cert_msg, CertSelectedMessage)
    assert cert_msg.selected_cert_id == "AI-900"

    # --- Step 4: CuratorExecutor Run 2 ---
    ctx_run2 = MagicMock()
    ctx_run2.yield_output = AsyncMock()
    ctx_run2.send_message = AsyncMock()
    store3: dict = {}
    ctx_run2.get_state = MagicMock(side_effect=lambda k: store3.get(k))
    ctx_run2.set_state = MagicMock(side_effect=lambda k, v: store3.update({k: v}))

    await curator_executor.handle_cert_selected(cert_msg, ctx_run2)

    # After Run 2: check the state that was mutated by handle_cert_selected
    # (cert_msg.state is the authoritative object after SeedExecutor created a new model_validate)
    final_state = cert_msg.state
    assert final_state.workflow_status == "awaiting_path_confirmation"
    assert len(final_state.learning_path) >= 1
    assert final_state.recommended_cert_id == "AI-900"
    # cert_options and selected_cert_id must be cleared
    assert final_state.cert_options == []
    assert final_state.selected_cert_id is None
    # Run 2 must NOT send next message
    ctx_run2.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_seed_awaiting_path_confirmation_completes_to_studying() -> None:
    """After awaiting_path_confirmation, SeedExecutor sets studying and sends PathConfirmedMessage."""
    from workflow.dispatcher import PathConfirmedMessage, SeedExecutor

    state = WorkflowState.seed(
        learner_id="EMP-CONFIRM",
        employee_id="EMP-CONFIRM",
        topics=["az900-cloud-concepts"],
        role="Cloud Engineer",
    )
    object.__setattr__(state, "workflow_status", "awaiting_path_confirmation")
    object.__setattr__(state, "recommended_cert_id", "AZ-900")
    object.__setattr__(state, "recommended_cert_name", "Azure Fundamentals")

    seed_executor = SeedExecutor()

    ctx = MagicMock()
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()
    store: dict = {"workflow_state": state.model_dump()}
    ctx.get_state = MagicMock(side_effect=lambda k: store.get(k))
    ctx.set_state = MagicMock(side_effect=lambda k, v: store.update({k: v}))

    await seed_executor.handle(_make_message_list("Yes, confirmed!"), ctx)

    ctx.send_message.assert_called_once()
    sent = ctx.send_message.call_args[0][0]
    assert isinstance(sent, PathConfirmedMessage)

    saved = store.get("workflow_state")
    assert saved is not None
    assert saved.get("workflow_status") == "studying"
