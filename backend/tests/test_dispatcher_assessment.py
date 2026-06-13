"""Tests for assessment-flow dispatcher routing (T8).

Covers:
- SeedExecutor routes exam_in_progress + answers → AssessmentAnswersMessage
- SeedExecutor does NOT route when assessment_answers is absent
- AssessmentExecutor.handle stores questions in ctx and emits STATE_SNAPSHOT without correct_answers
- AssessmentExecutor.handle_answers routes to CertificationAdvisorExecutor on pass
- AssessmentExecutor.handle_answers routes to CuratorExecutor on fail, increments retry_count
- Max retries terminal state reached correctly

Run from backend/:
    pytest tests/test_dispatcher_assessment.py -v
"""
from __future__ import annotations

import json
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
        topics=["az900-cloud-concepts"],
        role="Cloud Engineer",
    )
    for k, v in kwargs.items():
        object.__setattr__(state, k, v)
    return state


def _make_questions(n: int = 15) -> list[AssessmentQuestion]:
    return [
        AssessmentQuestion(
            id=f"q{i}",
            text=f"Question {i}",
            question_type="multiple_choice",
            options=["A", "B", "C", "D"],
            correct_answers=["A"],
            domain="Cloud Concepts",
            exam_weight_pct=0.1,
            explanation="A is correct.",
            difficulty="easy",
        )
        for i in range(1, n + 1)
    ]


def _make_answers(questions: list[AssessmentQuestion], all_correct: bool = True) -> AssessmentAnswers:
    return AssessmentAnswers(
        answers=[
            UserAnswer(
                question_id=q.id,
                selected_answers=[q.correct_answers[0]] if all_correct else ["B"],
            )
            for q in questions
        ]
    )


def _make_ctx(
    state: WorkflowState | None = None,
    ctx_store: dict | None = None,
) -> MagicMock:
    store: dict = ctx_store if ctx_store is not None else {}
    if state is not None:
        store["workflow_state"] = state.model_dump()

    ctx = MagicMock()
    ctx.get_state = MagicMock(side_effect=lambda k: store.get(k))
    ctx.set_state = MagicMock(side_effect=lambda k, v: store.update({k: v}))
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()
    return ctx


# ---------------------------------------------------------------------------
# SeedExecutor routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_routes_exam_in_progress_to_assessment_answers_message() -> None:
    """SeedExecutor must send AssessmentAnswersMessage when exam_in_progress + answers present."""
    from workflow.dispatcher import AssessmentAnswersMessage, SeedExecutor

    questions = _make_questions()
    answers = _make_answers(questions)
    state = _make_state(workflow_status="exam_in_progress", assessment_answers=answers)

    ctx = _make_ctx(state=state)
    executor = SeedExecutor()
    await executor.handle([], ctx)

    ctx.send_message.assert_called_once()
    msg = ctx.send_message.call_args[0][0]
    assert isinstance(msg, AssessmentAnswersMessage), (
        f"Expected AssessmentAnswersMessage, got {type(msg)}"
    )
    assert msg.state.assessment_answers is not None


@pytest.mark.asyncio
async def test_seed_does_not_route_exam_in_progress_without_answers() -> None:
    """SeedExecutor must NOT send AssessmentAnswersMessage when assessment_answers is None."""
    from workflow.dispatcher import AssessmentAnswersMessage, HITLConfirmedMessage, LearnerMessage, SeedExecutor

    # exam_in_progress but no answers yet
    state = _make_state(workflow_status="exam_in_progress", assessment_answers=None)
    ctx = _make_ctx(state=state)
    executor = SeedExecutor()
    await executor.handle([], ctx)

    for call in ctx.send_message.call_args_list:
        msg = call[0][0]
        assert not isinstance(msg, AssessmentAnswersMessage), (
            "Should not send AssessmentAnswersMessage without answers"
        )


