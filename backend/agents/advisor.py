"""Certification Advisor Agent — structured JSON output.

generate_advice() accepts full per-question data, team benchmark, and KB grounding,
emits a Pydantic-validated AdvisorResult JSON, and provides one corrective retry
plus a deterministic fallback so the frontend always receives a valid object.
"""
from __future__ import annotations

import json
import logging
import re
import textwrap
from typing import Any

from agent_framework import Agent
from pydantic import ValidationError

from agents.tools.advisor_tools import get_team_benchmark, percentile_rank
from workflow.state import (
    AdvisorDomainAnalysis,
    AdvisorPerformanceSnapshot,
    AdvisorRecommendation,
    AdvisorResult,
    AdvisorRetryComparison,
    AdvisorReviewArea,
    AdvisorScoreSummary,
    AdvisorStrongArea,
    AdvisorTeamBenchmark,
    AssessmentQuestion,
    AssessmentResult,
    QuestionResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cert metadata helpers
# ---------------------------------------------------------------------------

_CERT_NAMES: dict[str, str] = {
    "AZ-900": "Microsoft Azure Fundamentals",
    "AZ-104": "Microsoft Azure Administrator",
    "AZ-204": "Microsoft Azure Developer Associate",
    "AZ-305": "Microsoft Azure Solutions Architect Expert",
    "AZ-400": "Microsoft DevOps Engineer Expert",
    "AZ-500": "Microsoft Azure Security Engineer Associate",
    "AI-900": "Microsoft Azure AI Fundamentals",
    "AI-102": "Microsoft Azure AI Engineer Associate",
    "AI-103": "Microsoft Azure AI Apps and Agents Developer Associate",
    "SC-900": "Microsoft Security, Compliance, and Identity Fundamentals",
    "DP-900": "Microsoft Azure Data Fundamentals",
    "DP-203": "Microsoft Azure Data Engineer Associate",
}

_NEXT_CERT: dict[str, str] = {
    "AZ-900": "AZ-104 (Azure Administrator)",
    "AZ-104": "AZ-305 (Azure Solutions Architect Expert)",
    "AZ-204": "AZ-400 (DevOps Engineer Expert)",
    "AZ-305": "AZ-400 (DevOps Engineer Expert) or a specialty cert",
    "AZ-400": "AZ-305 (Azure Solutions Architect Expert)",
    "AI-900": "AI-102 (Azure AI Engineer Associate) or AI-103 (Azure AI Apps and Agents Developer Associate)",
    "AI-102": "AI-103 (Azure AI Apps and Agents Developer Associate)",
    "AI-103": "AZ-308 (Azure AI Infrastructure Solutions) or AI-300 (ML Operations Engineer)",
    "SC-900": "SC-500 (Cloud and AI Security Engineer Associate)",
    "AZ-500": "SC-500 (Cloud and AI Security Engineer Associate)",
    "DP-900": "DP-203 (Azure Data Engineer Associate)",
    "DP-203": "AZ-305 (Azure Solutions Architect Expert)",
}

_CERT_URL_TEMPLATE = "https://learn.microsoft.com/en-us/credentials/certifications/{cert_id}/"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_ADVISOR_RESULT_SCHEMA = """{
  "scenario": "<passed | max_retries>",
  "cert_id": "<string>",
  "cert_name": "<string>",
  "official_cert_url": "<string>",
  "next_cert_suggestion": "<string>",
  "score_summary": {
    "score": <float 0-100>,
    "passed": <bool>,
    "passing_score": <float 0-100>,
    "attempt": <int >= 1>
  },
  "performance_snapshot": {
    "total_questions": <int>,
    "correct": <int>,
    "conceptual_correct_pct": <float 0-100>,
    "application_correct_pct": <float 0-100>,
    "scenario_correct_pct": <float 0-100>,
    "has_scenario_gap": <bool>,
    "bloom_level_gap": "<conceptual_gap | application_gap | scenario_gap | bloom_gap | none>"
  },
  "team_benchmark": {
    "team_avg_score": <float 0-100>,
    "team_percentile": <int 0-100>,
    "comparison": "<above | below | on_par>",
    "team_signal": "<individual_gap | shared_team_gap | on_par | ahead>",
    "sample_size": <int>,
    "has_data": <bool>
  },
  "domain_analysis": [
    {
      "domain_name": "<string>",
      "learner_score": <float 0-100>,
      "team_avg": <float 0-100 | null>,
      "delta_vs_team": <float | null>,
      "pattern_type": "<conceptual_gap | application_gap | scenario_gap | bloom_gap | none>",
      "team_signal": "<individual_gap | shared_team_gap | on_par | ahead>"
    }
  ],
  "strong_areas": [
    {
      "domain_name": "<string>",
      "learner_score": <float 0-100>,
      "note": "<string>"
    }
  ],
  "areas_to_review": [
    {
      "domain_name": "<string>",
      "learner_score": <float 0-100>,
      "pattern_type": "<conceptual_gap | application_gap | scenario_gap | bloom_gap | none>",
      "note": "<string>",
      "resource_hint": "<string from KB or empty>"
    }
  ],
  "retry_comparison": null,
  "recommendations": [
    {
      "order": <int >= 1>,
      "title": "<string>",
      "detail": "<string>",
      "resource_hint": "<string>"
    }
  ],
  "closing_note": "<string — italic muted text, PII-free>"
}"""

_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a Microsoft Azure certification advisor and learning-analytics specialist.
    You have a learner's complete assessment data and must produce a STRUCTURED JSON
    analysis following the exact schema below.

    === YOUR TOOLS ===
    - get_team_benchmark(cert_id): returns team_avg_score, score_distribution,
      team_domain_avgs, and sample_size for the given certification.
    - search_knowledge_base(query): qualitative team insights — instructor feedback,
      common stumbling blocks, recommended resources. Query per weak domain.

    === ANALYSIS RULES ===
    Bloom cluster (from per-question bloom_level):
    - Remember/Understand errors → conceptual_gap
    - Apply/Analyze/Evaluate/Create errors → application_gap
    - If ≥60% of errors in a domain are at Remember/Understand → pattern_type = "conceptual_gap"
    - If ≥60% are at Apply/Analyze/Evaluate/Create → pattern_type = "application_gap"
    - Disproportionate scenario-question misses (scenario_correct_pct < overall by ≥15 pts) → has_scenario_gap=true, bloom_level_gap="scenario_gap"
    Strong areas: domain score ≥ 85. Areas to review: domain score < 70 OR in weak_areas list.
    team_signal per domain: learner within 5pts of team_avg → on_par; >5 above → ahead;
      >5 below AND domain team_avg also low (<65) → shared_team_gap; else individual_gap.
    comparison field: learner_score > team_avg_score + 5 → "above"; < team_avg_score - 5 → "below"; else → "on_par".

    === SCENARIO TONE ===
    - passed: celebratory, forward-looking. closing_note MUST acknowledge the achievement
      and point toward next steps (exam booking, next cert path). Set retry_comparison=null.
    - max_retries: constructive and actionable. POPULATE retry_comparison from the
      first vs last attempt data provided. closing_note MUST acknowledge effort and
      identify improvement paths. Do NOT use discouraging language.

    === PII (NON-NEGOTIABLE) ===
    Never include any person's name, email address, employee ID, learner ID, phone
    number, or any other identifying information in any field of the output.
    Use only cert_id and domain names to reference specific content.

    === OUTPUT FORMAT ===
    Return ONLY a valid JSON object matching this schema. No markdown fences, no prose:
""") + _ADVISOR_RESULT_SCHEMA


# ---------------------------------------------------------------------------
# PII scrubbing
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
_EMP_RE = re.compile(r"\b(?:EMP|emp|learner[-_]?id|LEARNER)[-_]?\d+\b", re.IGNORECASE)


def _scrub_pii(text: str) -> str:
    """Regex-redact emails and EMP-/learner-id-like tokens from free text."""
    text = _EMAIL_RE.sub("[REDACTED]", text)
    text = _EMP_RE.sub("[REDACTED]", text)
    return text


def _scrub_result(result: AdvisorResult) -> AdvisorResult:
    """Apply PII scrubbing to all free-text fields in an AdvisorResult."""
    result.closing_note = _scrub_pii(result.closing_note)
    for area in result.areas_to_review:
        area.note = _scrub_pii(area.note)
        area.resource_hint = _scrub_pii(area.resource_hint)
    for rec in result.recommendations:
        rec.detail = _scrub_pii(rec.detail)
        rec.resource_hint = _scrub_pii(rec.resource_hint)
    for strong in result.strong_areas:
        strong.note = _scrub_pii(strong.note)
    if result.retry_comparison:
        result.retry_comparison.summary = _scrub_pii(result.retry_comparison.summary)
    return result


# ---------------------------------------------------------------------------
# Pre-computation helpers (deterministic, executor-side)
# ---------------------------------------------------------------------------


def _compute_performance_snapshot(
    questions: list[AssessmentQuestion],
    per_question_results: list[QuestionResult],
) -> dict[str, Any]:
    """Compute performance snapshot percentages from per-question data."""
    q_map = {q.id: q for q in questions}
    total = len(per_question_results)
    correct = sum(1 for r in per_question_results if r.is_correct)

    conceptual_total = conceptual_correct = 0
    application_total = application_correct = 0
    scenario_total = scenario_correct = 0

    for r in per_question_results:
        q = q_map.get(r.question_id)
        bloom = getattr(q, "bloom_level", "Understand") if q else "Understand"
        is_scenario = getattr(q, "is_scenario_based", False) if q else False

        if bloom in ("Remember", "Understand"):
            conceptual_total += 1
            if r.is_correct:
                conceptual_correct += 1
        else:
            application_total += 1
            if r.is_correct:
                application_correct += 1

        if is_scenario:
            scenario_total += 1
            if r.is_correct:
                scenario_correct += 1

    overall_pct = (correct / total * 100) if total > 0 else 0.0
    conceptual_pct = (conceptual_correct / conceptual_total * 100) if conceptual_total > 0 else 0.0
    application_pct = (application_correct / application_total * 100) if application_total > 0 else 0.0
    scenario_pct = (scenario_correct / scenario_total * 100) if scenario_total > 0 else 0.0

    has_scenario_gap = scenario_total > 0 and (overall_pct - scenario_pct) >= 15.0

    # Bloom level gap
    bloom_level_gap = "none"
    if has_scenario_gap:
        bloom_level_gap = "scenario_gap"
    elif conceptual_pct < application_pct - 10:
        bloom_level_gap = "conceptual_gap"
    elif application_pct < conceptual_pct - 10:
        bloom_level_gap = "application_gap"

    return {
        "total_questions": total,
        "correct": correct,
        "conceptual_correct_pct": round(conceptual_pct, 1),
        "application_correct_pct": round(application_pct, 1),
        "scenario_correct_pct": round(scenario_pct, 1),
        "has_scenario_gap": has_scenario_gap,
        "bloom_level_gap": bloom_level_gap,
    }


def _compute_domain_table(
    questions: list[AssessmentQuestion],
    per_question_results: list[QuestionResult],
) -> dict[str, dict]:
    """Compute per-domain accuracy and bloom distribution."""
    q_map = {q.id: q for q in questions}
    domain_data: dict[str, dict] = {}

    for r in per_question_results:
        q = q_map.get(r.question_id)
        domain = (q.domain if q else "General")
        bloom = (q.bloom_level if q else "Understand")
        is_scenario = (q.is_scenario_based if q else False)

        if domain not in domain_data:
            domain_data[domain] = {
                "total": 0,
                "correct": 0,
                "conceptual_errors": 0,
                "application_errors": 0,
                "scenario_total": 0,
                "scenario_correct": 0,
            }

        d = domain_data[domain]
        d["total"] += 1
        if r.is_correct:
            d["correct"] += 1
        else:
            if bloom in ("Remember", "Understand"):
                d["conceptual_errors"] += 1
            else:
                d["application_errors"] += 1

        if is_scenario:
            d["scenario_total"] += 1
            if r.is_correct:
                d["scenario_correct"] += 1

    result = {}
    for domain, d in domain_data.items():
        accuracy = (d["correct"] / d["total"] * 100) if d["total"] > 0 else 0.0
        total_errors = d["conceptual_errors"] + d["application_errors"]
        if total_errors >= 1:
            if d["conceptual_errors"] / total_errors >= 0.6:
                pattern = "conceptual_gap"
            elif d["application_errors"] / total_errors >= 0.6:
                pattern = "bloom_gap"
            else:
                pattern = "none"
        else:
            pattern = "none"

        scenario_errors = d["scenario_total"] - d["scenario_correct"]
        has_scenario_gap = d["scenario_total"] >= 2 and scenario_errors / d["scenario_total"] >= 0.5

        result[domain] = {
            "accuracy": round(accuracy, 1),
            "pattern": pattern,
            "has_scenario_gap": has_scenario_gap,
        }

    return result


def _build_per_question_compact(
    questions: list[AssessmentQuestion],
    per_question_results: list[QuestionResult],
) -> str:
    """Build compact per-question table for LLM context."""
    q_map = {q.id: q for q in questions}
    lines = ["domain|bloom|difficulty|is_scenario|correct"]
    for r in per_question_results:
        q = q_map.get(r.question_id)
        domain = (q.domain if q else "Unknown")[:40]
        bloom = (q.bloom_level if q else "Understand")
        difficulty = (q.difficulty if q else "medium")
        is_scenario = "yes" if (q and q.is_scenario_based) else "no"
        correct = "yes" if r.is_correct else "no"
        lines.append(f"{domain}|{bloom}|{difficulty}|{is_scenario}|{correct}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON parser
# ---------------------------------------------------------------------------


def _parse_advisor_result(raw: str) -> AdvisorResult:
    """Parse and validate raw LLM string into AdvisorResult. Raises ValueError on failure."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(ln for ln in lines if not ln.startswith("```")).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON decode failed: {exc}") from exc
    try:
        return AdvisorResult.model_validate(data)
    except (ValidationError, TypeError) as exc:
        raise ValueError(f"Schema validation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Fallback (deterministic)
# ---------------------------------------------------------------------------


def _build_fallback_advisor_result(
    cert_id: str,
    scenario: str,
    score: float,
    passed: bool,
    passing_score: float,
    attempt: int,
    domain_table: dict[str, dict],
    perf_snapshot: dict,
    team_percentile: int,
    team_avg_score: float,
    sample_size: int,
    has_benchmark: bool,
    assessment_results: list[AssessmentResult],
    bench_domain_avgs: dict[str, float] | None = None,
) -> AdvisorResult:
    """Construct a minimal valid AdvisorResult deterministically from raw data."""
    cert_name = _CERT_NAMES.get(cert_id, f"Microsoft Azure {cert_id}")
    cert_url = _CERT_URL_TEMPLATE.format(cert_id=cert_id.lower())
    next_cert = _NEXT_CERT.get(cert_id, "a higher-level Azure specialty certification")

    comparison = "on_par"
    if score > team_avg_score + 5:
        comparison = "above"
    elif score < team_avg_score - 5:
        comparison = "below"

    team_signal_overall: str = "on_par"
    if score > team_avg_score + 5:
        team_signal_overall = "ahead"
    elif score < team_avg_score - 5:
        team_signal_overall = "individual_gap"

    strong_areas = []
    areas_to_review = []
    domain_analysis = []

    _domain_avgs = bench_domain_avgs or {}
    for domain, data in domain_table.items():
        accuracy = data["accuracy"]
        pattern = data.get("pattern", "conceptual_gap")
        team_domain_avg = _domain_avgs.get(domain)
        if team_domain_avg is not None:
            domain_team_signal: str = "shared_team_gap" if team_domain_avg < 60.0 else "individual_gap"
        else:
            domain_team_signal = "on_par"
        domain_analysis.append(
            AdvisorDomainAnalysis(
                domain_name=domain,
                learner_score=accuracy,
                team_avg=team_domain_avg,
                delta_vs_team=round(accuracy - team_domain_avg, 1) if team_domain_avg is not None else None,
                pattern_type=pattern,  # type: ignore[arg-type]
                team_signal=domain_team_signal,  # type: ignore[arg-type]
            )
        )
        if accuracy >= 85.0:
            strong_areas.append(AdvisorStrongArea(domain_name=domain, learner_score=accuracy))
        elif accuracy < 70.0:
            areas_to_review.append(
                AdvisorReviewArea(
                    domain_name=domain,
                    learner_score=accuracy,
                    pattern_type=pattern,  # type: ignore[arg-type]
                    note=f"Score {accuracy:.0f}% is below the 70% threshold.",
                    resource_hint="",
                )
            )

    recs = []
    for i, area in enumerate(areas_to_review[:3], start=1):
        recs.append(
            AdvisorRecommendation(
                order=i,
                title=f"Strengthen {area.domain_name}",
                detail=f"Focus on {area.domain_name} — current score {area.learner_score:.0f}%.",
                resource_hint="See Microsoft Learn for the relevant certification module.",
            )
        )
    if not recs:
        recs.append(
            AdvisorRecommendation(
                order=1,
                title="Continue building expertise",
                detail="Explore advanced scenarios and hands-on labs to deepen expertise.",
                resource_hint="Microsoft Learn practice assessments are available for this certification.",
            )
        )

    retry_comparison = None
    if scenario == "max_retries" and len(assessment_results) >= 2:
        first = assessment_results[0]
        last = assessment_results[-1]
        improved = [d for d in first.domain_scores if last.domain_scores.get(d, 0) > first.domain_scores[d]]
        regressed = [d for d in first.domain_scores if last.domain_scores.get(d, 0) < first.domain_scores[d]]
        retry_comparison = AdvisorRetryComparison(
            first_attempt_score=first.score,
            last_attempt_score=last.score,
            delta=round(last.score - first.score, 1),
            improved_domains=improved,
            regressed_domains=regressed,
            summary=f"Score moved from {first.score:.1f}% to {last.score:.1f}% across attempts.",
        )

    if scenario == "passed":
        closing_note = (
            f"Congratulations on passing {cert_id}! "
            f"Your score of {score:.1f}% qualifies you to pursue the official exam. "
            f"Recommended next step: {next_cert}. "
            f"Visit the official certification page to schedule your exam."
        )
    else:
        closing_note = (
            f"You have completed all available attempts for {cert_id}. "
            f"Your final score of {score:.1f}% reflects real progress. "
            f"Review the areas highlighted above before your next attempt. "
            f"You have the skills to succeed with focused preparation."
        )

    return AdvisorResult(
        scenario=scenario,  # type: ignore[arg-type]
        cert_id=cert_id,
        cert_name=cert_name,
        official_cert_url=cert_url,
        next_cert_suggestion=next_cert,
        score_summary=AdvisorScoreSummary(
            score=score,
            passed=passed,
            passing_score=passing_score,
            attempt=attempt,
        ),
        performance_snapshot=AdvisorPerformanceSnapshot(**perf_snapshot),
        team_benchmark=AdvisorTeamBenchmark(
            team_avg_score=team_avg_score,
            team_percentile=team_percentile,
            comparison=comparison,
            team_signal=team_signal_overall,  # type: ignore[arg-type]
            sample_size=sample_size,
            has_data=has_benchmark,
        ),
        domain_analysis=domain_analysis,
        strong_areas=strong_areas,
        areas_to_review=areas_to_review,
        retry_comparison=retry_comparison,
        recommendations=recs,
        closing_note=closing_note,
    )


# ---------------------------------------------------------------------------
# Corrective retry prompt
# ---------------------------------------------------------------------------


def _make_corrective_prompt(cert_id: str, error: str) -> str:
    return textwrap.dedent(f"""\
        Your previous response failed validation with this error:
        {error}

        CERT_ID: {cert_id}

        Re-generate the AdvisorResult JSON for this certification. Return ONLY
        a valid JSON object matching the schema in your system prompt.
        No markdown fences, no prose, no extra keys.
    """)


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def create_advisor_agent(client: Any, tools: list | None = None) -> Agent:
    """Return a configured Advisor Agent with the structured JSON system prompt."""
    return Agent(
        client=client,
        name="CertificationAdvisorAgent",
        instructions=_SYSTEM_PROMPT,
        tools=tools or [get_team_benchmark],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_advice(
    cert_id: str,
    learner_id: str,
    workflow_status: str,
    assessment_questions: list[AssessmentQuestion],
    assessment_answers: Any,
    assessment_results: list[AssessmentResult],
    team_benchmark_tool: Any = None,
    kb_mcp_functions: list | None = None,
    middleware: list | None = None,
    client: Any = None,
) -> tuple[AdvisorResult, str]:
    """Generate structured certification advice via LLM with deterministic fallback.

    Args:
        cert_id: The certification identifier (e.g. "AI-900").
        learner_id: The learner's ID (used only for logging, never in output).
        workflow_status: Current workflow status ("passed" or "max_retries_reached").
        assessment_questions: Full questions list (with bloom_level, difficulty, etc.).
        assessment_answers: AssessmentAnswers object (may be None).
        assessment_results: All attempt results (list[AssessmentResult]).
        team_benchmark_tool: The get_team_benchmark @tool callable.
        kb_mcp_functions: KB MCP tool functions list.
        middleware: Optional middleware list (e.g. KB capture).
        client: MAF-compatible chat client.

    Returns:
        Tuple of (AdvisorResult, raw_json_string).
        Always returns a valid AdvisorResult (fallback on both-attempt failure).
    """
    latest = assessment_results[-1] if assessment_results else None
    score = latest.score if latest else 0.0
    passed = latest.passed if latest else False
    passing_score = latest.passing_score if latest else 70.0
    attempt = latest.attempt if latest else 1
    weak_areas = latest.weak_areas if latest else []
    per_question_results = latest.per_question_results if latest else []
    domain_scores = latest.domain_scores if latest else {}

    scenario = "passed" if workflow_status == "passed" else "max_retries"

    cert_name = _CERT_NAMES.get(cert_id, f"Microsoft Azure {cert_id}")
    cert_url = _CERT_URL_TEMPLATE.format(cert_id=cert_id.lower())
    next_cert = _NEXT_CERT.get(cert_id, "a higher-level Azure specialty certification")

    # Precompute deterministic inputs
    perf_snapshot = _compute_performance_snapshot(assessment_questions, per_question_results)
    domain_table = _compute_domain_table(assessment_questions, per_question_results)
    per_q_compact = _build_per_question_compact(assessment_questions, per_question_results)

    # Get team benchmark deterministically (executor-side, not LLM-side)
    try:
        from agents.tools.advisor_tools import _BENCHMARKS  # noqa: PLC0415
        raw_bench = _BENCHMARKS.get(cert_id.upper(), {})
        bench_distribution: list[float] = raw_bench.get("score_distribution", [])
        bench_avg: float = raw_bench.get("team_avg_score", 70.0)
        bench_sample: int = raw_bench.get("sample_size", 0)
        bench_has_data: bool = bool(raw_bench)
        bench_domain_avgs: dict[str, float] = raw_bench.get("team_domain_avgs", {})
    except Exception:  # noqa: BLE001
        bench_distribution = []
        bench_avg = 70.0
        bench_sample = 0
        bench_domain_avgs = {}
        bench_has_data = False

    team_percentile = percentile_rank(score, bench_distribution)

    # Domain scores table string for prompt
    domain_scores_lines = "\n".join(
        f"  {domain}: {acc:.1f}%"
        for domain, acc in (domain_scores or {}).items()
    ) or "  (no domain scores available)"

    # Retry history for max_retries scenario
    retry_block = ""
    if scenario == "max_retries" and len(assessment_results) >= 2:
        first = assessment_results[0]
        last = assessment_results[-1]
        retry_block = textwrap.dedent(f"""\
            RETRY HISTORY:
            Attempt 1 score: {first.score:.1f}%
            Attempt {last.attempt} score: {last.score:.1f}%
            Delta: {last.score - first.score:+.1f}%
            Attempt 1 domain scores: {json.dumps(first.domain_scores)}
            Attempt {last.attempt} domain scores: {json.dumps(last.domain_scores)}
        """)

    user_message = textwrap.dedent(f"""\
        CERT_ID: {cert_id}
        CERT_NAME: {cert_name}
        CERT_URL: {cert_url}
        NEXT_CERT_SUGGESTION: {next_cert}
        SCENARIO: {scenario}

        SCORE SUMMARY:
        Score: {score:.1f}%
        Passed: {passed}
        Passing score: {passing_score:.1f}%
        Attempt: {attempt}

        PRECOMPUTED PERFORMANCE SNAPSHOT:
        Total questions: {perf_snapshot['total_questions']}
        Correct: {perf_snapshot['correct']}
        Conceptual correct %: {perf_snapshot['conceptual_correct_pct']}
        Application correct %: {perf_snapshot['application_correct_pct']}
        Scenario correct %: {perf_snapshot['scenario_correct_pct']}
        Has scenario gap: {perf_snapshot['has_scenario_gap']}
        Bloom level gap: {perf_snapshot['bloom_level_gap']}

        PRECOMPUTED TEAM BENCHMARK:
        Team avg score: {bench_avg:.1f}%
        Team percentile: {team_percentile} (learner is at the {team_percentile}th percentile)
        Sample size: {bench_sample}
        Has data: {bench_has_data}

        DOMAIN SCORES:
{domain_scores_lines}

        WEAK AREAS: {', '.join(weak_areas) if weak_areas else 'none'}

        PER-QUESTION BREAKDOWN:
{per_q_compact}

        {retry_block}

        Now call get_team_benchmark(cert_id="{cert_id}") to confirm domain averages.
        Then call search_knowledge_base for each weak domain to enrich resource_hint fields.
        Return ONLY the JSON object per your system prompt schema.
    """)

    tool_list = [team_benchmark_tool or get_team_benchmark]
    if kb_mcp_functions:
        tool_list = tool_list + list(kb_mcp_functions)

    agent = create_advisor_agent(client=client, tools=tool_list)
    _mw = middleware or []

    raw = ""
    exc_1_str = ""

    # Attempt 1
    try:
        raw_result = await agent.run(messages=user_message, middleware=_mw)  # type: ignore[arg-type]
        raw = str(raw_result) if raw_result else ""
        result = _parse_advisor_result(raw)
        result = _scrub_result(result)
        logger.info("[advisor] Parsed AdvisorResult successfully for cert=%s", cert_id)
        return result, raw
    except Exception as exc_1:  # noqa: BLE001
        exc_1_str = str(exc_1)
        logger.warning("[advisor] First attempt failed for cert=%s: %s — retrying", cert_id, exc_1)

    # Attempt 2 — corrective prompt
    corrective = _make_corrective_prompt(cert_id, exc_1_str)
    try:
        raw_result_2 = await agent.run(messages=corrective, middleware=_mw)  # type: ignore[arg-type]
        raw = str(raw_result_2) if raw_result_2 else ""
        result = _parse_advisor_result(raw)
        result = _scrub_result(result)
        logger.info("[advisor] Corrective retry succeeded for cert=%s", cert_id)
        return result, raw
    except Exception as exc_2:  # noqa: BLE001
        logger.error(
            "[advisor] Both attempts failed for cert=%s: %s — using fallback",
            cert_id,
            exc_2,
        )

    # Fallback
    fallback = _build_fallback_advisor_result(
        cert_id=cert_id,
        scenario=scenario,
        score=score,
        passed=passed,
        passing_score=passing_score,
        attempt=attempt,
        domain_table=domain_table,
        perf_snapshot=perf_snapshot,
        team_percentile=team_percentile,
        team_avg_score=bench_avg,
        sample_size=bench_sample,
        has_benchmark=bench_has_data,
        assessment_results=assessment_results,
        bench_domain_avgs=bench_domain_avgs,
    )
    fallback = _scrub_result(fallback)
    return fallback, raw
