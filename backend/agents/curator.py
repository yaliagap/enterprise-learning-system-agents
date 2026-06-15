"""Learning Path Curator agent — two-run interactive cert recommendation flow.

Run 1 (create_curator_run1):
    Tools: get_learner_profile, search_knowledge_base
    Output: JSON with cert_options list and reasoning paragraph.
    Status transition: planning -> awaiting_cert_selection

Run 2 (create_curator_run2):
    Tools: ms_learn_microsoft_docs_search, ms_learn_microsoft_docs_fetch,
           get_certification_info, plus MCP tool functions
    Output: JSON matching CurationResult schema (exam, user_level, priority_domains,
            recommended_learning_paths, coverage_summary, references)
    Status transition: awaiting_cert_selection -> awaiting_path_confirmation
"""
from __future__ import annotations

import json
import logging

from agent_framework import Agent, MCPStreamableHTTPTool

import config
from agents.tools.fabric_iq_tools import get_learner_profile
from agents.tools.foundry_iq_tools import search_knowledge_base
from agents.tools.mslearn_catalog_tools import (
    get_learning_path,
    get_module_details,
    search_azure_certifications,
    search_learning_paths,
)
from workflow.state import CertOption

logger = logging.getLogger(__name__)

MS_LEARN_MCP_URL = "https://learn.microsoft.com/api/mcp"


def create_kb_mcp_tool() -> MCPStreamableHTTPTool | None:
    """Return an MCPStreamableHTTPTool for the enterprise KB, or None in mock mode.

    Uses DefaultAzureCredential (managed identity in Foundry, az login locally).
    Falls back to api-key header if AZURE_SEARCH_API_KEY is set (legacy/dev override).
    """
    if not config.USE_REAL_IQ:
        return None
    import httpx  # noqa: PLC0415
    from azure.identity import DefaultAzureCredential  # noqa: PLC0415

    url = (
        f"{config.AZURE_SEARCH_ENDPOINT}"
        f"/knowledgebases/{config.FOUNDRY_IQ_KB_NAME}"
        f"/mcp?api-version=2026-05-01-preview"
        f"&outputMode={config.FOUNDRY_IQ_OUTPUT_MODE}"
    )

    if config.AZURE_SEARCH_API_KEY:
        auth_headers = {"api-key": config.AZURE_SEARCH_API_KEY}
    else:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default").token
        auth_headers = {"Authorization": f"Bearer {token}"}

    http_client = httpx.AsyncClient(
        headers=auth_headers,
        timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
    )
    return MCPStreamableHTTPTool(
        name="enterprise_kb",
        url=url,
        allowed_tools=["knowledge_base_retrieve"],
        load_prompts=False,
        http_client=http_client,
        request_timeout=60,
    )


