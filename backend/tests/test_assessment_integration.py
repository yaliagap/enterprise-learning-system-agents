"""Integration tests for the full assessment flow (T13).

Covers:
1. Full pass vertical: HITLConfirmedMessage -> questions generated -> all-correct answers -> passed
2. Full fail vertical: all-wrong answers -> score 0% -> retries loop back to curator
3. JSON retry: malformed LLM output -> retry -> success on second attempt
4. Middleware: request with exam_in_progress status + populated answers passes validation

Run from backend/:
    pytest tests/test_assessment_integration.py -v
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow.state import (
    AssessmentAnswers,
    AssessmentQuestion,
    UserAnswer,
    WorkflowState,
)


# ---------------------------------------------------------------------------
# Helpers — shared across all tests
# ---------------------------------------------------------------------------


def _make_state(**kwargs) -> WorkflowState:
    """Return a fresh WorkflowState with optional field overrides."""
    state = WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=["az204-azure-compute"],
        role="Cloud Engineer",
    )
    for k, v in kwargs.items():
        object.__setattr__(state, k, v)
    return state


def _make_questions(n: int = 15) -> list[AssessmentQuestion]:
    """Return n mock AssessmentQuestion objects."""
    return [
        AssessmentQuestion(
            id=f"q{i:02d}",
            text=f"Integration question {i}",
            question_type="multiple_choice",
            options=["A", "B", "C", "D"],
            correct_answers=["A"],
            domain="Azure Compute" if i % 2 == 0 else "Azure Storage",
            exam_weight_pct=100.0 / n,
            explanation=f"A is the correct answer for Q{i}.",
            difficulty="easy",
        )
        for i in range(1, n + 1)
    ]


def _make_answers(
    questions: list[AssessmentQuestion], all_correct: bool = True
) -> AssessmentAnswers:
    """Return AssessmentAnswers for all questions, either all-correct or all-wrong."""
    return AssessmentAnswers(
        answers=[
            UserAnswer(
                question_id=q.id,
                selected_answers=[q.correct_answers[0]] if all_correct else ["D"],
            )
            for q in questions
        ]
    )


def _make_ctx(
    state: WorkflowState | None = None,
    ctx_store: dict | None = None,
) -> MagicMock:
    """Build a mock WorkflowContext with state store support."""
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
# Test 1 — Full pass vertical
# HITLConfirmedMessage -> generate questions -> submit all-correct -> passed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pass_vertical() -> None:
    """All-correct answers must produce workflow_status='passed' and score=100.0."""
    from workflow.dispatcher import (
        AssessmentAnswersMessage,
        AssessmentExecutor,
        AssessmentPassedMessage,
        HITLConfirmedMessage,
    )

    questions = _make_questions()

    # --- Stage 1: HITLConfirmedMessage triggers question generation ---
    state = _make_state(
        workflow_status="assessing",
        recommended_cert_id="AZ-204",
        recommended_cert_name="Azure Developer Associate",
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    # New executor uses _mcp_tool and _client (not _agent directly)
    executor._client = MagicMock()

    class _MockMCP:
        functions: list = []
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

    executor._mcp_tool = _MockMCP()

    # Use explicit captured dict to avoid pytest asyncio lambda closure issue
    captured: dict = {}
    ctx = MagicMock()
    ctx.get_state = MagicMock(side_effect=lambda k: captured.get(k))
    ctx.set_state = MagicMock(side_effect=lambda k, v: captured.update({k: v}))
    ctx.yield_output = AsyncMock()
    ctx.send_message = AsyncMock()

    with patch(
        "workflow.dispatcher.generate_assessment_questions",
        new=AsyncMock(return_value=(questions, None)),
    ):
        await executor.handle(HITLConfirmedMessage(state=state), ctx)

    # After stage 1: questions stored in ctx, status = exam_in_progress
    assert captured.get("assessment_questions_full") is not None, (
        "Full questions must be stored in ctx after generation"
    )
    assert len(captured["assessment_questions_full"]) == 15
    saved = captured.get("workflow_state", {})
    assert saved.get("workflow_status") == "exam_in_progress", (
        f"Expected exam_in_progress, got {saved.get('workflow_status')}"
    )
    # No send_message — run ends here to wait for frontend
    ctx.send_message.assert_not_called()

    # --- Stage 2: Submit all-correct answers ---
    answers = _make_answers(questions, all_correct=True)
    state2 = WorkflowState.model_validate(captured["workflow_state"])
    object.__setattr__(state2, "assessment_answers", answers)
    object.__setattr__(state2, "workflow_status", "exam_in_progress")

    ctx_store = captured  # reuse same dict for stage 2
    ctx2 = MagicMock()
    ctx2.get_state = MagicMock(side_effect=lambda k: ctx_store.get(k))
    ctx2.set_state = MagicMock(side_effect=lambda k, v: ctx_store.update({k: v}))
    ctx2.yield_output = AsyncMock()
    ctx2.send_message = AsyncMock()

    with patch("agents.tools.assessment_tools.save_assessment_attempt", return_value={"status": "saved", "attempt_number": 1}):
        await executor.handle_answers(AssessmentAnswersMessage(state=state2), ctx2)

    # Must route to CertificationAdvisorExecutor via AssessmentPassedMessage
    ctx2.send_message.assert_called_once()
    msg = ctx2.send_message.call_args[0][0]
    assert isinstance(msg, AssessmentPassedMessage), (
        f"Expected AssessmentPassedMessage on pass, got {type(msg)}"
    )
    assert msg.state.assessment_results[-1].passed is True
    assert msg.state.assessment_results[-1].score == pytest.approx(100.0, abs=0.1)
    assert ctx_store["workflow_state"]["workflow_status"] == "passed"


# ---------------------------------------------------------------------------
# Test 2 — Full fail vertical
# All-wrong answers -> score 0% -> retry_count incremented -> loops back to curator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_fail_vertical() -> None:
    """All-wrong answers must produce score=0, passed=False, and route back to curator."""
    from workflow.dispatcher import (
        AssessmentAnswersMessage,
        AssessmentExecutor,
        LearnerMessage,
    )

    questions = _make_questions()
    answers = _make_answers(questions, all_correct=False)

    state = _make_state(
        workflow_status="exam_in_progress",
        assessment_answers=answers,
        recommended_cert_id="AZ-204",
        recommended_cert_name="Azure Developer Associate",
        retry_count=0,
        max_retries=3,
    )

    executor = AssessmentExecutor.__new__(AssessmentExecutor)
    executor.id = "assessment"
    executor._agent = MagicMock()

    ctx_store: dict = {"assessment_questions_full": [q.model_dump() for q in questions]}
    ctx = _make_ctx(ctx_store=ctx_store)

    await executor.handle_answers(AssessmentAnswersMessage(state=state), ctx)

    # exam_failed pause pattern: run ends without send_message; next run's SeedExecutor reroutes
    ctx.send_message.assert_not_called()

    # State in context must reflect exam_failed with a recorded result
    raw_state = ctx.get_state("workflow_state")
    assert raw_state is not None
    from workflow.state import WorkflowState
    saved = WorkflowState.model_validate(raw_state)
    assert saved.workflow_status == "exam_failed"
    result = saved.assessment_results[-1]
    assert result.passed is False
    assert result.score == pytest.approx(0.0, abs=0.1)
    # Weak areas must be populated from per-question results
    assert len(result.per_question_results) == 15
    for qr in result.per_question_results:
        assert qr.partial_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 3 — JSON retry: malformed output -> retry -> success
# Verifies generate_assessment_questions retry logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_question_generation_json_retry_succeeds() -> None:
    """A malformed first LLM response must trigger a retry that succeeds."""
    from agents.assessment import generate_assessment_questions

    questions = _make_questions()
    # Build valid JSON for the second call
    valid_json = json.dumps([
        {
            "id": q.id,
            "text": q.text,
            "question_type": q.question_type,
            "options": q.options,
            "correct_answers": q.correct_answers,
            "domain": q.domain,
            "exam_weight_pct": q.exam_weight_pct,
            "explanation": q.explanation,
            "difficulty": q.difficulty,
        }
        for q in questions
    ])

    call_count = 0

    async def mock_agent_run(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: return malformed JSON
            return "NOT_VALID_JSON {{{"
        # Second call: return valid JSON
        return valid_json

    mock_agent = MagicMock()
    mock_agent.run = mock_agent_run

    questions_result, reasoning = await generate_assessment_questions(
        agent=mock_agent,
        cert_id="AZ-204",
        domain_weights={"Azure Compute": 0.5, "Azure Storage": 0.5},
    )

    assert len(questions_result) == 15, f"Expected 15 questions, got {len(questions_result)}"
    assert call_count == 2, f"Expected exactly 2 agent calls (retry), got {call_count}"
    # Returned questions must have no correct_answers stripped (they are full AssessmentQuestion)
    for q in questions_result:
        assert isinstance(q, AssessmentQuestion)
        assert len(q.correct_answers) > 0


# ---------------------------------------------------------------------------
# Test 4 — Middleware: exam_in_progress state with answers passes validation
# The middleware only validates learner_id + topics — exam state should not be rejected
# ---------------------------------------------------------------------------


def test_middleware_passes_exam_in_progress_request() -> None:
    """A request with exam_in_progress workflow_status and answers must pass middleware."""
    from api.middleware import validate_learn_request

    body = {
        "state": {
            "learner": {
                "learner_id": "EMP-001",
                "employee_id": "EMP-001",
                "role": "Cloud Engineer",
                "topics": ["az204-azure-compute"],
            },
            "workflow_status": "exam_in_progress",
            "assessment_answers": {
                "answers": [
                    {"question_id": f"q{i:02d}", "selected_answers": ["A"]}
                    for i in range(1, 16)
                ]
            },
        }
    }

    # Must not raise — middleware validates learner_id + topics only
    validate_learn_request(body)


def test_middleware_exam_in_progress_still_rejects_missing_topics() -> None:
    """Even with exam_in_progress status, missing topics must still raise 422."""
    from fastapi import HTTPException

    from api.middleware import validate_learn_request

    body = {
        "state": {
            "learner": {
                "learner_id": "EMP-001",
                "employee_id": "EMP-001",
                "role": "Cloud Engineer",
                # topics missing intentionally
            },
            "workflow_status": "exam_in_progress",
            "assessment_answers": {
                "answers": [
                    {"question_id": f"q{i:02d}", "selected_answers": ["A"]}
                    for i in range(1, 16)
                ]
            },
        }
    }

    with pytest.raises(HTTPException) as exc_info:
        validate_learn_request(body)

    assert exc_info.value.status_code == 422
