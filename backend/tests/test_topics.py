"""Tests for workflow/topics.py — Azure topic taxonomy constants.

TDD Phase 1 tests (RED -> GREEN).
"""
from __future__ import annotations

from workflow.topics import AZURE_TOPICS, TOPIC_DOMAINS


def test_azure_topics_minimum_count() -> None:
    """AZURE_TOPICS must contain at least 30 topic IDs."""
    assert len(AZURE_TOPICS) >= 30, f"Expected >= 30 topics, got {len(AZURE_TOPICS)}"


def test_azure_topics_required_ids_present() -> None:
    """All IDs from the spec taxonomy table must be present in AZURE_TOPICS."""
    required = {
        "az900-cloud-concepts",
        "az900-azure-architecture",
        "az900-management-governance",
        "az900-security-compliance",
        "az900-pricing-support",
        "az104-identity-access",
        "az104-networking",
        "az104-storage",
        "az104-compute",
        "az104-monitoring",
        "az204-azure-compute",
        "az204-storage-solutions",
        "az204-security-solutions",
        "az204-api-management",
        "az204-event-driven",
        "az204-caching-cdn",
        "az305-identity-governance",
        "az305-data-storage-design",
        "az305-business-continuity",
        "az305-infrastructure-design",
        "az305-app-architecture",
        "az305-migration",
        "az400-devops-processes",
        "az400-source-control",
        "az400-ci-pipelines",
        "az400-cd-release",
        "az400-security-compliance",
        "ai102-ai-workloads",
        "ai102-computer-vision",
        "ai102-nlp",
        "ai102-knowledge-mining",
        "ai102-conversational-ai",
        "dp203-data-storage",
        "dp203-data-processing",
        "dp203-data-security",
    }
    missing = required - set(AZURE_TOPICS)
    assert not missing, f"Missing topic IDs: {missing}"


def test_azure_topics_contains_fundamentals_entry() -> None:
    """Basic smoke test: az900-cloud-concepts must be in AZURE_TOPICS."""
    assert "az900-cloud-concepts" in AZURE_TOPICS


def test_topic_domains_is_dict() -> None:
    """TOPIC_DOMAINS must be a dict mapping topic IDs to lists of cert families."""
    assert isinstance(TOPIC_DOMAINS, dict)


def test_topic_domains_keys_are_valid_topic_ids() -> None:
    """Every key in TOPIC_DOMAINS must be a valid topic ID from AZURE_TOPICS."""
    for key in TOPIC_DOMAINS:
        assert key in AZURE_TOPICS, f"TOPIC_DOMAINS key '{key}' not in AZURE_TOPICS"


def test_topic_domains_values_are_nonempty_lists() -> None:
    """Every value in TOPIC_DOMAINS must be a non-empty list of strings."""
    for key, val in TOPIC_DOMAINS.items():
        assert isinstance(val, list) and len(val) >= 1, (
            f"TOPIC_DOMAINS['{key}'] must be a non-empty list, got {val!r}"
        )