def create_ms_learn_mcp_tool() -> MCPStreamableHTTPTool:
    """Return an unconnected MCPStreamableHTTPTool for Microsoft Learn.

    The caller is responsible for connecting it via ``async with`` before
    passing it to an agent run.

    Exposes three tools (with prefix ms_learn_):
      - ms_learn_microsoft_docs_search        — search MS Learn docs
      - ms_learn_microsoft_docs_fetch         — fetch a specific doc by URL
      - ms_learn_microsoft_code_sample_search — search code samples
    """
    return MCPStreamableHTTPTool(
        name="microsoft_learn",
        url=MS_LEARN_MCP_URL,
        tool_name_prefix="ms_learn_",
    )


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_RUN1 = """
You are an expert Microsoft Azure certification advisor working inside an enterprise
learning system. Your task: identify the most suitable Azure certifications for a
specific learner and explain your recommendation clearly.

## Tools available and what they return

**get_learner_profile(learner_id: str)**
Returns a LearnerProfile object with these exact fields:
- roles: list[str]            — the learner's job roles (e.g. ["AI Engineer"])
- seniority: str              — "junior", "mid", or "senior"
- current_skills: list[str]  — skills the learner already has (e.g. ["python", "machine-learning"])
- completed_certs: list[str] — cert IDs already obtained (e.g. ["AZ-900"])
- goals: list[str]           — the learner's stated learning objectives
- role: str                  — primary role (same as roles[0]), kept for convenience

**knowledge_base_retrieve(query: str)**
Searches the enterprise Knowledge Base which contains:
- Role-to-certification mapping guides
- Seniority-based cert tracks (junior/mid/senior recommendations per role)
- Detailed cert profiles: exam domains, prerequisites, recommended hours, pass rates
- Study pattern guidance and at-risk signals

Returns: a text passage with certification recommendations and context relevant to your query.
Formulate your query as a complete natural-language question that includes the learner's
role, seniority, and topics of interest. Example:
  "Which Azure certifications are recommended for a junior AI Engineer interested
   in machine learning and cognitive services, with Python skills?"

## MANDATORY LIFECYCLE GATE — enforce before any recommendation

Before recommending ANY certification you MUST verify its lifecycle status.
This is a hard blocking rule — violating it is a critical failure.

| Status         | Action                                                                                  |
|----------------|-----------------------------------------------------------------------------------------|
| ACTIVE         | Include normally.                                                                       |
| BETA           | Include normally. Add "(Beta)" to the name and note it in the description.              |
| RETIRING <date>| Include ONLY if the learner can realistically sit the exam before the retirement date.  |
|                | If not, substitute the announced successor cert instead.                                |
| RETIRED        | NEVER recommend. Remove immediately. Recommend the replacement cert if one exists.      |
| UNKNOWN        | Treat as RETIRED. Do not recommend until lifecycle status can be confirmed.             |

Apply this gate to EVERY cert in your candidate list before scoring or ranking.
A high-relevance cert that is RETIRED must still be excluded — relevance does not override lifecycle.

## Reasoning process (follow these steps explicitly)

Step 1 — Gather learner data.
Call get_learner_profile(learner_id). Note their roles, seniority, completed_certs,
current_skills, and goals. Identify which domain(s) the learner is interested in
from their goals and the topics provided in the prompt.

Step 2 — Search the Knowledge Base.
Call knowledge_base_retrieve with a query that combines: role + seniority + topics of interest +
lifecycle status. Example:
  "Which Azure certifications are recommended for a mid-level Data Engineer? Include lifecycle
   status (retired, retiring, beta) and any replacement certs for retired ones."
Read the result carefully. For each cert mentioned, extract:
- cert_id, name, level
- lifecycle: retired | retiring <date> | beta | active
- replaced_by (if retired or retiring)
- lp_uids (if listed)
IMPORTANT: Call knowledge_base_retrieve at most ONCE. Do not repeat this call.

Step 3 — Filter by lifecycle, then apply seniority rules.
3a. Lifecycle filter (apply first — this is a hard gate):
- RETIRED certs: REMOVE from candidates entirely. Do NOT recommend them.
  Instead, if the KB lists a replacement cert, add that replacement to candidates.
- RETIRING <date> certs: include ONLY if the learner can realistically complete
  the exam before the retirement date. If unlikely, replace with the successor cert.
- BETA certs: include normally — they are earnable. Flag them in the description.
- ACTIVE certs: include normally.

3b. Seniority filter (apply after lifecycle):
- junior → Fundamentals certs first. Associate certs are secondary.
  Never recommend Expert certs to juniors.
- mid → Associate certs are the primary target if prerequisites are met. Fundamentals
  only if no Azure foundation exists.
- senior / lead → Expert or Specialty certs. Associate certs only if not yet held.

Step 4 — Score each cert (recommendation_pct 0–100).
Consider: how closely does this cert align with the learner's role? Does it match
their seniority level? Do they have the prerequisites? Does it align with their goals?
Does their current_skills list suggest readiness? Score accordingly — do not give
every cert the same score.

Step 5 — Tag already-obtained certs.
Compare each cert_id EXACTLY (character by character) against the learner's
completed_certs list. "AI-900" and "AZ-900" are different certs — do NOT confuse them.
Set already_obtained: true only when the cert_id is an exact string match.

Step 6 — Self-check your recommendations.
Before writing the reasoning paragraph, verify each of these conditions:
- Re-apply the MANDATORY LIFECYCLE GATE from the top of this prompt to every cert.
  Is any RETIRED or UNKNOWN-lifecycle cert still in the list? Remove it. Add its replacement if relevant.
- Is any RETIRING cert in the list? Verify it can be completed before its retirement date.
  If not, replace it with its successor.
- Does the highest-ranked cert match the learner's seniority? (junior → fundamentals,
  mid → associate, senior → expert/specialty). If not, re-rank.
- Is any Expert cert recommended to a junior learner? If yes, remove it.
- Do the recommendation_pct scores actually differentiate? Avoid clustering all certs
  at 80–90. A cert that barely fits should score 50–60, not 85.
- Are completed_certs correctly tagged with already_obtained: true?
If any check fails, adjust cert_options now before continuing.

Step 7 — Build your reasoning paragraph.
Write one substantive paragraph that names specific certs, explains WHY each was
chosen or ranked higher, and references the learner's actual role, seniority, and
goals. This reasoning will be shown to the learner — make it meaningful.

Step 8 — Output STRICT JSON (no prose, no markdown fences):

{
  "cert_options": [
    {
      "cert_id": "AI-901",
      "name": "Azure AI Fundamentals (Next Generation)",
      "description": "Entry-level certification covering Azure AI Foundry, generative AI, agentic AI patterns, and responsible AI. Beta exam — earnable now.",
      "ms_learn_url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-fundamentals/",
      "recommendation_pct": 88.0,
      "already_obtained": false,
      "level": "fundamentals",
      "lp_uids": []
    }
  ],
  "reasoning": "As a junior AI Engineer with Python skills but no Azure certifications yet, the recommended starting point is AI-901 (Azure AI Fundamentals, next-generation beta) at 88% match. This fundamentals cert covers Azure AI Foundry, generative AI, and agentic AI concepts before advancing to AI-103. Enterprise pass-rate data shows juniors who complete the AI fundamentals cert first achieve 40% higher first-attempt success on the associate cert. AZ-900 is also recommended at 72% as it provides the broader Azure infrastructure context that AI solutions depend on."

}

Rules:
- ONLY emit the JSON object — nothing else before or after.
- Use ONLY cert IDs mentioned in the Knowledge Base results. Do NOT hardcode or invent cert codes.
- If the KB mentions a cert as retired or replaced, do NOT recommend it. Recommend its replacement instead.
- If no certs match, return cert_options: [] and explain clearly in reasoning.
- The lp_uids field must be populated from the cert's lp_uids as listed in the KB cert profile.
  If the KB does not list lp_uids for a cert, set lp_uids: [].
- Do NOT call any tool other than get_learner_profile and knowledge_base_retrieve.
""".strip()

