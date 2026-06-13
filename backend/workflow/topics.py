"""Predefined Azure certification topic taxonomy.

This module is the backend source of truth for the closed vocabulary of Azure
certification topics that learners may select. The middleware imports AZURE_TOPICS
to enforce that only known topic IDs are accepted.

Frontend mirror: frontend/app/lib/topics.ts — keep in sync.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Flat tuple of all valid topic IDs (closed vocabulary — no free text allowed)
# ---------------------------------------------------------------------------

AZURE_TOPICS: tuple[str, ...] = (
    # AZ-900 — Fundamentals
    "az900-cloud-concepts",
    "az900-azure-architecture",
    "az900-management-governance",
    "az900-security-compliance",
    "az900-pricing-support",
    # AZ-104 — Azure Administrator (Associate)
    "az104-identity-access",
    "az104-networking",
    "az104-storage",
    "az104-compute",
    "az104-monitoring",
    # AZ-204 — Azure Developer (Associate)
    "az204-azure-compute",
    "az204-storage-solutions",
    "az204-security-solutions",
    "az204-api-management",
    "az204-event-driven",
    "az204-caching-cdn",
    # AZ-305 — Azure Solutions Architect (Expert)
    "az305-identity-governance",
    "az305-data-storage-design",
    "az305-business-continuity",
    "az305-infrastructure-design",
    "az305-app-architecture",
    "az305-migration",
    # AZ-400 — Azure DevOps Engineer (Expert)
    "az400-devops-processes",
    "az400-source-control",
    "az400-ci-pipelines",
    "az400-cd-release",
    "az400-security-compliance",
    # AI-102 — Azure AI Engineer (Associate)
    "ai102-ai-workloads",
    "ai102-computer-vision",
    "ai102-nlp",
    "ai102-knowledge-mining",
    "ai102-conversational-ai",
    # DP-203 — Azure Data Engineer (Associate)
    "dp203-data-storage",
    "dp203-data-processing",
    "dp203-data-security",
)

# ---------------------------------------------------------------------------
# Mapping: topic ID -> list of candidate certification exam IDs
# Used as a soft grounding hint in the curator prompt and for fallback inference.
# ---------------------------------------------------------------------------

TOPIC_DOMAINS: dict[str, list[str]] = {
    # AZ-900
    "az900-cloud-concepts": ["AZ-900"],
    "az900-azure-architecture": ["AZ-900"],
    "az900-management-governance": ["AZ-900"],
    "az900-security-compliance": ["AZ-900"],
    "az900-pricing-support": ["AZ-900"],
    # AZ-104
    "az104-identity-access": ["AZ-104"],
    "az104-networking": ["AZ-104"],
    "az104-storage": ["AZ-104"],
    "az104-compute": ["AZ-104"],
    "az104-monitoring": ["AZ-104"],
    # AZ-204
    "az204-azure-compute": ["AZ-204"],
    "az204-storage-solutions": ["AZ-204"],
    "az204-security-solutions": ["AZ-204"],
    "az204-api-management": ["AZ-204"],
    "az204-event-driven": ["AZ-204"],
    "az204-caching-cdn": ["AZ-204"],
    # AZ-305
    "az305-identity-governance": ["AZ-305"],
    "az305-data-storage-design": ["AZ-305"],
    "az305-business-continuity": ["AZ-305"],
    "az305-infrastructure-design": ["AZ-305"],
    "az305-app-architecture": ["AZ-305"],
    "az305-migration": ["AZ-305"],
    # AZ-400
    "az400-devops-processes": ["AZ-400"],
    "az400-source-control": ["AZ-400"],
    "az400-ci-pipelines": ["AZ-400"],
    "az400-cd-release": ["AZ-400"],
    "az400-security-compliance": ["AZ-400"],
    # AI-102
    "ai102-ai-workloads": ["AI-102"],
    "ai102-computer-vision": ["AI-102"],
    "ai102-nlp": ["AI-102"],
    "ai102-knowledge-mining": ["AI-102"],
    "ai102-conversational-ai": ["AI-102"],
    # DP-203
    "dp203-data-storage": ["DP-203"],
    "dp203-data-processing": ["DP-203"],
    "dp203-data-security": ["DP-203"],
}

# ---------------------------------------------------------------------------
# Human-readable labels (used for display by curator and frontend)
# ---------------------------------------------------------------------------

TOPIC_LABELS: dict[str, str] = {
    "az900-cloud-concepts": "Cloud Concepts",
    "az900-azure-architecture": "Azure Architecture & Services",
    "az900-management-governance": "Management & Governance",
    "az900-security-compliance": "Security, Compliance & Identity",
    "az900-pricing-support": "Pricing & Support",
    "az104-identity-access": "Identity & Access Management",
    "az104-networking": "Azure Networking",
    "az104-storage": "Azure Storage",
    "az104-compute": "Azure Compute (VMs, VMSS)",
    "az104-monitoring": "Monitoring & Backup",
    "az204-azure-compute": "Azure Compute Solutions",
    "az204-storage-solutions": "Azure Storage Solutions",
    "az204-security-solutions": "Azure Security Solutions",
    "az204-api-management": "API Management & Integration",
    "az204-event-driven": "Event-Based & Message Solutions",
    "az204-caching-cdn": "Caching & CDN",
    "az305-identity-governance": "Identity & Governance Design",
    "az305-data-storage-design": "Data Storage Design",
    "az305-business-continuity": "Business Continuity Design",
    "az305-infrastructure-design": "Infrastructure Solutions Design",
    "az305-app-architecture": "Application Architecture Design",
    "az305-migration": "Migration Design",
    "az400-devops-processes": "DevOps Processes & Agile",
    "az400-source-control": "Source Control Management",
    "az400-ci-pipelines": "CI Pipeline Design",
    "az400-cd-release": "CD & Release Management",
    "az400-security-compliance": "Security & Compliance in DevOps",
    "ai102-ai-workloads": "AI Workloads & Considerations",
    "ai102-computer-vision": "Computer Vision Solutions",
    "ai102-nlp": "Natural Language Processing",
    "ai102-knowledge-mining": "Knowledge Mining",
    "ai102-conversational-ai": "Conversational AI",
    "dp203-data-storage": "Data Storage Design",
    "dp203-data-processing": "Data Processing & Pipelines",
    "dp203-data-security": "Data Security & Compliance",
}

# Exam human-readable names (for recommended_cert_name display)
EXAM_NAMES: dict[str, str] = {
    "AZ-900": "Microsoft Azure Fundamentals",
    "AZ-104": "Microsoft Azure Administrator",
    "AZ-204": "Developing Solutions for Microsoft Azure",
    "AZ-305": "Designing Microsoft Azure Infrastructure Solutions",
    "AZ-400": "Designing and Implementing Microsoft DevOps Solutions",
    "AI-102": "Designing and Implementing a Microsoft Azure AI Solution",
    "DP-203": "Data Engineering on Microsoft Azure",
}
