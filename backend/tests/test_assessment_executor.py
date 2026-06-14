"""Tests for AssessmentExecutor changes in dispatcher.py.

T-09: Covers domain_scores derivation, weak_areas threshold, save_assessment_attempt
integration, MCP lifecycle (handle success + fallback paths), and result field population.

No real LLM calls, no real MCP connections, no real file I/O.
"""
from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow.state import (
    AssessmentAnswers,
    AssessmentQuestion,
    AssessmentQuestionPublic,
    UserAnswer,
    WorkflowState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**kwargs) -> WorkflowState:
    state = WorkflowState.seed(
        learner_id="EMP-TEST",
        employee_id="EMP-TEST",
        topics=["az104-identities"],
        role="Cloud Admin",
    )
    for k, v in kwargs.items():
        object.__setattr__(state, k, v)
    return state


def _make_question(
    id: str = "q1",
    domain: str = "Networking",
    correct_answers: list[str] | None = None,
) -> AssessmentQuestion:
    return AssessmentQuestion(
        id=id,
        text=f"Question {id}",
        question_type="multiple_choice",
        options=["A", "B", "C", "D"],
        correct_answers=correct_answers or ["A"],
        domain=domain,
        exam_weight_pct=0.1,
        explanation="Explanation.",
        difficulty="easy",
        bloom_level="Understand",
    )


def _make_ctx(ctx_store: dict | None = None) -> MagicMock:
    store: dict = ctx_store or {}
    ctx = MagicMock()
    ctx.get_state = MagicMock(side_effect=lambda k: store.get(k))
    ctx.set_state = MagicMock(side_effect=lambda k, v: store.update({k: v}))
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()
    return ctx