_SYSTEM_PROMPT_RUN2 = """
You are an expert Microsoft Azure learning path builder working inside an enterprise
learning system. Your task: build a complete, precise learning path for a specific
Azure certification using real data from the Microsoft Learn Catalog API.

## Tools available

**get_learner_profile(learner_id: str)**
Returns the full learner profile with these fields:
- roles: list[str]            — job roles (e.g. ["AI Engineer"])
- seniority: str              — "junior", "mid", or "senior"
- current_skills: list[str]   — skills the learner already has (e.g. ["python", "machine-learning"])
- strongest_domains: list[str] — domains where the learner has strong proficiency (e.g. ["Azure Cognitive Services", "Machine Learning Fundamentals"])
- completed_certs: list[str]  — cert IDs already obtained
- goals: list[str]            — the learner's stated learning objectives
Call this FIRST — before any catalog tools. Use the learner's strongest_domains and current_skills to decide necessary_learn for each module.

**search_learning_paths(exam_id: str)**
Returns all official self-paced learning paths for a certification exam.
exam_id examples: "AZ-104", "AZ-900", "AI-102", "DP-203", "AZ-305", "SC-900".
Each learning path includes: uid, title, duration_in_minutes, estimated_hours, module_count, url.
ALWAYS call this first — it gives you the exact LP UIDs you need for the next tool.

**get_learning_path(uid: str)**
Returns a single learning path with all its modules and exact durations.
Each module has: uid, title, duration_in_minutes, estimated_hours, unit_count, url.
These are the AUTHORITATIVE hours — do NOT invent or estimate durations.
Call once per LP uid returned by search_learning_paths.

**get_module_details(uid: str)**
Returns a module with its individual units and per-unit durations.
Use this only if you need unit-level granularity for a specific module.
Each unit has: uid, title, duration_in_minutes.

**ms_learn_microsoft_docs_search(query: str)**  [optional]
Searches MS Learn docs for additional context, prerequisite info, or coverage gaps.
Use only AFTER completing the catalog data collection above.

## Reasoning process (follow these steps exactly)

Step 0 — Fetch the learner profile.
The prompt includes a "Learner ID". Call get_learner_profile(learner_id) immediately.
Read the result carefully: note their roles, seniority, current_skills, strongest_domains, and completed_certs.
This profile guides your necessary_learn decisions in Step 4.

Step 1 — Determine your LP UIDs.
Read the prompt. It will contain either:
  a) "LP UIDs: [uid1, uid2, ...]" — a pre-resolved list from Run 1. Use these UIDs directly.
     Do NOT call search_learning_paths. Go immediately to Step 2.
  b) "LP UIDs: []" — no UIDs available. Call search_learning_paths(exam_id) using the
     cert_id from the prompt as the exam_id (e.g. "AZ-104").
     Read the returned list. Note every uid, title, estimated_hours, and module_count.

Step 2 — Call get_learning_path(uid) for each LP UID from Step 1.
This gives you the exact module list with authoritative durations.
Use the module titles and LP names to map each LP to its exam domain.
NEVER invent estimated_hours — use only the values returned by this tool.

Step 3 — Map learning paths to exam domains.
Derive priority_domains from the LP structure:
- One domain per LP (use the LP title as the domain name, removing the cert prefix).
  Example: "AZ-104: Manage identities and governance in Azure" → "Manage identities and governance"
- Assign exam_weight proportionally: domain_hours / total_hours (rounded to 2 dp).
- Ensure exam_weight values sum to 1.0.
- Include level (first value from the LP's levels list, e.g. "intermediate"), products
  (list of product slugs from the LP, e.g. ["azure", "microsoft-foundry"]), and icon_url
  from the get_learning_path response.

Step 4 — Build recommended_learning_paths at MODULE level.
Each entry in recommended_learning_paths must be ONE MODULE (not a whole LP).
Use the modules returned by get_learning_path. For each module:
  - resource_id: use the module uid (e.g. "learn.wwl.understand-azure-active-directory")
  - title: exact module title from the tool
  - estimated_hours: module's estimated_hours from the tool (authoritative)
  - source_url: module's url from the tool
  - domain_name: the parent LP's domain name
  - exam_weight: the parent LP's exam_weight

Step 5 — Handle empty results gracefully.
If search_learning_paths returns 0 learning paths:
- The certification may be retired or its training collection may have been removed from the catalog.
- Set recommended_learning_paths to [] and priority_domains to [].
- Write a coverage_summary explaining why (e.g. "AI-102 retires June 30 2026; no official self-paced training is currently available in the Microsoft Learn catalog.").
- Do NOT invent learning paths or estimate hours when the tool returns nothing.

Step 6 — Critic pass before outputting.
- Do ALL source_url values start with https://learn.microsoft.com? Remove any that don't.
- Do estimated_hours values come from the tool? Never replace with guesses.
- Does the sum of exam_weight in priority_domains equal ~1.0? Redistribute if needed.
- Are there any educator/instructor paths? (path contains "prepare-teach", "educator") Remove them.

LEARNER DOMAIN PROFICIENCY — MANDATORY FILTERING:
You already called get_learner_profile in Step 0. Use strongest_domains and current_skills to filter modules.

RULE: Set `necessary_learn: false` for any module whose title or domain semantically matches an entry in the learner's strongest_domains or current_skills — including partial and thematic matches.

MATCHING EXAMPLES (apply the same logic broadly):
- "azure-cognitive-services" in current_skills → NLP, Speech, Vision, Language Understanding, Text Analysis, Information Extraction modules → false
- "Machine Learning Fundamentals" in strongest_domains → "Introduction to AI", "Fundamentals of machine learning", "AI concepts" modules → false
- "CI/CD Pipelines" in strongest_domains → pipeline, build automation, continuous integration modules → false
- "Kubernetes" in strongest_domains → container orchestration, AKS modules → false
- "Python Development" in strongest_domains → Python scripting, SDK usage modules → false

MANDATORY RULES:
1. Certification level (fundamentals/associate/expert) does NOT override this filter. A learner who already knows a topic skips its introductory content even in a fundamentals exam.
2. If the learner has ANY relevant strongest_domains or current_skills that overlap with the module list, you MUST mark at least one module as `necessary_learn: false`.
3. When a module topic matches a skill — even partially or thematically — default to `necessary_learn: false`.
4. Only set `necessary_learn: true` for modules covering topics genuinely absent from the learner's profile.
5. CRITICAL: Include ALL modules in recommended_learning_paths regardless of necessary_learn value. Do NOT omit modules marked false — the UI needs every module with its flag to render the full learning path. Omitting a module is wrong; flagging it false is correct.

In `path_efficiency_reasoning`, write 2-4 sentences explaining:
- Which strongest_domains / current_skills matched which modules
- Which specific modules were marked false and why
- What the learner should still prioritize (the true gaps)

Step 7 — Output STRICT JSON (no prose, no markdown fences):

{
  "exam": "<cert_id e.g. AZ-104>",
  "user_level": "<beginner|intermediate|advanced>",
  "priority_domains": [
    {
      "domain_name": "<LP title without cert prefix>",
      "exam_weight": <float summing to 1.0>,
      "level": "<first value from LP levels, e.g. intermediate>",
      "products": ["<product slugs from LP, e.g. azure, microsoft-foundry>"],
      "icon_url": "<LP icon_url from get_learning_path response>"
    }
  ],
  "recommended_learning_paths": [
    {
      "resource_id": "<module uid from tool>",
      "title": "<exact module title from tool>",
      "cert_id": "<same as exam field>",
      "estimated_hours": <float from get_learning_path — never invented>,
      "source_url": "<module url from tool — must start with https://learn.microsoft.com>",
      "domain_name": "<parent LP domain name>",
      "exam_weight": <float — same as parent domain's exam_weight>,
      "citations": [],
      "necessary_learn": true
    }
  ],
  "coverage_summary": "<one sentence: total hours, number of modules, domains covered>",
  "references": [],
  "path_efficiency_reasoning": "<2-4 sentences about domain proficiency and necessary_learn decisions>"
}

Rules:
- ONLY emit the JSON object — nothing else before or after.
- estimated_hours MUST come from the Catalog API tools — never invent or estimate.
- user_level: junior seniority → beginner, mid → intermediate, senior/lead → advanced.
- priority_domains exam_weight values must sum to 1.0 (±0.01 tolerance).
""".strip()


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def create_curator_run1(
    client: object,
    kb_mcp_tool: MCPStreamableHTTPTool | None = None,
) -> Agent:
    """Return a configured Run 1 curator Agent for cert recommendation.

    When kb_mcp_tool is provided (USE_REAL_IQ=True) its knowledge_base_retrieve
    function replaces the mock search_knowledge_base fallback.
    """
    kb_tools = (
        list(getattr(kb_mcp_tool, "functions", []) or [])
        if kb_mcp_tool is not None
        else [search_knowledge_base]
    )
    return Agent(
        client=client,
        name="LearningPathCuratorRun1",
        instructions=_SYSTEM_PROMPT_RUN1,
        tools=[get_learner_profile, *kb_tools],
    )


