"""Tests for T4.2 — dispatcher multi-turn routing (PR 2).

Covers:
- CuratorExecutor.handle(LearnerMessage) → sets awaiting_cert_selection + populates cert_options
- CuratorExecutor.handle_cert_selected → sets awaiting_path_confirmation
- SeedExecutor routes awaiting_cert_selection → CertSelectedMessage on valid pick
- SeedExecutor re-prompts on ambiguous/no-match (does not change status)
- SeedExecutor routes awaiting_path_confirmation → LearnerMessage to study plan

Run from backend/:
    pytest tests/test_dispatcher_multiturn.py -v
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from workflow.state import CertOption, WorkflowState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**kwargs) -> WorkflowState:
    state = WorkflowState.seed(
        learner_id="EMP-MULTI",
        employee_id="EMP-MULTI",
        topics=["ai-fundamentals"],
        role="AI Engineer",
        experience_level="junior",
    )
    for k, v in kwargs.items():
        object.__setattr__(state, k, v)
    return state


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


def _valid_run1_json(certs: list[CertOption] | None = None) -> str:
    options = certs or _make_cert_options()
    return json.dumps({
        "cert_options": [o.model_dump() for o in options],
        "reasoning": "Chosen based on learner role and seniority.",
    })


def _valid_curation_json(exam: str = "AI-900") -> str:
    return json.dumps({
        "exam": exam,
        "user_level": "beginner",
        "priority_domains": [{"domain_name": "AI Fundamentals", "exam_weight": 0.5}],
        "recommended_learning_paths": [
            {
                "resource_id": "res-001",
                "title": f"Learn {exam}",
                "cert_id": exam,
                "estimated_hours": 8.0,
                "source_url": "https://learn.microsoft.com/",
                "domain_name": "AI Fundamentals",
                "exam_weight": 0.5,
            }
        ],
        "coverage_summary": f"Complete path for {exam}.",
    })


def _make_ctx(
    state: WorkflowState | None = None,
    ctx_store: dict | None = None,
) -> MagicMock:
    store: dict = ctx_store if ctx_store is not None else {}
    ctx = MagicMock()
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()
    ctx.get_state = MagicMock(side_effect=lambda key: store.get(key))
    ctx.set_state = MagicMock(side_effect=lambda key, value: store.update({key: value}))
    return ctx


def _make_message_list(text: str) -> list:
    """Build a minimal AG-UI message list with a single user text message."""
    content = MagicMock()
    content.type = "text"
    content.text = text
    msg = MagicMock()
    msg.role = "user"
    msg.contents = [content]
    return [msg]


# ---------------------------------------------------------------------------
# T4.2-A: CuratorExecutor.handle sets awaiting_cert_selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_curator_run1_sets_awaiting_cert_selection() -> None:
    """handle(LearnerMessage) must set workflow_status=awaiting_cert_selection."""
    from workflow.dispatcher import CuratorExecutor, LearnerMessage

    state = _make_state()
    mock_agent_run1 = MagicMock()
    mock_agent_run1.run = AsyncMock(return_value=_valid_run1_json())

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run1 = mock_agent_run1

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    assert state.workflow_status == "awaiting_cert_selection"


@pytest.mark.asyncio
async def test_curator_run1_populates_cert_options() -> None:
    """handle(LearnerMessage) must populate state.cert_options from Run 1 JSON."""
    from workflow.dispatcher import CuratorExecutor, LearnerMessage

    state = _make_state()
    mock_agent_run1 = MagicMock()
    mock_agent_run1.run = AsyncMock(return_value=_valid_run1_json())

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run1 = mock_agent_run1

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    assert len(state.cert_options) == 2
    assert state.cert_options[0].cert_id == "AI-900"


@pytest.mark.asyncio
async def test_curator_run1_does_not_send_next_message() -> None:
    """handle(LearnerMessage) must NOT call ctx.send_message — run ends after cert options."""
    from workflow.dispatcher import CuratorExecutor, LearnerMessage

    state = _make_state()
    mock_agent_run1 = MagicMock()
    mock_agent_run1.run = AsyncMock(return_value=_valid_run1_json())

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run1 = mock_agent_run1

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    ctx.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_curator_run1_emits_state_snapshot() -> None:
    """handle(LearnerMessage) must emit a StateSnapshotEvent."""
    from ag_ui.core import StateSnapshotEvent
    from workflow.dispatcher import CuratorExecutor, LearnerMessage

    state = _make_state()
    mock_agent_run1 = MagicMock()
    mock_agent_run1.run = AsyncMock(return_value=_valid_run1_json())

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run1 = mock_agent_run1

    emitted: list[Any] = []
    ctx = MagicMock()
    ctx.send_message = AsyncMock()
    ctx.set_state = MagicMock()

    async def capture(event: Any) -> None:
        emitted.append(event)

    ctx.yield_output = capture

    await executor.handle(LearnerMessage(state=state), ctx)

    snapshot_events = [e for e in emitted if isinstance(e, StateSnapshotEvent)]
    assert len(snapshot_events) >= 1


@pytest.mark.asyncio
async def test_curator_run1_sets_current_agent() -> None:
    """handle(LearnerMessage) must set state.current_agent='curator'."""
    from workflow.dispatcher import CuratorExecutor, LearnerMessage

    state = _make_state()
    mock_agent_run1 = MagicMock()
    mock_agent_run1.run = AsyncMock(return_value=_valid_run1_json())

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run1 = mock_agent_run1

    ctx = _make_ctx()
    await executor.handle(LearnerMessage(state=state), ctx)

    assert state.current_agent == "curator"


# ---------------------------------------------------------------------------
# T4.2-B: CuratorExecutor.handle_cert_selected sets awaiting_path_confirmation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_curator_run2_sets_awaiting_path_confirmation() -> None:
    """handle_cert_selected must set workflow_status=awaiting_path_confirmation."""
    from workflow.dispatcher import CertSelectedMessage, CuratorExecutor

    state = _make_state(
        cert_options=_make_cert_options(),
        selected_cert_id="AI-900",
        workflow_status="awaiting_cert_selection",
    )

    mock_agent_run2 = MagicMock()
    mock_agent_run2.run = AsyncMock(return_value=_valid_curation_json("AI-900"))
    mock_mcp = MagicMock()
    mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
    mock_mcp.__aexit__ = AsyncMock(return_value=False)

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run2 = mock_agent_run2
    executor._mcp_tool = mock_mcp

    ctx = _make_ctx()
    await executor.handle_cert_selected(CertSelectedMessage(state=state, selected_cert_id="AI-900"), ctx)

    assert state.workflow_status == "awaiting_path_confirmation"


@pytest.mark.asyncio
async def test_curator_run2_populates_learning_path() -> None:
    """handle_cert_selected must populate state.learning_path from Run 2 JSON."""
    from workflow.dispatcher import CertSelectedMessage, CuratorExecutor

    state = _make_state(
        cert_options=_make_cert_options(),
        selected_cert_id="AI-900",
        workflow_status="awaiting_cert_selection",
    )

    mock_agent_run2 = MagicMock()
    mock_agent_run2.run = AsyncMock(return_value=_valid_curation_json("AI-900"))
    mock_mcp = MagicMock()
    mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
    mock_mcp.__aexit__ = AsyncMock(return_value=False)

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run2 = mock_agent_run2
    executor._mcp_tool = mock_mcp

    ctx = _make_ctx()
    await executor.handle_cert_selected(CertSelectedMessage(state=state, selected_cert_id="AI-900"), ctx)

    assert len(state.learning_path) >= 1
    assert state.recommended_cert_id == "AI-900"


@pytest.mark.asyncio
async def test_curator_run2_clears_cert_options() -> None:
    """handle_cert_selected must clear cert_options and selected_cert_id after run."""
    from workflow.dispatcher import CertSelectedMessage, CuratorExecutor

    state = _make_state(
        cert_options=_make_cert_options(),
        selected_cert_id="AI-900",
        workflow_status="awaiting_cert_selection",
    )

    mock_agent_run2 = MagicMock()
    mock_agent_run2.run = AsyncMock(return_value=_valid_curation_json("AI-900"))
    mock_mcp = MagicMock()
    mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
    mock_mcp.__aexit__ = AsyncMock(return_value=False)

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run2 = mock_agent_run2
    executor._mcp_tool = mock_mcp

    ctx = _make_ctx()
    await executor.handle_cert_selected(CertSelectedMessage(state=state, selected_cert_id="AI-900"), ctx)

    assert state.cert_options == []
    assert state.selected_cert_id is None


@pytest.mark.asyncio
async def test_curator_run2_does_not_send_next_message() -> None:
    """handle_cert_selected must NOT call ctx.send_message — run ends at path_confirmation."""
    from workflow.dispatcher import CertSelectedMessage, CuratorExecutor

    state = _make_state(
        cert_options=_make_cert_options(),
        selected_cert_id="AI-900",
        workflow_status="awaiting_cert_selection",
    )

    mock_agent_run2 = MagicMock()
    mock_agent_run2.run = AsyncMock(return_value=_valid_curation_json("AI-900"))
    mock_mcp = MagicMock()
    mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
    mock_mcp.__aexit__ = AsyncMock(return_value=False)

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run2 = mock_agent_run2
    executor._mcp_tool = mock_mcp

    ctx = _make_ctx()
    await executor.handle_cert_selected(CertSelectedMessage(state=state, selected_cert_id="AI-900"), ctx)

    ctx.send_message.assert_not_called()


# ---------------------------------------------------------------------------
# T4.2-C: SeedExecutor routes awaiting_cert_selection → CertSelectedMessage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_awaiting_cert_selection_valid_cert_id_sends_cert_selected() -> None:
    """SeedExecutor must send CertSelectedMessage when user picks a valid cert by ID."""
    from workflow.dispatcher import CertSelectedMessage, SeedExecutor

    cert_options = _make_cert_options()
    state = _make_state(
        workflow_status="awaiting_cert_selection",
        cert_options=cert_options,
    )

    executor = SeedExecutor()
    ctx = _make_ctx()
    ctx.get_state = MagicMock(return_value=state.model_dump())

    await executor.handle(_make_message_list("AI-900"), ctx)

    ctx.send_message.assert_called_once()
    sent = ctx.send_message.call_args[0][0]
    assert isinstance(sent, CertSelectedMessage)
    assert sent.selected_cert_id == "AI-900"


@pytest.mark.asyncio
async def test_seed_awaiting_cert_selection_number_pick_sends_cert_selected() -> None:
    """SeedExecutor must send CertSelectedMessage when user picks a cert by position (e.g. '1')."""
    from workflow.dispatcher import CertSelectedMessage, SeedExecutor

    cert_options = _make_cert_options()
    state = _make_state(
        workflow_status="awaiting_cert_selection",
        cert_options=cert_options,
    )

    executor = SeedExecutor()
    ctx = _make_ctx()
    ctx.get_state = MagicMock(return_value=state.model_dump())

    await executor.handle(_make_message_list("1"), ctx)

    ctx.send_message.assert_called_once()
    sent = ctx.send_message.call_args[0][0]
    assert isinstance(sent, CertSelectedMessage)
    assert sent.selected_cert_id == "AI-900"  # first option


@pytest.mark.asyncio
async def test_seed_awaiting_cert_selection_no_match_does_not_change_status() -> None:
    """SeedExecutor must re-prompt (NOT change status) when input matches no cert option."""
    from workflow.dispatcher import SeedExecutor

    cert_options = _make_cert_options()
    state = _make_state(
        workflow_status="awaiting_cert_selection",
        cert_options=cert_options,
    )

    executor = SeedExecutor()
    ctx = _make_ctx()
    ctx.get_state = MagicMock(return_value=state.model_dump())

    await executor.handle(_make_message_list("I want the purple one"), ctx)

    # Status must remain awaiting_cert_selection
    assert state.workflow_status == "awaiting_cert_selection"
    # send_message must NOT be called with CertSelectedMessage
    from workflow.dispatcher import CertSelectedMessage
    for call in ctx.send_message.call_args_list:
        assert not isinstance(call[0][0], CertSelectedMessage)


@pytest.mark.asyncio
async def test_seed_awaiting_cert_selection_no_match_emits_reprompt_text() -> None:
    """SeedExecutor must emit a text message listing available options when no match."""
    from ag_ui.core import TextMessageContentEvent
    from workflow.dispatcher import SeedExecutor

    cert_options = _make_cert_options()
    state = _make_state(
        workflow_status="awaiting_cert_selection",
        cert_options=cert_options,
    )

    executor = SeedExecutor()
    emitted_texts: list[str] = []
    ctx = MagicMock()
    ctx.get_state = MagicMock(return_value=state.model_dump())
    ctx.set_state = MagicMock()
    ctx.send_message = AsyncMock()

    async def capture(event: Any) -> None:
        if isinstance(event, TextMessageContentEvent):
            emitted_texts.append(event.delta)

    ctx.yield_output = capture

    await executor.handle(_make_message_list("gibberish xyz"), ctx)

    # Must have emitted some text (the re-prompt)
    assert len(emitted_texts) > 0


# ---------------------------------------------------------------------------
# T4.2-D: SeedExecutor routes awaiting_path_confirmation → LearnerMessage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_awaiting_path_confirmation_sends_learner_message() -> None:
    """Any user message in awaiting_path_confirmation must route to StudyPlanExecutor via PathConfirmedMessage."""
    from workflow.dispatcher import PathConfirmedMessage, SeedExecutor

    state = _make_state(
        workflow_status="awaiting_path_confirmation",
        recommended_cert_id="AI-900",
        recommended_cert_name="Azure AI Fundamentals",
    )

    executor = SeedExecutor()
    ctx = _make_ctx()
    ctx.get_state = MagicMock(return_value=state.model_dump())

    await executor.handle(_make_message_list("Yes, let's go!"), ctx)

    ctx.send_message.assert_called_once()
    sent = ctx.send_message.call_args[0][0]
    assert isinstance(sent, PathConfirmedMessage)


@pytest.mark.asyncio
async def test_seed_awaiting_path_confirmation_sets_studying_status() -> None:
    """SeedExecutor must set workflow_status=studying before sending LearnerMessage."""
    from workflow.dispatcher import SeedExecutor

    state = _make_state(
        workflow_status="awaiting_path_confirmation",
        recommended_cert_id="AI-900",
    )

    executor = SeedExecutor()
    store: dict = {}
    ctx = MagicMock()
    ctx.get_state = MagicMock(return_value=state.model_dump())
    ctx.set_state = MagicMock(side_effect=lambda k, v: store.update({k: v}))
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()

    await executor.handle(_make_message_list("confirm"), ctx)

    # The state saved to ctx should have workflow_status=studying
    saved = store.get("workflow_state")
    assert saved is not None
    assert saved.get("workflow_status") == "studying"
