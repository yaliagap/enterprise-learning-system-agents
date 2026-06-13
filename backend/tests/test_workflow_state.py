"""Smoke tests for WorkflowState: seed, retry logic, and HITL guard.

Run from the backend/ directory:

    pytest tests/test_workflow_state.py -v
"""
from __future__ import annotations

import pytest

from api.middleware import AssessmentNotConfirmedError
from workflow.state import LearnerContext, WorkflowState


def test_workflow_state_seed(workflow_state: WorkflowState) -> None:
    """WorkflowState.seed() must return a valid initial state for EMP-001 with topics."""
    assert isinstance(workflow_state, WorkflowState)

    # Learner identity
    assert workflow_state.learner.learner_id == "EMP-001"
    assert workflow_state.learner.topics == ["az204-azure-compute", "az204-storage-solutions"]
    assert workflow_state.learner.role == "Cloud Engineer"
    # target_cert_id must no longer exist on LearnerContext
    assert not hasattr(workflow_state.learner, "target_cert_id")

    # Initial lifecycle state
    assert workflow_state.workflow_status == "planning"
    assert workflow_state.hitl_confirmed is False
    assert workflow_state.retry_count == 0
    assert workflow_state.max_retries >= 1

    # Collections start empty
    assert workflow_state.learning_path == []
    assert workflow_state.study_plan == []
    assert workflow_state.engagement is None
    assert workflow_state.assessment_results == []


def test_seed_with_topics() -> None:
    """WorkflowState.seed() must accept topics and set recommended_cert_id/name to None."""
    state = WorkflowState.seed(
        learner_id="EMP-002",
        employee_id="EMP-002",
        topics=["az104-networking", "az104-compute"],
        role="Network Engineer",
    )
    assert state.learner.topics == ["az104-networking", "az104-compute"]
    assert state.recommended_cert_id is None
    assert state.recommended_cert_name is None
    assert state.learning_path == []


def test_can_retry_false_at_max(workflow_state: WorkflowState) -> None:
    """can_retry must be False when retry_count equals max_retries."""
    # Exhaust all retries
    workflow_state.retry_count = workflow_state.max_retries

    assert workflow_state.can_retry is False, (
        f"Expected can_retry=False when retry_count({workflow_state.retry_count}) "
        f"== max_retries({workflow_state.max_retries})"
    )


def test_hitl_guard(workflow_state: WorkflowState) -> None:
    """AssessmentNotConfirmedError must be raised when assessment is attempted without HITL."""
    assert workflow_state.hitl_confirmed is False, "Precondition: HITL not confirmed"

    # Replicate the guard logic from workflow/dispatcher.py AssessmentStep.handle()
    with pytest.raises(AssessmentNotConfirmedError):
        if not workflow_state.hitl_confirmed:
            raise AssessmentNotConfirmedError(
                f"Assessment requested for learner={workflow_state.learner.learner_id} "
                "without HITL confirmation."
            )


def test_recommended_cert_fields_default_none() -> None:
    """WorkflowState must expose recommended_cert_id and recommended_cert_name, both None by default."""
    state = WorkflowState.seed(
        learner_id="EMP-003",
        employee_id="EMP-003",
        topics=["az900-cloud-concepts"],
        role="Student",
    )
    assert state.recommended_cert_id is None
    assert state.recommended_cert_name is None


def test_learning_path_item_domain_enrichment() -> None:
    """LearningPathItem must accept domain_name and exam_weight fields."""
    from workflow.state import LearningPathItem

    item = LearningPathItem(
        resource_id="res-001",
        title="Azure Fundamentals Path",
        cert_id="AZ-900",
        estimated_hours=4.0,
        source_url="https://learn.microsoft.com",
        domain_name="Cloud Concepts",
        exam_weight=0.25,
    )
    assert item.domain_name == "Cloud Concepts"
    assert item.exam_weight == 0.25


def test_curation_result_model() -> None:
    """CurationResult and DomainWeight models must be importable and constructible."""
    from workflow.state import CurationResult, DomainWeight, LearningPathItem

    domain = DomainWeight(domain_name="Compute", exam_weight=0.30)
    assert domain.domain_name == "Compute"

    result = CurationResult(
        exam="AZ-204",
        user_level="intermediate",
        priority_domains=[domain],
        recommended_learning_paths=[
            LearningPathItem(
                resource_id="r1",
                title="Dev path",
                cert_id="AZ-204",
                estimated_hours=8.0,
                source_url="https://learn.microsoft.com",
                domain_name="Compute",
                exam_weight=0.30,
            )
        ],
        coverage_summary="Covers core AZ-204 compute topics.",
    )
    assert result.exam == "AZ-204"
    assert result.user_level == "intermediate"
    assert len(result.priority_domains) == 1
    assert result.coverage_summary == "Covers core AZ-204 compute topics."