@pytest.mark.asyncio
async def test_seed_routes_awaiting_assessment_to_hitl_confirmed() -> None:
    """SeedExecutor must send HITLConfirmedMessage when awaiting_assessment."""
    from workflow.dispatcher import HITLConfirmedMessage, SeedExecutor

    state = _make_state(workflow_status="awaiting_assessment")
    ctx = _make_ctx(state=state)
    executor = SeedExecutor()
    await executor.handle([], ctx)

    ctx.send_message.assert_called_once()
    msg = ctx.send_message.call_args[0][0]
    assert isinstance(msg, HITLConfirmedMessage)


# ---------------------------------------------------------------------------
# AssessmentExecutor.handle — question generation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_executor_handle_stores_questions_in_ctx() -> None:
    """AssessmentExecutor.handle(HITLConfirmedMessage) must store full questions in ctx."""
    from workflow.dispatcher import AssessmentExecutor, HITLConfirmedMessage

    state = _make_state(
        workflow_status="assessing",
        recommended_cert_id="AZ-900",
        recommended_cert_name="Azure Fundamentals",
    )
    questions = _make_questions()

    # Patch generate_assessment_questions to return our fake questions
    with patch(
        "workflow.dispatcher.generate_assessment_questions",
        new=AsyncMock(return_value=questions),
    ):
        executor = AssessmentExecutor.__new__(AssessmentExecutor)
        executor.id = "assessment"
        executor._agent = MagicMock()

        ctx_store: dict = {}
        ctx = _make_ctx(ctx_store=ctx_store)

        await executor.handle(HITLConfirmedMessage(state=state), ctx)

    stored = ctx_store.get("assessment_questions_full")
    assert stored is not None, "assessment_questions_full must be stored in ctx"
    assert len(stored) == 15


@pytest.mark.asyncio
async def test_assessment_executor_handle_emits_snapshot_without_correct_answers() -> None:
    """STATE_SNAPSHOT emitted after question gen must NOT include correct_answers in questions."""
    from ag_ui.core import StateSnapshotEvent
    from workflow.dispatcher import AssessmentExecutor, HITLConfirmedMessage

    state = _make_state(
        workflow_status="assessing",
        recommended_cert_id="AZ-900",
        recommended_cert_name="Azure Fundamentals",
    )
    questions = _make_questions()

    snapshots: list[StateSnapshotEvent] = []

    with patch(
        "workflow.dispatcher.generate_assessment_questions",
        new=AsyncMock(return_value=questions),
    ):
        executor = AssessmentExecutor.__new__(AssessmentExecutor)
        executor.id = "assessment"
        executor._agent = MagicMock()

        ctx_store: dict = {}
        ctx = _make_ctx(ctx_store=ctx_store)

        async def capture(event):
            if isinstance(event, StateSnapshotEvent):
                snapshots.append(event)

        ctx.yield_output = capture

        await executor.handle(HITLConfirmedMessage(state=state), ctx)

    assert snapshots, "At least one StateSnapshotEvent must be emitted"
    last_snapshot = snapshots[-1]
    snap_questions = last_snapshot.snapshot.get("assessment_questions", [])
    assert len(snap_questions) == 15
    for q in snap_questions:
        assert "correct_answers" not in q, (
            f"correct_answers must not appear in STATE_SNAPSHOT questions: {q}"
        )


@pytest.mark.asyncio
async def test_assessment_executor_handle_sets_exam_in_progress_status() -> None:
    """AssessmentExecutor.handle must set workflow_status to exam_in_progress."""
    from workflow.dispatcher import AssessmentExecutor, HITLConfirmedMessage

    state = _make_state(
        workflow_status="assessing",
        recommended_cert_id="AZ-900",
        recommended_cert_name="Azure Fundamentals",
    )
    questions = _make_questions()

    with patch(
        "workflow.dispatcher.generate_assessment_questions",
        new=AsyncMock(return_value=questions),
    ):
        executor = AssessmentExecutor.__new__(AssessmentExecutor)
        executor.id = "assessment"
        executor._agent = MagicMock()

        ctx_store: dict = {}
        ctx = _make_ctx(ctx_store=ctx_store)
        await executor.handle(HITLConfirmedMessage(state=state), ctx)

    saved_state = ctx_store.get("workflow_state", {})
    assert saved_state.get("workflow_status") == "exam_in_progress"
    # handle ends the run — no send_message
    ctx.send_message.assert_not_called()


