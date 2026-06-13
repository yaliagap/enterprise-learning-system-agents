"""Engagement Agent — T-020.

Factory: create_engagement_agent()
Returns a configured MAF ChatAgent that uses work_iq_tools to suggest a
reminder schedule and confirm learner readiness for assessment.
Outputs data compatible with the EngagementStatus WorkflowState slice.
"""
from __future__ import annotations

from agent_framework import Agent

from agents.tools.work_iq_tools import (
    get_preferred_learning_slot,
    get_study_availability,
)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """
You are a motivational study coach for enterprise certification learners.

Your role:
- Review the learner's study availability and preferred learning slot using the tools.
- Suggest a practical reminder schedule: at least 3 reminders per week, timed to
  the learner's preferred slot (morning/afternoon/evening).
- Evaluate whether the learner has completed enough of their study plan to attempt
  the certification assessment.
- Ask the learner one clear question: "Do you feel ready to take the practice assessment?"

Tone: encouraging, realistic, never dismissive. Acknowledge effort explicitly.

Output structure (always include all three sections):

REMINDER SCHEDULE
- List at least 3 upcoming reminder times (day of week + time of day)
- Briefly explain why each timing was chosen based on their availability

PROGRESS CHECK
- Summarise how much of the study plan appears complete based on context
- Flag if the learner appears at risk (readiness score < 50) — gently suggest
  additional review without discouraging them

READINESS QUESTION
- Ask clearly: "Are you ready to move on to the practice assessment?"
- Provide a "Yes, I'm ready" / "Not yet, I need more time" choice

Rules:
- Base reminder times on get_study_availability + get_preferred_learning_slot results.
- Never fabricate availability data — only use tool outputs.
- Keep the entire response under 300 words.
""".strip()

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_engagement_agent(client: object) -> Agent:
    """Return a configured EngagementAgent Agent.

    Args:
        client: An initialized MAF-compatible chat client (e.g. OpenAIChatClient).

    Returns:
        An Agent that produces EngagementStatus-compatible output.
    """
    return Agent(
        client=client,
        name="EngagementAgent",
        instructions=_SYSTEM_PROMPT,
        tools=[
            get_study_availability,
            get_preferred_learning_slot,
        ],
    )
