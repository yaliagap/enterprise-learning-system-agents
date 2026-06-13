"""MAF @tool functions that wrap Foundry IQ: semantic resource search and cert catalog."""
from __future__ import annotations

import json
from typing import Annotated

import httpx
from agent_framework import tool
from pydantic import BaseModel, Field

import config
from grounding.base import CertificationInfo, FoundryIQResult
from grounding.factory import IQProviderFactory

_KB_MOCK_RESPONSE = (
    "Azure certifications overview (mock): "
    "AI-900 (Azure AI Fundamentals) is the entry-level AI certification. "
    "AI-102 (Designing and Implementing Microsoft Azure AI Solutions) targets AI Engineers. "
    "AZ-900 covers Azure cloud fundamentals. "
    "AZ-104 is for Azure Administrators. "
    "DP-203 is for Data Engineers working with Azure data solutions."
)


# ---------------------------------------------------------------------------
# Return models
# ---------------------------------------------------------------------------


class SearchLearningResourcesResult(BaseModel):
    """Ranked list of learning resources matching a semantic search query."""

    query: str
    cert_id: str | None
    top_k: int
    results: list[FoundryIQResult]


class GetResourceByIdResult(BaseModel):
    """A single learning resource looked up by its resource_id."""

    resource_id: str
    found: bool
    resource: FoundryIQResult | None = None


class GetResourcesForCertificationResult(BaseModel):
    """All learning resources associated with a specific certification."""

    cert_id: str
    results: list[FoundryIQResult]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


@tool
def search_learning_resources(
    query: Annotated[str, Field(description="Natural-language search query for learning resources.")],
    cert_id: Annotated[
        str | None,
        Field(description="Optional certification ID to restrict results (e.g. 'AZ-104'). Pass null to search all certs."),
    ] = None,
    top_k: Annotated[
        int,
        Field(description="Maximum number of results to return.", ge=1, le=20),
    ] = 5,
) -> SearchLearningResourcesResult:
    """Search learning resources semantically; optionally filter by certification ID."""
    foundry = IQProviderFactory().foundry()
    cert_ids = [cert_id] if cert_id else None
    results = foundry.search(query=query, cert_ids=cert_ids, k=top_k)
    return SearchLearningResourcesResult(
        query=query,
        cert_id=cert_id,
        top_k=top_k,
        results=results,
    )


@tool
def get_resource_by_id(
    resource_id: Annotated[str, Field(description="The unique resource identifier, e.g. 'RES-001'.")],
) -> GetResourceByIdResult:
    """Retrieve a single learning resource by its exact resource_id."""
    foundry = IQProviderFactory().foundry()
    # Use the resource title as a targeted query and filter by exact ID match
    # The mock provider searches by vector similarity; do a broad search and filter.
    results = foundry.search(query=resource_id, k=20)
    matched = next((r for r in results if r.resource_id == resource_id), None)
    return GetResourceByIdResult(
        resource_id=resource_id,
        found=matched is not None,
        resource=matched,
    )


@tool
def get_resources_for_certification(
    cert_id: Annotated[str, Field(description="Certification ID to retrieve all associated resources for, e.g. 'AZ-104'.")],
) -> GetResourcesForCertificationResult:
    """Return all learning resources associated with a specific certification."""
    foundry = IQProviderFactory().foundry()
    results = foundry.search(query=cert_id, cert_ids=[cert_id], k=20)
    return GetResourcesForCertificationResult(cert_id=cert_id, results=results)


@tool
async def search_knowledge_base(
    query: Annotated[
        str,
        Field(description="Natural language question about Azure certifications, max 400 chars"),
    ],
) -> str:
    """Search the enterprise Knowledge Base for cert recommendations and learning guidance."""
    if not config.USE_REAL_IQ:
        return _KB_MOCK_RESPONSE

    # Truncate query to 400 chars before sending
    truncated_query = query[:400]

    endpoint = config.AZURE_SEARCH_ENDPOINT
    kb_name = config.FOUNDRY_IQ_KB_NAME
    api_key = config.AZURE_SEARCH_API_KEY
    url = f"{endpoint}/knowledgebases/{kb_name}/mcp?api-version=2026-05-01-preview"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"queries": [truncated_query]},
                headers={"api-key": api_key},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return f"Knowledge base search failed: HTTP {exc.response.status_code} — {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"Knowledge base search failed: {exc}"

    # Parse SSE response: find line starting with `data:` → json.loads → extract text
    raw_content = response.content.decode("utf-8", errors="replace")
    for line in raw_content.splitlines():
        if line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            try:
                parsed = json.loads(data_str)
                return parsed["result"]["content"][0]["text"]
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                return f"Knowledge base search failed: could not parse SSE payload — {exc}"

    return "Knowledge base search failed: no data line found in SSE response"