# ---------------------------------------------------------------------------
# T-09: handle_answers — domain_scores derivation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_answers_domain_scores_derived_from_per_question_results() -> None:
    """domain_scores are computed by averaging partial_score per domain * 100."""
    from workflow.dispatcher import AssessmentAnswersMessage, AssessmentExecutor

    # 2 questions in Networking (scores 1.0 and 0.0) → avg 0.5 → 50.0
    # 1 question in Storage (score 1.0) → 100.0
    questions = [
        _make_question("q1", domain="Networking", correct_answers=["A"]),
        _make_question("q2", domain="Networking", correct_answers=["A"]),
        _make_question("q3", domain="Storage", correct_answers=["A"]),
    ]
    # Pad to 15 required by scoring helpers
    for i in range(4, 16):
        questions.append(_make_question(f"q{i}", domain="Storage", correct_answers=["A"]))

    answers = AssessmentAnswers(
        answers=[
            UserAnswer(question_id="q1", selected_answers=["A"]),   # correct → partial=1.0
            UserAnswer(question_id="q2", selected_answers=["B"]),   # wrong  → partial=0.0
            *[
                UserAnswer(question_id=f"q{i}", selected_answers=["A"])  # all correct
                for i in range(3, 16)
            ],
        ]
    )

    state = _make_state(
        workflow_status="exam_in_progress",
        assessment_answers=answers,
        recommended_cert_id="AZ-104",
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._client = MagicMock()
    executor._mcp_tool = MagicMock()

    ctx_store: dict = {
        "assessment_questions_full": [q.model_dump() for q in questions],
        "assessment_reasoning_distribution": "Test reasoning",
    }
    ctx = _make_ctx(ctx_store=ctx_store)

    with patch("agents.tools.assessment_tools.save_assessment_attempt", return_value={"status": "saved", "attempt_number": 1}):
        await executor.handle_answers(AssessmentAnswersMessage(state=state), ctx)

    saved_state_raw = ctx_store.get("workflow_state", {})
    from workflow.state import WorkflowState as WS
    saved = WS.model_validate(saved_state_raw)
    last_result = saved.assessment_results[-1]

    assert "Networking" in last_result.domain_scores
    assert "Storage" in last_result.domain_scores
    assert last_result.domain_scores["Networking"] == 50.0  # (1.0 + 0.0) / 2 * 100
    assert last_result.domain_scores["Storage"] == 100.0


@pytest.mark.asyncio
async def test_handle_answers_weak_areas_threshold() -> None:
    """Domains with score < 70 are included in weak_areas; domains >= 70 are excluded."""
    from workflow.dispatcher import AssessmentAnswersMessage, AssessmentExecutor
    from workflow.scoring import detect_weak_areas

    # 3 networking (all wrong → score=0 → domain_score=0.0) + 12 storage (all correct → 100.0)
    questions = [
        _make_question("q1", domain="Networking", correct_answers=["A"]),
        _make_question("q2", domain="Networking", correct_answers=["A"]),
        _make_question("q3", domain="Networking", correct_answers=["A"]),
        *[_make_question(f"q{i}", domain="Storage", correct_answers=["A"]) for i in range(4, 16)],
    ]

    answers = AssessmentAnswers(
        answers=[
            # All networking wrong
            UserAnswer(question_id="q1", selected_answers=["B"]),
            UserAnswer(question_id="q2", selected_answers=["B"]),
            UserAnswer(question_id="q3", selected_answers=["B"]),
            # All storage correct
            *[
                UserAnswer(question_id=f"q{i}", selected_answers=["A"])
                for i in range(4, 16)
            ],
        ]
    )

    state = _make_state(
        workflow_status="exam_in_progress",
        assessment_answers=answers,
        recommended_cert_id="AZ-104",
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._client = MagicMock()
    executor._mcp_tool = MagicMock()

    ctx_store: dict = {
        "assessment_questions_full": [q.model_dump() for q in questions],
    }
    ctx = _make_ctx(ctx_store=ctx_store)

    with patch("agents.tools.assessment_tools.save_assessment_attempt", return_value={"status": "saved", "attempt_number": 1}):
        await executor.handle_answers(AssessmentAnswersMessage(state=state), ctx)

    saved_state_raw = ctx_store.get("workflow_state", {})
    from workflow.state import WorkflowState as WS
    saved = WS.model_validate(saved_state_raw)
    last_result = saved.assessment_results[-1]

    assert last_result.domain_scores["Networking"] == 0.0
    assert last_result.domain_scores["Storage"] == 100.0
    # weak_areas from detect_weak_areas — Networking is weak (0.0 < 70)
    assert "Networking" in last_result.weak_areas
    assert "Storage" not in last_result.weak_areas


@pytest.mark.asyncio
async def test_handle_answers_save_assessment_attempt_called() -> None:
    """handle_answers calls save_assessment_attempt with correct args."""
    from workflow.dispatcher import AssessmentAnswersMessage, AssessmentExecutor

    questions = [_make_question(f"q{i}", domain="Cloud Concepts") for i in range(1, 16)]
    answers = AssessmentAnswers(
        answers=[
            UserAnswer(question_id=f"q{i}", selected_answers=["A"])
            for i in range(1, 16)
        ]
    )
    state = _make_state(
        workflow_status="exam_in_progress",
        assessment_answers=answers,
        recommended_cert_id="AZ-900",
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._client = MagicMock()
    executor._mcp_tool = MagicMock()

    ctx_store: dict = {"assessment_questions_full": [q.model_dump() for q in questions]}
    ctx = _make_ctx(ctx_store=ctx_store)

    with patch("agents.tools.assessment_tools.save_assessment_attempt") as mock_save:
        mock_save.return_value = {"status": "saved", "attempt_number": 1}
        await executor.handle_answers(AssessmentAnswersMessage(state=state), ctx)

    mock_save.assert_called_once()
    call_args = mock_save.call_args[0]
    assert call_args[0] == "EMP-TEST"   # learner_id
    assert call_args[1] == "AZ-900"     # cert_id
    assert isinstance(call_args[2], float)  # score
    assert isinstance(call_args[3], dict)   # domain_scores
    assert isinstance(call_args[4], list)   # weak_areas


@pytest.mark.asyncio
async def test_handle_answers_save_failure_does_not_block_routing() -> None:
    """save_assessment_attempt failure must not block pass/fail routing."""
    from workflow.dispatcher import AssessmentAnswersMessage, AssessmentExecutor, AssessmentPassedMessage

    # All correct → pass
    questions = [_make_question(f"q{i}", domain="Cloud Concepts") for i in range(1, 16)]
    answers = AssessmentAnswers(
        answers=[
            UserAnswer(question_id=f"q{i}", selected_answers=["A"])
            for i in range(1, 16)
        ]
    )
    state = _make_state(
        workflow_status="exam_in_progress",
        assessment_answers=answers,
        recommended_cert_id="AZ-900",
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._client = MagicMock()
    executor._mcp_tool = MagicMock()

    ctx_store: dict = {"assessment_questions_full": [q.model_dump() for q in questions]}
    ctx = _make_ctx(ctx_store=ctx_store)

    with patch("agents.tools.assessment_tools.save_assessment_attempt", side_effect=OSError("disk full")):
        # Must NOT raise even though save_assessment_attempt raises
        await executor.handle_answers(AssessmentAnswersMessage(state=state), ctx)

    # Routing still completed (pass path sends AssessmentPassedMessage)
    ctx.send_message.assert_called_once()
    msg = ctx.send_message.call_args[0][0]
    assert isinstance(msg, AssessmentPassedMessage)


@pytest.mark.asyncio
async def test_handle_answers_sets_reasoning_distribution_from_ctx() -> None:
    """assessment_result.reasoning_distribution is taken from ctx key."""
    from workflow.dispatcher import AssessmentAnswersMessage, AssessmentExecutor

    questions = [_make_question(f"q{i}", domain="Cloud Concepts") for i in range(1, 16)]
    answers = AssessmentAnswers(
        answers=[
            UserAnswer(question_id=f"q{i}", selected_answers=["A"])
            for i in range(1, 16)
        ]
    )
    state = _make_state(
        workflow_status="exam_in_progress",
        assessment_answers=answers,
        recommended_cert_id="AZ-900",
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._client = MagicMock()
    executor._mcp_tool = MagicMock()

    ctx_store: dict = {
        "assessment_questions_full": [q.model_dump() for q in questions],
        "assessment_reasoning_distribution": "Identity boosted due to weak performance.",
    }
    ctx = _make_ctx(ctx_store=ctx_store)

    with patch("agents.tools.assessment_tools.save_assessment_attempt", return_value={"status": "saved", "attempt_number": 1}):
        await executor.handle_answers(AssessmentAnswersMessage(state=state), ctx)

    saved_state_raw = ctx_store.get("workflow_state", {})
    from workflow.state import WorkflowState as WS
    saved = WS.model_validate(saved_state_raw)
    last_result = saved.assessment_results[-1]
    assert last_result.reasoning_distribution == "Identity boosted due to weak performance."


# ---------------------------------------------------------------------------
# T-09: handle — MCP lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_grounded_generation_success() -> None:
    """handle() uses async with mcp_tool, builds agent, calls generate_assessment_questions."""
    from agents.assessment import _build_fallback_questions
    from workflow.dispatcher import AssessmentExecutor, HITLConfirmedMessage

    state = _make_state(
        workflow_status="assessing",
        recommended_cert_id="AZ-104",
        recommended_cert_name="Azure Administrator",
    )

    fallback_qs = _build_fallback_questions("AZ-104", {"General": 1.0})

    class _MockMCPTool:
        functions: list = []
        _entered = False

        async def __aenter__(self):
            _MockMCPTool._entered = True
            return self

        async def __aexit__(self, *args):
            return False

    mock_mcp = _MockMCPTool()

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._client = MagicMock()
    executor._mcp_tool = mock_mcp

    # Use a shared mutable container to capture set_state calls
    captured: dict = {}

    ctx = MagicMock()
    ctx.get_state = MagicMock(side_effect=lambda k: captured.get(k))
    ctx.set_state = MagicMock(side_effect=lambda k, v: captured.update({k: v}))
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()

    with patch(
        "workflow.dispatcher.generate_assessment_questions",
        new=AsyncMock(return_value=(fallback_qs, "Reasoning text")),
    ):
        await executor.handle(HITLConfirmedMessage(state=state), ctx)

    # MCP context manager was entered
    assert _MockMCPTool._entered is True
    # Questions stored in ctx
    stored = captured.get("assessment_questions_full")
    assert stored is not None and len(stored) == 15
    # Reasoning stashed
    assert captured.get("assessment_reasoning_distribution") == "Reasoning text"


@pytest.mark.asyncio
async def test_handle_fallback_when_mcp_raises() -> None:
    """handle() falls back to deterministic questions when async with mcp_tool raises."""
    from workflow.dispatcher import AssessmentExecutor, HITLConfirmedMessage

    state = _make_state(
        workflow_status="assessing",
        recommended_cert_id="AZ-104",
    )

    class _FailingMCPTool:
        async def __aenter__(self):
            raise ConnectionError("MCP unreachable")

        async def __aexit__(self, *args):
            return False

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._client = MagicMock()
    executor._mcp_tool = _FailingMCPTool()

    captured: dict = {}
    ctx = MagicMock()
    ctx.get_state = MagicMock(side_effect=lambda k: captured.get(k))
    ctx.set_state = MagicMock(side_effect=lambda k, v: captured.update({k: v}))
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()

    # Should NOT raise
    await executor.handle(HITLConfirmedMessage(state=state), ctx)

    stored = captured.get("assessment_questions_full")
    assert stored is not None and len(stored) == 15
    assert all(q["id"].startswith("fallback-") for q in stored)
    assert captured.get("assessment_reasoning_distribution") is None


@pytest.mark.asyncio
async def test_handle_fallback_when_generate_raises() -> None:
    """handle() falls back when generate_assessment_questions raises."""
    from workflow.dispatcher import AssessmentExecutor, HITLConfirmedMessage

    state = _make_state(
        workflow_status="assessing",
        recommended_cert_id="AZ-104",
    )

    class _OkMCPTool:
        functions: list = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._client = MagicMock()
    executor._mcp_tool = _OkMCPTool()

    captured: dict = {}
    ctx = MagicMock()
    ctx.get_state = MagicMock(side_effect=lambda k: captured.get(k))
    ctx.set_state = MagicMock(side_effect=lambda k, v: captured.update({k: v}))
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()

    with patch(
        "workflow.dispatcher.generate_assessment_questions",
        new=AsyncMock(side_effect=ValueError("LLM parse error")),
    ):
        await executor.handle(HITLConfirmedMessage(state=state), ctx)

    stored = captured.get("assessment_questions_full")
    assert stored is not None and len(stored) == 15
    assert all(q["id"].startswith("fallback-") for q in stored)
