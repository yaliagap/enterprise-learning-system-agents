"""Shared pytest fixtures for the enterprise-learning-system smoke test suite."""
from __future__ import annotations

import pytest

from workflow.state import LearnerContext, WorkflowState


@pytest.fixture()
def learner_context() -> LearnerContext:
    """Return a LearnerContext for EMP-001 with AZ-204-related topics.

    EMP-001 is the first persona in learner_profiles.json.
    Topics are az204-azure-compute and az204-storage-solutions, which map
    to the AZ-204 certification family used throughout the smoke tests.
    """
    return LearnerContext(
        learner_id="EMP-001",
        employee_id="EMP-001",
        topics=["az204-azure-compute", "az204-storage-solutions"],
        role="Cloud Engineer",
    )


@pytest.fixture()
def workflow_state(learner_context: LearnerContext) -> WorkflowState:
    """Return a freshly seeded WorkflowState for EMP-001 with AZ-204 topics."""
    return WorkflowState.seed(
        learner_id=learner_context.learner_id,
        employee_id=learner_context.employee_id,
        topics=learner_context.topics,
        role=learner_context.role,
    )
