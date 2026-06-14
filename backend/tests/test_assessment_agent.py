"""Tests for assessment.py — factory, _largest_remainder, parser, critic, fallback.

T-07: No real LLM or MCP calls. Agent.run is mocked.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.assessment import (
    _build_fallback_questions,
    _check_batch,
    _largest_remainder,
    _parse_questions,
    create_assessment_agent,
)
from workflow.state import AssessmentQuestion, GroundingReference


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_question(
    id: str = "q1",
    domain: str = "Cloud Concepts",
    difficulty: str = "easy",
    is_scenario_based: bool = False,
    question_type: str = "multiple_choice",
    correct_answers: list[str] | None = None,
    text: str | None = None,
    grounding_reference: GroundingReference | None = None,
) -> AssessmentQuestion:
    if correct_answers is None:
        correct_answers = ["A"]
    if question_type == "multi_select":
        correct_answers = ["A", "B"]
        if text is None:
            text = "Which two options? (Select 2)"
    if text is None:
        text = "What is Azure?"
    return AssessmentQuestion(
        id=id,
        text=text,
        question_type=question_type,
        options=["A", "B", "C", "D"],
        correct_answers=correct_answers,
        domain=domain,
        exam_weight_pct=0.1,
        explanation="Explanation.",
        difficulty=difficulty,
        bloom_level="Understand",
        is_scenario_based=is_scenario_based,
        scenario_context="Contoso scenario." if is_scenario_based else None,
        grounding_reference=grounding_reference,
    )


def _make_valid_batch(
    n: int = 15,
    easy_count: int = 6,
    medium_count: int = 6,
    hard_count: int = 3,
    scenario_count: int = 4,
) -> list[AssessmentQuestion]:
    """Build a batch that passes structural checks."""
    difficulties = (
        ["easy"] * easy_count
        + ["medium"] * medium_count
        + ["hard"] * hard_count
    )
    questions = []
    for i in range(n):
        diff = difficulties[i] if i < len(difficulties) else "medium"
        is_scenario = i < scenario_count
        questions.append(_make_question(
            id=f"q{i+1}",
            difficulty=diff,
            is_scenario_based=is_scenario,
        ))
    return questions


def _batch_to_json(questions: list[AssessmentQuestion]) -> str:
    """Serialize a question list to the envelope JSON format."""
    return json.dumps({
        "questions": [q.model_dump() for q in questions],
        "reasoning_distribution": "Storage boosted due to weak performance.",
    })


# ---------------------------------------------------------------------------
# Tests: _largest_remainder
# ---------------------------------------------------------------------------


def test_largest_remainder_sums_to_15() -> None:
    """_largest_remainder with 3 domains must sum to exactly 15."""
    weights = {"A": 0.4, "B": 0.4, "C": 0.2}
    result = _largest_remainder(weights, total=15)
    assert sum(result.values()) == 15


def test_largest_remainder_standard_case() -> None:
    """_largest_remainder with equal-split weights distributes evenly (6/6/3)."""
    weights = {"A": 0.4, "B": 0.4, "C": 0.2}
    result = _largest_remainder(weights, total=15)
    assert result["A"] == 6
    assert result["B"] == 6
    assert result["C"] == 3


def test_largest_remainder_single_domain() -> None:
    """Single domain gets all 15 questions."""
    result = _largest_remainder({"Only": 1.0}, total=15)
    assert result == {"Only": 15}


def test_largest_remainder_various_distributions() -> None:
    """_largest_remainder always sums to total for various weight combinations."""
    for weights in [
        {"A": 0.35, "B": 0.25, "C": 0.20, "D": 0.15, "E": 0.05},
        {"X": 0.5, "Y": 0.3, "Z": 0.2},
        {"P": 1 / 3, "Q": 1 / 3, "R": 1 / 3},
        {"M": 0.1, "N": 0.9},
    ]:
        result = _largest_remainder(weights, total=15)
        assert sum(result.values()) == 15, f"Failed for weights={weights}, result={result}"


# ---------------------------------------------------------------------------
# Tests: create_assessment_agent
# ---------------------------------------------------------------------------


def _get_agent_tools(agent: object) -> list:
    """Extract tools list from agent.default_options (agent_framework internal storage)."""
    return agent.default_options.get("tools", [])


def test_create_assessment_agent_default_tools() -> None:
    """create_assessment_agent with no extra args returns Agent with 2 default tools."""
    client = MagicMock()
    agent = create_assessment_agent(client)
    assert agent is not None
    assert len(_get_agent_tools(agent)) == 2  # get_learner_performance + search_knowledge_base


def test_create_assessment_agent_with_submit_tool() -> None:
    """create_assessment_agent with extra mcp_fn returns Agent with 3 tools."""
    client = MagicMock()
    mock_mcp_fn = MagicMock()
    agent = create_assessment_agent(client, None, None, mock_mcp_fn)
    assert len(_get_agent_tools(agent)) == 3


def test_create_assessment_agent_without_mcp_has_2_tools() -> None:
    """create_assessment_agent without mcp functions has 2 tools (perf + kb)."""
    client = MagicMock()
    agent = create_assessment_agent(client)
    assert len(_get_agent_tools(agent)) == 2


# ---------------------------------------------------------------------------
# Tests: _parse_questions
# ---------------------------------------------------------------------------


def test_parse_questions_bare_array() -> None:
    """_parse_questions handles bare JSON array and returns (questions, None)."""
    batch = _make_valid_batch()
    raw = json.dumps([q.model_dump() for q in batch])
    questions, reasoning = _parse_questions(raw)
    assert len(questions) == 15
    assert reasoning is None


def test_parse_questions_envelope_format() -> None:
    """_parse_questions handles envelope JSON and extracts reasoning_distribution."""
    batch = _make_valid_batch()
    raw = _batch_to_json(batch)
    questions, reasoning = _parse_questions(raw)
    assert len(questions) == 15
    assert reasoning == "Storage boosted due to weak performance."


def test_parse_questions_invalid_json_raises_value_error() -> None:
    """_parse_questions raises ValueError on invalid JSON."""
    with pytest.raises(ValueError, match="JSON decode failed"):
        _parse_questions("NOT JSON {}")


def test_parse_questions_wrong_count_raises_value_error() -> None:
    """_parse_questions raises ValueError when question count is not 15."""
    batch = _make_valid_batch(n=14)
    raw = json.dumps([q.model_dump() for q in batch])
    with pytest.raises(ValueError, match="Expected 15 questions"):
        _parse_questions(raw)


# ---------------------------------------------------------------------------
# Tests: _check_batch (structural critic)
# ---------------------------------------------------------------------------


def test_check_batch_valid_returns_no_issues() -> None:
    """_check_batch on a valid batch returns an empty issues list."""
    batch = _make_valid_batch()
    issues = _check_batch(batch)
    assert issues == []


def test_check_batch_few_scenario_questions_detected() -> None:
    """_check_batch detects when fewer than 4 questions are scenario-based."""
    batch = _make_valid_batch(scenario_count=2)
    issues = _check_batch(batch)
    assert any("scenario" in i.lower() for i in issues)


def test_check_batch_difficulty_out_of_range_detected() -> None:
    """_check_batch detects when hard count is outside 2-4 range."""
    # Only 1 hard question — below the 2-4 range
    batch = _make_valid_batch(easy_count=7, medium_count=7, hard_count=1)
    issues = _check_batch(batch)
    assert any("hard" in i.lower() for i in issues)


# ---------------------------------------------------------------------------
# Tests: generate_assessment_questions (mocked agent)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_assessment_questions_success_path() -> None:
    """generate_assessment_questions returns (questions, reasoning) when agent succeeds."""
    from agents.assessment import generate_assessment_questions

    batch = _make_valid_batch()
    mock_output = _batch_to_json(batch)

    agent = MagicMock()
    agent.run = AsyncMock(return_value=mock_output)

    questions, reasoning = await generate_assessment_questions(
        agent=agent,
        cert_id="AZ-104",
        domain_weights={"Cloud Concepts": 0.5, "Networking": 0.5},
        learner_id="EMP-001",
    )

    assert len(questions) == 15
    assert reasoning == "Storage boosted due to weak performance."


@pytest.mark.asyncio
async def test_generate_assessment_questions_fallback_on_parse_failure() -> None:
    """generate_assessment_questions returns fallback questions when both LLM attempts fail."""
    from agents.assessment import generate_assessment_questions

    agent = MagicMock()
    agent.run = AsyncMock(return_value="INVALID JSON")

    questions, reasoning = await generate_assessment_questions(
        agent=agent,
        cert_id="AZ-104",
        domain_weights={"General": 1.0},
    )

    # Fallback must still return 15 questions
    assert len(questions) == 15
    assert all(q.id.startswith("fallback-") for q in questions)
    assert reasoning is None


@pytest.mark.asyncio
async def test_generate_assessment_questions_bare_array_accepted() -> None:
    """generate_assessment_questions accepts bare JSON array from agent."""
    from agents.assessment import generate_assessment_questions

    batch = _make_valid_batch()
    mock_output = json.dumps([q.model_dump() for q in batch])

    agent = MagicMock()
    agent.run = AsyncMock(return_value=mock_output)

    questions, reasoning = await generate_assessment_questions(
        agent=agent,
        cert_id="AZ-900",
        domain_weights={"General": 1.0},
    )

    assert len(questions) == 15
    assert reasoning is None
