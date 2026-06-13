"""Tests for Phase 3 — dispatcher rethreading of target_cert_id references.

TDD Phase 3 tests (RED -> GREEN).
Verifies that:
1. No 'target_cert_id' string remains in dispatcher.py source.
2. After curator runs, state.recommended_cert_id is set.
3. Seed executor uses topics in initial messages, not a cert ID.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from workflow.state import WorkflowState


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


def _valid_curation_json(exam: str = "AZ-204") -> str:
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
                "source_url": "https://learn.microsoft.com/en-us/training/",
                "domain_name": "Azure Compute Solutions",
                "exam_weight": 0.25,
            }
        ],
        "coverage_summary": "Covers core AZ-204 topics.",
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dispatcher_has_no_target_cert_id_references() -> None:
    """dispatcher.py must contain zero references to 'target_cert_id'."""
    import pathlib

    dispatcher_path = pathlib.Path(__file__).parent.parent / "workflow" / "dispatcher.py"
    source = dispatcher_path.read_text(encoding="utf-8")
    assert "target_cert_id" not in source, (
        "Found 'target_cert_id' in dispatcher.py — all references must use topics or recommended_cert_id"
    )


@pytest.mark.asyncio
async def test_seed_executor_uses_topics_in_message() -> None:
    """SeedExecutor must reference topics (not a cert ID) in its initial text message."""
    from ag_ui.core import TextMessageContentEvent
    from workflow.dispatcher import LearnerMessage, SeedExecutor

    state = _make_state(topics=["az104-networking", "az104-compute"])

    executor = SeedExecutor()

    ctx = MagicMock()
    ctx.get_state = MagicMock(return_value=state.model_dump())
    ctx.set_state = MagicMock()
    ctx.send_message = AsyncMock()

    emitted_texts: list[str] = []

    async def capture(event: object) -> None:
        if isinstance(event, TextMessageContentEvent):
            emitted_texts.append(event.delta)

    ctx.yield_output = capture

    await executor.handle([], ctx)

    combined = " ".join(emitted_texts)
    assert "az104-networking" in combined or "az104-compute" in combined, (
        f"Expected topic references in seed message, got: {combined!r}"
    )
    assert "target_cert_id" not in combined


@pytest.mark.asyncio
async def test_curator_executor_run1_sets_awaiting_cert_selection() -> None:
    """After CuratorExecutor.handle() (Run 1), state must be awaiting_cert_selection."""
    import json

    from workflow.dispatcher import CuratorExecutor, LearnerMessage
    from workflow.state import CertOption

    state = _make_state()

    cert_options = [
        CertOption(
            cert_id="AZ-204",
            name="Developing Solutions for Azure",
            recommendation_pct=85.0,
            already_obtained=False,
        )
    ]
    run1_json = json.dumps({
        "cert_options": [o.model_dump() for o in cert_options],
        "reasoning": "Best fit for Cloud Engineer.",
    })

    mock_agent_run1 = MagicMock()
    mock_agent_run1.run = AsyncMock(return_value=run1_json)

    executor = CuratorExecutor.__new__(CuratorExecutor)
    executor.id = "curator"
    executor._agent_run1 = mock_agent_run1

    ctx = MagicMock()
    ctx.set_state = MagicMock()
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()

    await executor.handle(LearnerMessage(state=state), ctx)

    assert state.workflow_status == "awaiting_cert_selection"
    assert len(state.cert_options) == 1
    assert state.cert_options[0].cert_id == "AZ-204"
    # Run 1 must NOT advance to next executor
    ctx.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_emitted_messages_contain_no_target_cert_id() -> None:
    """No emitted text message from SeedExecutor should contain 'target_cert_id'."""
    from ag_ui.core import TextMessageContentEvent
    from workflow.dispatcher import SeedExecutor

    state = _make_state()

    executor = SeedExecutor()
    ctx = MagicMock()
    ctx.get_state = MagicMock(return_value=state.model_dump())
    ctx.set_state = MagicMock()
    ctx.send_message = AsyncMock()

    emitted_texts: list[str] = []

    async def capture(event: object) -> None:
        if isinstance(event, TextMessageContentEvent):
            emitted_texts.append(event.delta)

    ctx.yield_output = capture

    await executor.handle([], ctx)

    for text in emitted_texts:
        assert "target_cert_id" not in text, f"Found 'target_cert_id' in message: {text!r}"