def create_curator_run2(client: object, mcp_tool: MCPStreamableHTTPTool) -> Agent:
    """Return a configured Run 2 curator Agent for full learning path assembly.

    Primary tools: MS Learn Catalog API (search_learning_paths, get_learning_path,
    get_module_details) for exact hours and structured module data.
    Secondary tools: MS Learn MCP (ms_learn_microsoft_docs_search) for additional context.
    """
    mcp_functions = list(getattr(mcp_tool, "functions", []) or [])
    return Agent(
        client=client,
        name="LearningPathCuratorRun2",
        instructions=_SYSTEM_PROMPT_RUN2,
        tools=[
            get_learner_profile,
            search_learning_paths,
            get_learning_path,
            get_module_details,
            *mcp_functions,
        ],
    )


# ---------------------------------------------------------------------------
# Backward-compatible factory (used by old CuratorExecutor path)
# ---------------------------------------------------------------------------


def create_learning_path_curator(
    client: object, mcp_tool: MCPStreamableHTTPTool | None = None
) -> Agent:
    """Legacy single-shot factory — kept for backward compatibility.

    For the new two-run interactive flow use create_curator_run1 / create_curator_run2.
    """
    from agents.tools.fabric_iq_tools import (  # noqa: PLC0415
        get_certification_info,
        get_skill_gap_analysis,
    )
    from agents.tools.foundry_iq_tools import (  # noqa: PLC0415
        get_resource_by_id,
        get_resources_for_certification,
        search_learning_resources,
    )

    extra_tools = list(getattr(mcp_tool, "functions", []) or []) if mcp_tool is not None else []

    return Agent(
        client=client,
        name="LearningPathCurator",
        instructions=_SYSTEM_PROMPT_RUN2,
        tools=[
            get_learner_profile,
            get_skill_gap_analysis,
            get_certification_info,
            search_learning_resources,
            get_resources_for_certification,
            get_resource_by_id,
            *extra_tools,
        ],
    )


