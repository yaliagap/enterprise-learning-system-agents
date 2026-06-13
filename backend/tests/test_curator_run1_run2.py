"""Tests for T3.2 — Curator agent factory wiring (two-run redesign).

Covers:
- create_curator_run1 returns an Agent with get_learner_profile and search_knowledge_base tools
- create_curator_run2 returns an Agent with ms_learn_* and get_certification_info tools
- _parse_cert_options correctly parses the Run 1 JSON response
- already_obtained tagging logic works
- Seniority ordering: junior profile → fundamentals cert ranked first
- Empty KB response → cert_options can still be populated from LLM reasoning

Run from backend/:
    pytest tests/test_curator_run1_run2.py -v
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from workflow.state import CertOption


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run1_json(certs: list[dict] | None = None) -> str:
    """Build a valid Run 1 JSON response string."""
    if certs is None:
        certs = [
            {
                "cert_id": "AI-900",
                "name": "Azure AI Fundamentals",
                "description": "Entry-level AI cert",
                "ms_learn_url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-fundamentals/",
                "recommendation_pct": 90.0,
                "already_obtained": False,
                "level": "fundamentals",
            },
            {
                "cert_id": "AI-102",
                "name": "Designing and Implementing Azure AI Solutions",
                "description": "Associate-level AI cert",
                "ms_learn_url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-engineer/",
                "recommendation_pct": 70.0,
                "already_obtained": False,
                "level": "associate",
            },
        ]
    return json.dumps({"cert_options": certs, "reasoning": "Test reasoning paragraph."})


# ---------------------------------------------------------------------------
# T3.2-A: Factory tool wiring
# ---------------------------------------------------------------------------


def _agent_tool_names(agent) -> list[str]:
    """Extract tool names from a MAF Agent's default_options['tools'] list."""
    tools = agent.default_options.get("tools", [])
    names = []
    for t in tools:
        # FunctionTool wraps a callable and has a .name attribute
        name = getattr(t, "name", None) or getattr(t, "__name__", None) or str(t)
        names.append(name)
    return names


def test_create_curator_run1_has_correct_tools() -> None:
    """create_curator_run1 must register get_learner_profile and search_knowledge_base."""
    from agents.curator import create_curator_run1

    mock_client = MagicMock()
    agent = create_curator_run1(mock_client)

    tool_names = _agent_tool_names(agent)
    assert "get_learner_profile" in tool_names
    assert "search_knowledge_base" in tool_names


def test_create_curator_run1_does_not_have_run2_tools() -> None:
    """Run 1 agent must NOT have ms_learn or get_certification_info tools."""
    from agents.curator import create_curator_run1

    mock_client = MagicMock()
    agent = create_curator_run1(mock_client)

    tool_names = _agent_tool_names(agent)
    assert "get_certification_info" not in tool_names
    assert "ms_learn_microsoft_docs_search" not in tool_names


def test_create_curator_run2_has_correct_tools() -> None:
    """create_curator_run2 must use only MS Learn MCP tools — no get_certification_info."""
    from agents.curator import create_curator_run2

    mock_client = MagicMock()
    mock_mcp = MagicMock()
    mock_mcp.functions = []
    agent = create_curator_run2(mock_client, mock_mcp)

    tool_names = _agent_tool_names(agent)
    assert "get_certification_info" not in tool_names


def test_create_curator_run2_does_not_have_run1_tools() -> None:
    """Run 2 agent must NOT have search_knowledge_base or get_learner_profile tools."""
    from agents.curator import create_curator_run2

    mock_client = MagicMock()
    mock_mcp = MagicMock()
    mock_mcp.functions = []
    agent = create_curator_run2(mock_client, mock_mcp)

    tool_names = _agent_tool_names(agent)
    assert "search_knowledge_base" not in tool_names
    assert "get_learner_profile" not in tool_names


# ---------------------------------------------------------------------------
# T3.2-B: _parse_cert_options helper
# ---------------------------------------------------------------------------


def test_parse_cert_options_valid_json() -> None:
    """_parse_cert_options must return a list of CertOption from valid Run 1 JSON."""
    from agents.curator import _parse_cert_options

    raw = _make_run1_json()
    result = _parse_cert_options(raw)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(o, CertOption) for o in result)
    assert result[0].cert_id == "AI-900"
    assert result[0].recommendation_pct == 90.0


def test_parse_cert_options_markdown_fences_stripped() -> None:
    """_parse_cert_options must strip ```json ... ``` fences before parsing."""
    from agents.curator import _parse_cert_options

    inner = _make_run1_json()
    fenced = f"```json\n{inner}\n```"
    result = _parse_cert_options(fenced)

    assert len(result) == 2
    assert result[0].cert_id == "AI-900"


