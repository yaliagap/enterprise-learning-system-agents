"""Assessment Agent — grounded question generation via LLM with learner history.

generate_assessment_questions() generates exactly 15 questions for a given
certification, adapted to the learner's history, grounded via MS Learn MCP,
validated against the AssessmentQuestion Pydantic schema, and provides one
retry with corrective instruction on parse failure.
"""
from __future__ import annotations

import json
import logging
import textwrap

from agent_framework import Agent
from pydantic import TypeAdapter, ValidationError

from workflow.state import AssessmentQuestion

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Difficulty inference per cert
# ---------------------------------------------------------------------------

_CERT_DIFFICULTY: dict[str, str] = {
    "AZ-900": "fundamental",
    "SC-900": "fundamental",
    "AI-900": "fundamental",
    "DP-900": "fundamental",
    "AZ-104": "associate",
    "AZ-204": "associate",
    "AZ-400": "associate",
    "AI-102": "associate",
    "DP-203": "associate",
    "AZ-305": "expert",
    "AZ-500": "associate",
}

_DEFAULT_DIFFICULTY = "associate"

# ---------------------------------------------------------------------------
# Largest-remainder helper (deterministic integer allocation)
# ---------------------------------------------------------------------------


def _largest_remainder(weights: dict[str, float], total: int = 15) -> dict[str, int]:
    """Allocate *total* integers proportionally to *weights* using the largest-remainder method.

    Guarantees sum(result.values()) == total exactly.

    Args:
        weights: Mapping of domain_name → weight (float, any positive scale).
        total: Target integer total (default 15).

    Returns:
        Mapping of domain_name → integer question count.
    """
    if not weights:
        return {}

    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        # Equal distribution fallback
        per = total // len(weights)
        remainder = total % len(weights)
        result = {k: per for k in weights}
        for i, k in enumerate(weights):
            if i < remainder:
                result[k] += 1
        return result

    # Compute exact quotas and floor values
    exact: dict[str, float] = {k: v / weight_sum * total for k, v in weights.items()}
    floored: dict[str, int] = {k: int(v) for k, v in exact.items()}
    remainders: dict[str, float] = {k: exact[k] - floored[k] for k in exact}

    # Distribute leftover seats to domains with largest remainders
    leftover = total - sum(floored.values())
    sorted_keys = sorted(remainders, key=lambda k: remainders[k], reverse=True)
    result = dict(floored)
    for i in range(leftover):
        result[sorted_keys[i % len(sorted_keys)]] += 1

    return result


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert in Microsoft Azure certifications and an assessment
    question generator. Your goal is to generate exactly 15 high-quality,
    grounded, learner-adapted questions for the given certification.

    === YOUR TOOLS ===
    - get_learner_performance(learner_id, cert_id): returns the learner's
      history, including domain_scores and weak_areas from their last attempt.
    - search_knowledge_base(query): searches the internal knowledge base.
    - ms_learn_microsoft_docs_search(query): searches official Microsoft Learn docs.

    === GATHERING CONTEXT ===
    Before generating questions, gather:
    1. The learner's performance history (if any) via get_learner_performance.
    2. The OFFICIAL exam skill area names and weights for this certification.
       Use search_knowledge_base and/or ms_learn_microsoft_docs_search to find these.
       CRITICAL: the "domain" field in every question must use these official
       skill area names VERBATIM — never invent, rename, or use learning path
       module titles as domain names.
    3. Grounding references for each skill area: a real URL + title from
       ms_learn_microsoft_docs_search that supports the question's content.

    If a tool fails, returns an error, or returns empty/unhelpful results:
    try the other tool, rephrase the query, or fall back to your own trained
    knowledge of official Microsoft certification skill areas — as long as
    the names you use are real, accurate skill area names for this exam.
    Never fabricate a skill area name, and never fabricate a URL: if no
    real URL is found after reasonable attempts, set grounding_reference to null.

    === ADAPTIVE DISTRIBUTION (apply only if learner has history) ===
    Base weight per domain = official exam weight.
    For domains where domain_score < 0.70:
      gap = 0.70 - domain_score
      adjusted_weight = base_weight * (1 + gap / 0.70)
    Domains at or above 0.70 keep their base weight.
    Renormalize all adjusted weights to sum to 1.0, then convert to integer
    question counts summing to 15 (largest-remainder method).
    First-time learners (no history): use base weights directly.

    Write a "reasoning_distribution" paragraph explaining the resulting
    counts per domain — cite the learner's scores and any boosts applied,
    or state "first-time learner, using official base weights".

    === OUTPUT CONSTRAINTS (non-negotiable) ===
    - Exactly 15 questions total.
    - Difficulty: easy 5–7, medium 5–7, hard 2–4 (target ~40/40/20%).
    - Bloom's Taxonomy: Remember/Understand 4, Apply/Analyze 8, Evaluate/Create 3.
    - At least 4 questions with is_scenario_based: true. Scenario questions
      put the situation in "scenario_context" and the ask in "text";
      non-scenario questions set "scenario_context" to null.
    - question_type is either "multiple_choice" (exactly 1 correct_answer,
      4 options) or "multi_select" (ALWAYS exactly 2 correct_answers of 4
      options, and "text" must end with "(Select 2)"). Never make a
      multi_select where correct_answers count equals total options.
    - Per-domain question count must match the adjusted distribution (±1).

    === SELF-CHECK BEFORE RETURNING ===
    Review your 15 questions against the constraints above. If anything is
    off (wrong total, wrong difficulty/bloom spread, fewer than 4 scenarios,
    a domain off by more than 1, a malformed multi_select), fix it by
    regenerating only the affected questions — one corrective pass,
    then return your output regardless of remaining minor issues
    (note any unresolved issue briefly in reasoning_distribution).

    === OUTPUT FORMAT ===
    Return ONLY a valid JSON object, no prose, no markdown fences:
    {
      "questions": [
        {
          "id": "<unique string, e.g. q1>",
          "text": "<the question itself>",
          "question_type": "<multiple_choice | multi_select>",
          "options": ["<A>", "<B>", "<C>", "<D>"],
          "correct_answers": ["<correct option text — 1 for multiple_choice, 2 for multi_select>"],
          "domain": "<official skill area name>",
          "exam_weight_pct": <float 0–1, e.g. 0.20 for a 20% weight domain>,
          "explanation": "<2-4 sentence explanation>",
          "difficulty": "<easy | medium | hard>",
          "bloom_level": "<Remember | Understand | Apply | Analyze | Evaluate | Create>",
          "is_scenario_based": <true | false>,
          "scenario_context": "<scenario paragraph or null>",
          "grounding_reference": {
            "title": "<exact title from tool result>",
            "url": "<exact url from tool result, copied verbatim>",
            "type": "web"
          }
        }
      ],
      "reasoning_distribution": "<paragraph explaining domain allocation>"
    }

    Set grounding_reference to null if no real URL was found via tools.
    Never return fewer or more than 15 questions.