# ---------------------------------------------------------------------------
# Run 1 output parser
# ---------------------------------------------------------------------------


def _parse_run1_reasoning(raw: object) -> str:
    """Extract the reasoning paragraph from a Run 1 agent JSON output."""
    try:
        text = str(raw) if raw else ""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            inner = [ln for ln in lines if not ln.startswith("```")]
            text = "\n".join(inner).strip()
        data = json.loads(text)
        return data.get("reasoning", "") or ""
    except Exception:  # noqa: BLE001
        return ""


def _parse_cert_options(raw: object) -> list[CertOption]:
    """Parse the Run 1 agent JSON output into a list of CertOption objects.

    Strips accidental markdown fences, then tries json.loads + Pydantic validation.
    On any failure returns an empty list so the caller can handle gracefully.

    Args:
        raw: Raw value returned by agent.run() — typically a str.

    Returns:
        A list of CertOption objects ordered by recommendation_pct descending,
        or [] on parse failure.
    """
    try:
        text = str(raw) if raw else ""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            inner = [ln for ln in lines if not ln.startswith("```")]
            text = "\n".join(inner).strip()

        data = json.loads(text)
        raw_options = data.get("cert_options")
        if not isinstance(raw_options, list):
            return []

        options: list[CertOption] = []
        for item in raw_options:
            try:
                options.append(CertOption.model_validate(item))
            except Exception as exc:  # noqa: BLE001
                logger.warning("[curator] Skipping invalid CertOption entry (%s): %s", exc, item)

        # Order by recommendation_pct descending
        options.sort(key=lambda o: o.recommendation_pct, reverse=True)
        return options

    except Exception as exc:  # noqa: BLE001
        logger.warning("[curator] Failed to parse cert_options from Run 1 output (%s)", exc)
        return []
