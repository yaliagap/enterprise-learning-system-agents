"""Tests for CertOption model, extended WorkflowStatusLiteral, and WorkflowState new fields.

TDD: T1.4 — tests written before implementation.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from workflow.state import WorkflowState


class TestCertOption:
    """Capability 4: CertOption model validation."""

    def test_cert_option_all_required_fields(self) -> None:
        """CertOption parses correctly with all required fields."""
        from workflow.state import CertOption

        opt = CertOption(
            cert_id="AI-900",
            name="Azure AI Fundamentals",
            description="Foundational AI certification.",
            ms_learn_url="https://learn.microsoft.com/en-us/certifications/azure-ai-fundamentals/",
            recommendation_pct=85.0,
            already_obtained=False,
            level="Fundamentals",
        )
        assert opt.cert_id == "AI-900"
        assert opt.name == "Azure AI Fundamentals"
        assert opt.description == "Foundational AI certification."
        assert opt.ms_learn_url.startswith("https://")
        assert opt.recommendation_pct == 85.0
        assert opt.already_obtained is False
        assert opt.level == "Fundamentals"

    def test_cert_option_already_obtained_true(self) -> None:
        from workflow.state import CertOption

        opt = CertOption(
            cert_id="AI-900",
            name="Azure AI Fundamentals",
            description="",
            ms_learn_url="",
            recommendation_pct=85.0,
            already_obtained=True,
            level="Fundamentals",
        )
        assert opt.already_obtained is True

    def test_cert_option_recommendation_pct_typed_as_float(self) -> None:
        from workflow.state import CertOption

        opt = CertOption(
            cert_id="AI-102",
            name="Designing and Implementing Microsoft Azure AI Solutions",
            description="",
            ms_learn_url="",
            recommendation_pct=65.5,
            already_obtained=False,
            level="Associate",
        )
        assert isinstance(opt.recommendation_pct, float)

    def test_cert_option_zero_recommendation_pct(self) -> None:
        from workflow.state import CertOption

        opt = CertOption(
            cert_id="DP-100",
            name="Designing a Data Science Solution",
            description="",
            ms_learn_url="",
            recommendation_pct=0.0,
            already_obtained=False,
            level="Associate",
        )
        assert opt.recommendation_pct == 0.0


class TestWorkflowStatusExtensions:
    """New status literals are accepted by Pydantic validator."""

    def test_awaiting_cert_selection_is_valid(self) -> None:
        state = WorkflowState.seed(
            learner_id="EMP-001",
            employee_id="EMP-001",
            topics=["azure-ai"],
            role="AI Engineer",
        )
        state.workflow_status = "awaiting_cert_selection"
        # Re-validate
        validated = WorkflowState.model_validate(state.model_dump())
        assert validated.workflow_status == "awaiting_cert_selection"

    def test_awaiting_path_confirmation_is_valid(self) -> None:
        state = WorkflowState.seed(
            learner_id="EMP-001",
            employee_id="EMP-001",
            topics=["azure-ai"],
            role="AI Engineer",
        )
        state.workflow_status = "awaiting_path_confirmation"
        validated = WorkflowState.model_validate(state.model_dump())
        assert validated.workflow_status == "awaiting_path_confirmation"

    def test_invalid_status_raises_validation_error(self) -> None:
        with pytest.raises((ValidationError, Exception)):
            WorkflowState(
                learner={"learner_id": "X", "employee_id": "X", "role": "Eng", "topics": ["t"]},
                workflow_status="not_a_valid_status",  # type: ignore[arg-type]
            )


class TestWorkflowStateNewFields:
    """WorkflowState cert_options and selected_cert_id fields."""

    def test_cert_options_defaults_to_empty_list(self) -> None:
        state = WorkflowState.seed(
            learner_id="EMP-001",
            employee_id="EMP-001",
            topics=["azure-ai"],
            role="AI Engineer",
        )
        assert state.cert_options == []

    def test_selected_cert_id_defaults_to_none(self) -> None:
        state = WorkflowState.seed(
            learner_id="EMP-001",
            employee_id="EMP-001",
            topics=["azure-ai"],
            role="AI Engineer",
        )
        assert state.selected_cert_id is None

    def test_cert_options_can_be_populated(self) -> None:
        from workflow.state import CertOption

        state = WorkflowState.seed(
            learner_id="EMP-001",
            employee_id="EMP-001",
            topics=["azure-ai"],
            role="AI Engineer",
        )
        state.cert_options = [
            CertOption(
                cert_id="AI-900",
                name="Azure AI Fundamentals",
                description="",
                ms_learn_url="",
                recommendation_pct=90.0,
                already_obtained=False,
                level="Fundamentals",
            )
        ]
        assert len(state.cert_options) == 1
        assert state.cert_options[0].cert_id == "AI-900"

    def test_selected_cert_id_can_be_set(self) -> None:
        state = WorkflowState.seed(
            learner_id="EMP-001",
            employee_id="EMP-001",
            topics=["azure-ai"],
            role="AI Engineer",
        )
        state.selected_cert_id = "AI-900"
        assert state.selected_cert_id == "AI-900"