""")

# ---------------------------------------------------------------------------
# Corrective retry prompt
# ---------------------------------------------------------------------------

_CORRECTIVE_PROMPT = textwrap.dedent("""\
    Your previous response could not be parsed as a valid JSON object with a "questions" array.

    Please re-generate exactly 15 questions in STRICT JSON format:
    {
      "questions": [...15 question objects...],
      "reasoning_distribution": "<string>"
    }

    No markdown, no explanations outside the JSON.
    Alternatively, a bare JSON array starting with [ and ending with ] is also accepted.
""")

# ---------------------------------------------------------------------------
# Structural Critic check (Python post-parse)
# ---------------------------------------------------------------------------


def _check_batch(questions: list[AssessmentQuestion]) -> list[str]:
    """Run structural checks on a parsed batch. Returns list of issue descriptions."""
    issues: list[str] = []

    if len(questions) != 15:
        issues.append(f"Expected 15 questions, got {len(questions)}")

    scenario_count = sum(1 for q in questions if q.is_scenario_based)
    if scenario_count < 4:
        issues.append(f"Only {scenario_count} scenario-based questions (minimum 4 required)")

    easy = sum(1 for q in questions if q.difficulty == "easy")
    medium = sum(1 for q in questions if q.difficulty == "medium")
    hard = sum(1 for q in questions if q.difficulty == "hard")
    if not (5 <= easy <= 7):
        issues.append(f"Easy count {easy} outside range 5-7")
    if not (5 <= medium <= 7):
        issues.append(f"Medium count {medium} outside range 5-7")
    if not (2 <= hard <= 4):
        issues.append(f"Hard count {hard} outside range 2-4")

    for q in questions:
        if q.question_type == "multi_select":
            if len(q.correct_answers) != 2:
                issues.append(f"multi_select question {q.id} has {len(q.correct_answers)} correct answers (expected 2)")
            if not q.text.endswith("(Select 2)"):
                issues.append(f"multi_select question {q.id} text does not end with '(Select 2)'")

    return issues


# ---------------------------------------------------------------------------
# Fallback generator (demo safety net — only used when both LLM attempts fail)
# ---------------------------------------------------------------------------


def _build_fallback_questions(cert_id: str, domain_weights: dict[str, float]) -> list[AssessmentQuestion]:
    """Generate exactly 15 deterministic placeholder questions so the demo never breaks."""
    domains = list(domain_weights.keys()) if domain_weights else ["General"]
    difficulty_cycle = ["easy", "easy", "easy", "easy", "easy", "medium", "medium", "medium", "medium", "medium", "medium", "medium", "hard", "hard", "hard"]

    questions: list[AssessmentQuestion] = []
    for i in range(15):
        domain = domains[i % len(domains)]
        weight = domain_weights.get(domain, 1.0 / len(domains))
        questions.append(
            AssessmentQuestion(
                id=f"fallback-q{i + 1}",
                text=f"[Placeholder] Question {i + 1} about {domain} for {cert_id}.",
                question_type="multiple_choice",
                options=[
                    f"Option A for {domain}",
                    f"Option B for {domain}",
                    f"Option C for {domain}",
                    f"Option D for {domain}",
                ],
                correct_answers=[f"Option A for {domain}"],
                domain=domain,
                exam_weight_pct=round(weight, 4),
                explanation=f"This is a placeholder explanation for {domain}.",
                difficulty=difficulty_cycle[i],  # type: ignore[arg-type]
                bloom_level="Understand",
                is_scenario_based=False,
                scenario_context=None,
                grounding_reference=None,
            )
        )
    return questions


# ---------------------------------------------------------------------------
# Parser — handles both bare array and envelope formats
# ---------------------------------------------------------------------------

_question_list_adapter: TypeAdapter[list[AssessmentQuestion]] = TypeAdapter(list[AssessmentQuestion])


def _parse_questions(raw: str) -> tuple[list[AssessmentQuestion], str | None]:
    """Parse raw LLM output into a validated list of AssessmentQuestion.

    Accepts both:
    - Bare JSON array: [...] → returns (questions, None)
    - Envelope: {"questions": [...], "reasoning_distribution": "..."} → returns (questions, reasoning)

    Strips markdown fences if present before parsing.

    Raises:
        ValueError: if JSON parsing or Pydantic validation fails.
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(ln for ln in lines if not ln.startswith("```")).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON decode failed: {exc}") from exc

    reasoning_distribution: str | None = None

    # Handle envelope format
    if isinstance(data, dict):
        reasoning_distribution = data.get("reasoning_distribution")
        raw_questions = data.get("questions")
        if not isinstance(raw_questions, list):
            raise ValueError("Envelope JSON missing 'questions' array")
        data = raw_questions

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array or envelope, got {type(data).__name__}")

    try:
        questions = _question_list_adapter.validate_python(data)
    except (ValidationError, TypeError) as exc:
        raise ValueError(f"Schema validation failed: {exc}") from exc

    if len(questions) != 15:
        raise ValueError(f"Expected 15 questions, got {len(questions)}")

    return questions, reasoning_distribution


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_assessment_questions(
    agent: Agent,
    cert_id: str,
    learner_id: str = "UNKNOWN",
) -> tuple[list[AssessmentQuestion], str | None]:
    """Generate 15 assessment questions via LLM with one retry on parse failure.

    Args:
        agent: A configured MAF Agent with LLM client and tools.
        cert_id: The certification identifier (e.g. "AZ-900").
        learner_id: The learner's ID for history lookup (default "UNKNOWN").

    Returns:
        Tuple of (list[AssessmentQuestion], reasoning_distribution | None).
        Always returns exactly 15 questions (fallback if both LLM attempts fail).
    """
    difficulty = _CERT_DIFFICULTY.get(cert_id, _DEFAULT_DIFFICULTY)

    user_message = (
        f"LEARNER_ID: {learner_id}\n"
        f"CERT_ID: {cert_id}\n"
        f"Difficulty level: {difficulty}\n\n"
        "Follow the 5-step instructions in your system prompt. "
        "Start by calling get_learner_performance, then call search_knowledge_base to get "
        "the official exam skill areas for this cert — those names are the only valid domain values. "
        "Generate exactly 15 questions. Return ONLY the JSON envelope as instructed."
    )

    # Attempt 1
    try:
        raw_1 = await agent.run(messages=user_message)  # type: ignore[arg-type]
        questions, reasoning = _parse_questions(str(raw_1) if raw_1 else "")

        # Run structural critic check
        issues = _check_batch(questions)
        if issues:
            logger.warning(
                "[assessment] Structural issues in generated batch for cert=%s: %s",
                cert_id,
                issues,
            )
            # Soft gate — submit anyway after logging
        return questions, reasoning
    except (ValueError, Exception) as exc_1:
        logger.warning(
            "[assessment] First parse attempt failed for cert=%s: %s — retrying",
            cert_id,
            exc_1,
        )

    # Attempt 2 — corrective prompt
    try:
        raw_2 = await agent.run(messages=_CORRECTIVE_PROMPT)  # type: ignore[arg-type]
        questions, reasoning = _parse_questions(str(raw_2) if raw_2 else "")
        return questions, reasoning
    except (ValueError, Exception) as exc_2:
        logger.error(
            "[assessment] Second parse attempt also failed for cert=%s: %s — using fallback questions",
            cert_id,
            exc_2,
        )
        return _build_fallback_questions(cert_id, {}), None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_assessment_agent(
    client: object,
    learner_perf_tool: object = None,
    *mcp_functions: object,
) -> Agent:
    """Return a configured AssessmentAgent for grounded question generation.

    Args:
        client: An initialised MAF-compatible chat client.
        learner_perf_tool: get_learner_performance @tool (defaults to module-level import).
        *mcp_functions: MCP tool functions from connected MCPStreamableHTTPTool instances
                        (KB and/or MS Learn). Passed in directly — no HTTP fallback.

    Returns:
        An Agent configured with the grounded system prompt and all provided tools.
    """
    from agents.tools.assessment_tools import get_learner_performance  # noqa: PLC0415

    perf_tool = learner_perf_tool if learner_perf_tool is not None else get_learner_performance

    tools = [perf_tool, *mcp_functions]

    return Agent(
        client=client,
        name="AssessmentAgent",
        instructions=_SYSTEM_PROMPT,
        tools=tools,
    )