def test_parse_cert_options_invalid_json_returns_empty() -> None:
    """_parse_cert_options must return [] when JSON cannot be parsed."""
    from agents.curator import _parse_cert_options

    result = _parse_cert_options("This is not JSON at all.")
    assert result == []


def test_parse_cert_options_missing_key_returns_empty() -> None:
    """_parse_cert_options must return [] when cert_options key is absent."""
    from agents.curator import _parse_cert_options

    result = _parse_cert_options(json.dumps({"reasoning": "some text"}))
    assert result == []


# ---------------------------------------------------------------------------
# T3.2-C: already_obtained tagging
# ---------------------------------------------------------------------------


def test_parse_cert_options_already_obtained_true() -> None:
    """When already_obtained=True in JSON, CertOption.already_obtained must be True."""
    from agents.curator import _parse_cert_options

    certs = [
        {
            "cert_id": "AI-900",
            "name": "Azure AI Fundamentals",
            "description": "",
            "ms_learn_url": "",
            "recommendation_pct": 80.0,
            "already_obtained": True,
            "level": "fundamentals",
        }
    ]
    result = _parse_cert_options(json.dumps({"cert_options": certs, "reasoning": ""}))
    assert len(result) == 1
    assert result[0].already_obtained is True


def test_parse_cert_options_already_obtained_false() -> None:
    """When already_obtained=False in JSON, CertOption.already_obtained must be False."""
    from agents.curator import _parse_cert_options

    certs = [
        {
            "cert_id": "AZ-900",
            "name": "Azure Fundamentals",
            "description": "",
            "ms_learn_url": "",
            "recommendation_pct": 85.0,
            "already_obtained": False,
            "level": "fundamentals",
        }
    ]
    result = _parse_cert_options(json.dumps({"cert_options": certs, "reasoning": ""}))
    assert result[0].already_obtained is False


# ---------------------------------------------------------------------------
# T3.2-D: Seniority ordering — junior → fundamentals first
# ---------------------------------------------------------------------------


def test_parse_cert_options_ordered_by_recommendation_pct_descending() -> None:
    """cert_options must be ordered by recommendation_pct descending after parsing."""
    from agents.curator import _parse_cert_options

    certs = [
        {
            "cert_id": "AI-102",
            "name": "AI Engineer",
            "description": "",
            "ms_learn_url": "",
            "recommendation_pct": 60.0,
            "already_obtained": False,
            "level": "associate",
        },
        {
            "cert_id": "AI-900",
            "name": "AI Fundamentals",
            "description": "",
            "ms_learn_url": "",
            "recommendation_pct": 90.0,
            "already_obtained": False,
            "level": "fundamentals",
        },
    ]
    result = _parse_cert_options(json.dumps({"cert_options": certs, "reasoning": ""}))
    # Should be ordered descending by recommendation_pct
    assert result[0].cert_id == "AI-900"
    assert result[1].cert_id == "AI-102"


# ---------------------------------------------------------------------------
# T3.2-E: Empty KB response → cert_options can still be populated
# ---------------------------------------------------------------------------


def test_parse_cert_options_with_empty_kb_context() -> None:
    """Even when KB context is empty, as long as LLM returns valid JSON, parse succeeds."""
    from agents.curator import _parse_cert_options

    # Simulate LLM reasoning without KB data by using a valid JSON output
    certs = [
        {
            "cert_id": "AZ-900",
            "name": "Azure Fundamentals",
            "description": "Foundational Azure cert",
            "ms_learn_url": "https://learn.microsoft.com/",
            "recommendation_pct": 75.0,
            "already_obtained": False,
            "level": "fundamentals",
        }
    ]
    raw = json.dumps({"cert_options": certs, "reasoning": "KB returned no results but inferred from role."})
    result = _parse_cert_options(raw)

    assert len(result) == 1
    assert result[0].cert_id == "AZ-900"


# ---------------------------------------------------------------------------
# T3.2-F: _SYSTEM_PROMPT_RUN1 and _SYSTEM_PROMPT_RUN2 exist
# ---------------------------------------------------------------------------


def test_system_prompts_exist() -> None:
    """Both _SYSTEM_PROMPT_RUN1 and _SYSTEM_PROMPT_RUN2 must be importable strings."""
    import agents.curator as curator_module

    assert hasattr(curator_module, "_SYSTEM_PROMPT_RUN1")
    assert hasattr(curator_module, "_SYSTEM_PROMPT_RUN2")
    assert isinstance(curator_module._SYSTEM_PROMPT_RUN1, str)
    assert isinstance(curator_module._SYSTEM_PROMPT_RUN2, str)
    assert len(curator_module._SYSTEM_PROMPT_RUN1) > 50
    assert len(curator_module._SYSTEM_PROMPT_RUN2) > 50
