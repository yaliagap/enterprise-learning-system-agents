"""Assessment Agent — question generation via LLM.

generate_assessment_questions() generates exactly 15 questions for a given
certification, validates against the AssessmentQuestion Pydantic schema, and
provides one retry with corrective instruction on parse failure.
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
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a Microsoft Azure certification exam question generator.

    When given a certification ID and domain weights, generate exactly 15 questions
    that mirror the real Azure certification exam format.
    Use ONLY two question types: multiple_choice and multi_select.

    === DIFFICULTY DISTRIBUTION (strictly enforced) ===
    - easy: 5 questions (33%)
    - medium: 7 questions (47%)
    - hard: 3 questions (20%)

    === SCENARIO DISTRIBUTION ===
    - At least 4 of the 15 questions must be scenario-based (is_scenario_based: true).
    - Scenario questions describe a realistic business or technical situation (Contoso, Fabrikam, etc.)
      and ask what the learner should do or recommend.
    - For scenario questions, put the scenario setup in "scenario_context" and the actual question in "text".
    - For non-scenario questions, leave "scenario_context" as null.

    === BLOOM'S TAXONOMY DISTRIBUTION ===
    - Remember / Understand: 4 questions (conceptual recall)
    - Apply / Analyze: 8 questions (practical application and reasoning)
    - Evaluate / Create: 3 questions (design decisions, architectural choices)

    === OUTPUT FORMAT ===
    Return ONLY a valid JSON array — no prose, no markdown fences, no extra keys.
    Each element must be a JSON object with EXACTLY these fields:
        {
          "id": "<unique string, e.g. q1>",
          "text": "<the question itself — NOT the scenario>",
          "question_type": "<multiple_choice | multi_select>",
          "options": ["<option A>", "<option B>", "<option C>", "<option D>"],
          "correct_answers": ["<correct option text>"],
          "domain": "<domain name>",
          "exam_weight_pct": <float between 0 and 1>,
          "explanation": "<2-4 sentence explanation of why the correct answer is right>",
          "difficulty": "<easy | medium | hard>",
          "bloom_level": "<Remember | Understand | Apply | Analyze | Evaluate | Create>",
          "is_scenario_based": <true | false>,
          "scenario_context": "<scenario setup paragraph, or null if not scenario-based>"
        }

    === QUESTION TYPE RULES ===
    - "multiple_choice": exactly 1 correct_answers entry, exactly 4 options.
    - "multi_select": ALWAYS exactly 2 correct_answers entries, always 4 options (never 3, never 5, never 6).
    - For multi_select questions, the "text" MUST end with "(Select 2)".
    - NEVER generate a multi_select where the number of correct_answers equals the total number of options — that is trivially correct and forbidden.

    === COVERAGE RULES ===
    - Distribute questions proportionally across domains according to their weights.
    - Mix conceptual, applied, and scenario reasoning questions.
    - Never return fewer or more than 15 questions.
    - Difficulty distribution must match exactly: 5 easy, 7 medium, 3 hard.
""")

# ---------------------------------------------------------------------------
# Corrective retry prompt
# ---------------------------------------------------------------------------

_CORRECTIVE_PROMPT = textwrap.dedent("""\
    Your previous response could not be parsed as a valid JSON array of assessment questions.

    Please re-generate exactly 15 questions in STRICT JSON format — a bare JSON array
    starting with [ and ending with ].  No markdown, no explanations outside the JSON.
""")

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
            )
        )
    return questions


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_question_list_adapter: TypeAdapter[list[AssessmentQuestion]] = TypeAdapter(list[AssessmentQuestion])


def _parse_questions(raw: str) -> list[AssessmentQuestion]:
    """Parse raw LLM output into a validated list of AssessmentQuestion.

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

    try:
        questions = _question_list_adapter.validate_python(data)
    except (ValidationError, TypeError) as exc:
        raise ValueError(f"Schema validation failed: {exc}") from exc

    if len(questions) != 15:
        raise ValueError(f"Expected 15 questions, got {len(questions)}")

    return questions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_assessment_questions(
    agent: Agent,
    cert_id: str,
    domain_weights: dict[str, float],
) -> list[AssessmentQuestion]:
    """Generate 15 assessment questions via LLM with one retry on parse failure.

    Args:
        agent: A configured MAF Agent with LLM client.
        cert_id: The certification identifier (e.g. "AZ-900").
        domain_weights: Mapping of domain_name → exam_weight (float 0–1).

    Returns:
        A list of exactly 15 AssessmentQuestion objects.

    Raises:
        ValueError: If both the initial attempt and the retry fail to produce valid JSON.
    """
    difficulty = _CERT_DIFFICULTY.get(cert_id, _DEFAULT_DIFFICULTY)
    domain_summary = ", ".join(
        f"{d} ({w:.0%})" for d, w in sorted(domain_weights.items(), key=lambda x: -x[1])
    )

    user_message = (
        f"Certification: {cert_id}\n"
        f"Difficulty level: {difficulty}\n"
        f"Domain weights: {domain_summary}\n\n"
        "Generate exactly 15 questions. Return ONLY the JSON array."
    )

    # Attempt 1
    try:
        raw_1 = await agent.run(messages=user_message)  # type: ignore[arg-type]
        return _parse_questions(str(raw_1) if raw_1 else "")
    except (ValueError, Exception) as exc_1:
        logger.warning(
            "[assessment] First parse attempt failed for cert=%s: %s — retrying",
            cert_id,
            exc_1,
        )

    # Attempt 2 — corrective prompt
    try:
        raw_2 = await agent.run(messages=_CORRECTIVE_PROMPT)  # type: ignore[arg-type]
        return _parse_questions(str(raw_2) if raw_2 else "")
    except (ValueError, Exception) as exc_2:
        logger.error(
            "[assessment] Second parse attempt also failed for cert=%s: %s — using fallback questions",
            cert_id,
            exc_2,
        )
        return _build_fallback_questions(cert_id, domain_weights)


# ---------------------------------------------------------------------------
# Legacy factory (kept for backward compatibility with dispatcher)
# ---------------------------------------------------------------------------


def create_assessment_agent(client: object) -> Agent:
    """Return a configured AssessmentAgent for question generation.

    Args:
        client: An initialised MAF-compatible chat client.

    Returns:
        A plain Agent with the question-generation system prompt and no tools.
        Question generation is done via generate_assessment_questions(), not agent.run() alone.
    """
    return Agent(
        client=client,
        name="AssessmentAgent",
        instructions=_SYSTEM_PROMPT,
        tools=[],
    )