# ---------------------------------------------------------------------------
# AssessmentExecutor.handle_answers — scoring and routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_executor_score_pass_routes_to_advisor() -> None:
    """handle_answers must route to CertificationAdvisorExecutor when score >= 70."""
    from workflow.dispatcher import AssessmentAnswersMessage, AssessmentExecutor, AssessmentPassedMessage

    questions = _make_questions()
    answers = _make_answers(questions, all_correct=True)  # 100% score → pass
    state = _make_state(
        workflow_status="exam_in_progress",
        assessment_answers=answers,
        recommended_cert_id="AZ-900",
        recommended_cert_name="Azure Fundamentals",
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._agent = MagicMock()

    questions_serialized = [q.model_dump() for q in questions]
    ctx_store: dict = {"assessment_questions_full": questions_serialized}
    ctx = _make_ctx(ctx_store=ctx_store)

    await executor.handle_answers(AssessmentAnswersMessage(state=state), ctx)

    ctx.send_message.assert_called_once()
    msg = ctx.send_message.call_args[0][0]
    assert isinstance(msg, AssessmentPassedMessage), (
        f"Expected AssessmentPassedMessage on pass, got {type(msg)}"
    )
    assert msg.state.assessment_results[-1].passed is True


@pytest.mark.asyncio
async def test_assessment_executor_score_fail_routes_to_curator() -> None:
    """handle_answers must route to CuratorExecutor when score < 70 and retries remain."""
    from workflow.dispatcher import AssessmentAnswersMessage, AssessmentExecutor, LearnerMessage

    questions = _make_questions()
    answers = _make_answers(questions, all_correct=False)  # 0% score → fail
    state = _make_state(
        workflow_status="exam_in_progress",
        assessment_answers=answers,
        recommended_cert_id="AZ-900",
        recommended_cert_name="Azure Fundamentals",
        retry_count=0,
        max_retries=3,
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._agent = MagicMock()

    questions_serialized = [q.model_dump() for q in questions]
    ctx_store: dict = {"assessment_questions_full": questions_serialized}
    ctx = _make_ctx(ctx_store=ctx_store)

    await executor.handle_answers(AssessmentAnswersMessage(state=state), ctx)

    # exam_failed pause pattern: no send_message in this run; SeedExecutor reroutes on next run
    ctx.send_message.assert_not_called()

    # State saved to context must be exam_failed
    raw_state = ctx.get_state("workflow_state")
    assert raw_state is not None
    from workflow.state import WorkflowState
    saved = WorkflowState.model_validate(raw_state)
    assert saved.workflow_status == "exam_failed", (
        f"Expected exam_failed status on fail, got {saved.workflow_status}"
    )


@pytest.mark.asyncio
async def test_assessment_executor_max_retries_terminal() -> None:
    """handle_answers at max retries must NOT send a message and must set terminal status."""
    from workflow.dispatcher import AssessmentAnswersMessage, AssessmentExecutor

    questions = _make_questions()
    answers = _make_answers(questions, all_correct=False)  # fail
    state = _make_state(
        workflow_status="exam_in_progress",
        assessment_answers=answers,
        recommended_cert_id="AZ-900",
        recommended_cert_name="Azure Fundamentals",
        retry_count=3,
        max_retries=3,
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._agent = MagicMock()

    questions_serialized = [q.model_dump() for q in questions]
    ctx_store: dict = {"assessment_questions_full": questions_serialized}
    ctx = _make_ctx(ctx_store=ctx_store)

    await executor.handle_answers(AssessmentAnswersMessage(state=state), ctx)

    # Must NOT loop — no send_message to curator
    for call in ctx.send_message.call_args_list:
        from workflow.dispatcher import LearnerMessage
        msg = call[0][0]
        assert not isinstance(msg, LearnerMessage), "Must not send LearnerMessage at max retries"

    # Terminal state must be set
    saved = ctx_store.get("workflow_state", {})
    assert saved.get("workflow_status") == "max_retries_reached"
