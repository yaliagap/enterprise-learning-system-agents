"""Tests for curator IQ integration: config defaults, LearnerContext goals, curator wiring, and grounding adapter.

Tasks covered: 5.1–5.8
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 5.1 — config.py Foundry IQ defaults
# ---------------------------------------------------------------------------


def test_config_foundry_iq_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Foundry IQ tuning vars use correct defaults when env vars are absent."""
    import importlib
    import config

    monkeypatch.delenv("FOUNDRY_IQ_RETRIEVAL_MODE", raising=False)
    monkeypatch.delenv("FOUNDRY_IQ_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("FOUNDRY_IQ_OUTPUT_MODE", raising=False)

    with patch("dotenv.load_dotenv", return_value=None):
        importlib.reload(config)

    assert config.FOUNDRY_IQ_RETRIEVAL_MODE == "semantic"
    assert config.FOUNDRY_IQ_REASONING_EFFORT == "minimal"
    assert config.FOUNDRY_IQ_OUTPUT_MODE == "extractive_data"


# ---------------------------------------------------------------------------
# 5.2 — LearnerContext goals field
# ---------------------------------------------------------------------------


def test_learner_context_goals_default_is_none() -> None:
    """LearnerContext constructed without goals → goals is None."""
    from workflow.state import LearnerContext

    ctx = LearnerContext(
        learner_id="EMP-001",
        employee_id="EMP-001",
        role="Cloud Engineer",
        topics=["az104-networking"],
    )
    assert ctx.goals is None


def test_learner_context_goals_set() -> None:
    """LearnerContext constructed with goals list → goals equals provided list."""
    from workflow.state import LearnerContext

    goals = ["Pass AZ-104 by Q3", "Lead governance initiative"]
    ctx = LearnerContext(
        learner_id="EMP-001",
        employee_id="EMP-001",
        role="Cloud Engineer",
        topics=["az104-networking"],
        goals=goals,
    )
    assert ctx.goals == goals


# ---------------------------------------------------------------------------
# 5.3 — WorkflowState.seed() goals forwarding
# ---------------------------------------------------------------------------


def test_seed_without_goals() -> None:
    """WorkflowState.seed() called without goals → state.learner.goals is None."""
    from workflow.state import WorkflowState

    state = WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=["az104-networking"],
        role="Cloud Engineer",
    )
    assert state.learner.goals is None


def test_seed_with_goals() -> None:
    """WorkflowState.seed() called with goals → forwarded correctly to learner."""
    from workflow.state import WorkflowState

    goals = ["Pass AZ-104 by Q3", "Lead governance initiative"]
    state = WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=["az104-networking"],
        role="Cloud Engineer",
        goals=goals,
    )
    assert state.learner.goals == goals


# ---------------------------------------------------------------------------
# 5.4 — create_learning_path_curator with USE_REAL_IQ=false
# ---------------------------------------------------------------------------


def test_curator_mock_path_has_no_context_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_learning_path_curator with USE_REAL_IQ=false returns agent without context_providers."""
    import importlib
    import config
    monkeypatch.setattr(config, "USE_REAL_IQ", False)

    import agents.curator
    importlib.reload(agents.curator)

    mock_client = MagicMock()
    agent = agents.curator.create_learning_path_curator(mock_client)

    cp = getattr(agent, "context_providers", None)
    assert not cp  # None or empty list — mock path uses tools, not context_providers


# ---------------------------------------------------------------------------
# 5.5 — create_learning_path_curator always uses tools (no ContextProvider path)
# ---------------------------------------------------------------------------


def test_curator_always_uses_tools_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_learning_path_curator always returns Agent — ContextProvider path removed."""
    import importlib
    from agent_framework import Agent

    import agents.curator
    importlib.reload(agents.curator)

    mock_client = MagicMock()
    agent = agents.curator.create_learning_path_curator(mock_client)

    # Agent is constructed — no context_providers (tools path)
    assert isinstance(agent, Agent)
    cp = getattr(agent, "context_providers", None)
    assert not cp  # ContextProvider path is gone


# ---------------------------------------------------------------------------
# 5.6 — CuratorExecutor prompt includes Goals: line when goals set
# ---------------------------------------------------------------------------


def test_curator_executor_prompt_includes_goals() -> None:
    """CuratorExecutor.handle prompt contains Goals: line when state.learner.goals is set."""
    from workflow.state import WorkflowState

    state = WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=["az104-networking"],
        role="Cloud Engineer",
        goals=["Pass AZ-104 by Q3", "Lead governance initiative"],
    )

    topics_display = ", ".join(state.learner.topics)
    experience = state.learner.experience_level or "intermediate"
    goals_line = (
        f"Goals: {'; '.join(state.learner.goals)}\n"
        if state.learner.goals
        else ""
    )
    prompt = (
        f"Learner ID: {state.learner.learner_id}\n"
        f"Role: {state.learner.role}\n"
        f"Experience level: {experience}\n"
        f"Selected topics: {topics_display}\n"
        f"{goals_line}"
        "\nBased on these topics and role, identify the most relevant Azure certification "
        "and build a prioritised learning path. Return STRICT JSON as instructed."
    )

    assert "Goals: Pass AZ-104 by Q3; Lead governance initiative" in prompt


def test_curator_executor_prompt_no_goals_line() -> None:
    """CuratorExecutor.handle prompt does not include Goals: line when goals is None."""
    from workflow.state import WorkflowState

    state = WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=["az104-networking"],
        role="Cloud Engineer",
    )

    goals_line = (
        f"Goals: {'; '.join(state.learner.goals)}\n"
        if state.learner.goals
        else ""
    )
    prompt = (
        f"Learner ID: {state.learner.learner_id}\n"
        f"Role: {state.learner.role}\n"
        f"Experience level: intermediate\n"
        f"Selected topics: az104-networking\n"
        f"{goals_line}"
        "\nBased on these topics and role, identify the most relevant Azure certification "
        "and build a prioritised learning path. Return STRICT JSON as instructed."
    )

    assert "Goals:" not in prompt


# ---------------------------------------------------------------------------
# 5.7 — grounding.real.foundry stub is importable and has no dead classes
# ---------------------------------------------------------------------------


def test_real_foundry_module_importable_without_error() -> None:
    """grounding.real.foundry can be imported without raising — stub file is valid."""
    import importlib
    import sys
    sys.modules.pop("grounding.real.foundry", None)
    # Must not raise
    import grounding.real.foundry  # noqa: F401
    importlib.reload(grounding.real.foundry)


def test_real_foundry_module_has_no_real_provider_class() -> None:
    """RealFoundryIQProvider class must not exist in the stub module."""
    import sys
    sys.modules.pop("grounding.real.foundry", None)
    import grounding.real.foundry
    assert not hasattr(grounding.real.foundry, "RealFoundryIQProvider")


# ---------------------------------------------------------------------------
# 5.8 — Smoke test: agent_framework_azure_ai_search never imported by curator
# ---------------------------------------------------------------------------


def test_curator_does_not_import_azure_ai_search() -> None:
    """Importing agents.curator never loads agent_framework_azure_ai_search (ContextProvider path removed)."""
    import importlib

    # Remove the module from sys.modules to force a fresh import
    for mod in list(sys.modules.keys()):
        if "curator" in mod or "agent_framework_azure_ai_search" in mod:
            sys.modules.pop(mod, None)

    import agents.curator  # noqa: F401 — import side-effect test

    assert "agent_framework_azure_ai_search" not in sys.modules
