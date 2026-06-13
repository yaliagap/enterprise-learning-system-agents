"""Certification Advisor Agent.

Provides post-pass performance feedback, official cert URL, next-cert suggestion,
and a reinforcement schedule tailored to the learner's weak areas and score bracket.
"""
from __future__ import annotations

import logging
import textwrap

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Official cert URL template
# ---------------------------------------------------------------------------

_CERT_URL_TEMPLATE = "https://learn.microsoft.com/en-us/credentials/certifications/{cert_id}/"

# ---------------------------------------------------------------------------
# Next cert suggestions
# ---------------------------------------------------------------------------

_NEXT_CERT: dict[str, str] = {
    "AZ-900": "AZ-104 (Azure Administrator)",
    "AZ-104": "AZ-305 (Azure Solutions Architect Expert)",
    "AZ-204": "AZ-400 (DevOps Engineer Expert)",
    "AZ-305": "AZ-400 (DevOps Engineer Expert) or a specialty cert",
    "AZ-400": "AZ-305 (Azure Solutions Architect Expert)",
    "AI-900": "AI-103 (Azure AI Apps and Agents Developer Associate)",
    "AI-901": "AI-103 (Azure AI Apps and Agents Developer Associate)",
    "AI-102": "AI-103 (Azure AI Apps and Agents Developer Associate)",
    "AI-103": "AZ-308 (Azure AI Infrastructure Solutions) or AI-300 (ML Operations Engineer)",
    "SC-900": "SC-500 (Cloud and AI Security Engineer Associate)",
    "AZ-500": "SC-500 (Cloud and AI Security Engineer Associate)",
    "DP-900": "DP-203 (Azure Data Engineer Associate)",
    "DP-203": "AZ-305 (Azure Solutions Architect Expert)",
}

_DEFAULT_NEXT_CERT = "a higher-level Azure specialty certification"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a Microsoft Azure certification advisor.

    You have just reviewed a learner's assessment results and must provide structured
    post-assessment guidance.  Your response MUST include:

    1. **Performance Feedback** — congratulate or encourage the learner based on their score.
       - Score > 90%: celebratory, highlight their achievement.
       - Score 70–75%: encouraging, focus on reinforcement and growth.
       - Other passing scores: balanced positive feedback.

    2. **Official Certification Link** — provide the exact URL to the Microsoft certification page.

    3. **Next Certification Suggestion** — recommend a logical progression from their current cert.

    4. **Reinforcement Schedule** — propose a concrete study plan to address any weak areas.
       If there are no weak areas, suggest advanced topics to deepen expertise.

    Keep your tone professional, warm, and encouraging.  Format with clear section headings.
""")

# ---------------------------------------------------------------------------
# CertificationAdvisorAgent
# ---------------------------------------------------------------------------


class CertificationAdvisorAgent:
    """Generates post-pass certification advice for a learner."""

    def __init__(self, client: object) -> None:
        self._agent = Agent(
            client=client,
            name="CertificationAdvisorAgent",
            instructions=_SYSTEM_PROMPT,
            tools=[],
        )

    async def generate(
        self,
        score: float,
        weak_areas: list[str],
        learner_role: str,
        recommended_cert_id: str,
    ) -> str:
        """Generate certification advice for a learner who passed the assessment.

        Args:
            score: Overall assessment score (0–100).
            weak_areas: List of domain names that scored below the threshold.
            learner_role: The learner's job role (e.g. "Cloud Engineer").
            recommended_cert_id: The certification they just passed (e.g. "AZ-104").

        Returns:
            A formatted markdown string with all four advice sections.
        """
        cert_url = _CERT_URL_TEMPLATE.format(cert_id=recommended_cert_id.lower())
        next_cert = _NEXT_CERT.get(recommended_cert_id, _DEFAULT_NEXT_CERT)

        tone_hint = ""
        if score > 90:
            tone_hint = "The learner scored exceptionally well — use a celebratory, enthusiastic tone."
        elif 70 <= score <= 75:
            tone_hint = (
                "The learner barely passed — use an encouraging tone that focuses on reinforcement."
            )

        weak_areas_text = (
            ", ".join(weak_areas) if weak_areas else "none — the learner performed well across all domains"
        )

        user_message = textwrap.dedent(f"""\
            Learner role: {learner_role}
            Certification just passed: {recommended_cert_id}
            Overall score: {score:.1f}%
            Weak areas: {weak_areas_text}
            Official certification URL: {cert_url}
            Suggested next certification: {next_cert}
            {tone_hint}

            Please provide the four-section post-assessment guidance.
        """)

        try:
            result = await self._agent.run(messages=user_message)  # type: ignore[arg-type]
            return str(result) if result else _build_fallback_advice(
                score, weak_areas, recommended_cert_id, cert_url, next_cert
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[advisor] Agent call failed (%s); using fallback advice", exc)
            return _build_fallback_advice(score, weak_areas, recommended_cert_id, cert_url, next_cert)


# ---------------------------------------------------------------------------
# Fallback (deterministic)
# ---------------------------------------------------------------------------


def _build_fallback_advice(
    score: float,
    weak_areas: list[str],
    cert_id: str,
    cert_url: str,
    next_cert: str,
) -> str:
    """Return deterministic advice when the LLM call fails."""
    if score > 90:
        feedback = (
            f"Outstanding performance! You achieved {score:.1f}% — an excellent result "
            f"that demonstrates strong command of {cert_id} material."
        )
    elif 70 <= score <= 75:
        feedback = (
            f"Congratulations on passing with {score:.1f}%! You cleared the threshold — "
            f"now let's focus on strengthening the areas that need more attention."
        )
    else:
        feedback = (
            f"Well done! You passed {cert_id} with a score of {score:.1f}%. "
            f"Keep building on this momentum."
        )

    weak_section = ""
    if weak_areas:
        weak_section = (
            "\n\n## Reinforcement Schedule\n"
            + f"Focus your study time on these domains: {', '.join(weak_areas)}.\n"
            + "Dedicate 2–3 additional study sessions per weak area before moving on."
        )
    else:
        weak_section = (
            "\n\n## Reinforcement Schedule\n"
            + "No weak areas detected. Consider exploring advanced scenarios and "
            + "hands-on labs to deepen your expertise."
        )

    return textwrap.dedent(f"""\
        ## Performance Feedback
        {feedback}

        ## Official Certification Link
        [{cert_id} certification page]({cert_url})

        ## Next Certification
        Recommended next step: {next_cert}
        {weak_section}
    """)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_certification_advisor_agent(client: object) -> CertificationAdvisorAgent:
    """Return a configured CertificationAdvisorAgent."""
    return CertificationAdvisorAgent(client=client)
