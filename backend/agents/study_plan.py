"""Study Plan Generator agent — T-019.

Factory: create_study_plan_generator(client, schedule_tool)
The agent calls two tools:
  1. get_learner_schedule_preferences — triggers UI preferences card via middleware
  2. compute_study_schedule — deterministic Python scheduler (injected by executor)
The LLM is responsible only for the plan_header narrative summary.
"""
from __future__ import annotations

from collections.abc import Callable

from agent_framework import Agent

from agents.tools.work_iq_tools import get_learner_schedule_preferences

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """
You are a study scheduling assistant for enterprise learners.

Follow these steps in order:

Step 1 — Retrieve schedule preferences:
  Call get_learner_schedule_preferences(employee_id) using the employee_id from the prompt.

Step 2 — Compute the schedule:
  Call compute_study_schedule(employee_id) using the same employee_id.
  This tool calculates the complete session list deterministically — do not recalculate it yourself.

Step 3 — Return JSON only:
  No prose, no markdown fences. Return exactly:
  {
    "plan_header": {
      "cert": "<cert_id from prompt>",
      "slot": "<preferred_slot from step 1>",
      "weekly_capacity_hours": <capacity_hours_per_week from step 1>,
      "estimated_weeks": <estimated_weeks from step 2>
    },
    "study_plan_reasoning": "<2-3 sentences explaining which modules were prioritized and why, how session frequency and duration were allocated, and any notable scheduling decisions>"
  }
""".strip()

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_study_plan_generator(client: object, schedule_tool: Callable | None = None) -> Agent:
    """Return a configured StudyPlanGenerator Agent.

    Args:
        client: An initialised MAF-compatible chat client.
        schedule_tool: The compute_study_schedule closure created by the executor,
            bound to the current learner's learning path and domains.
    """
    tools = [get_learner_schedule_preferences]
    if schedule_tool is not None:
        tools.append(schedule_tool)

    return Agent(
        client=client,
        name="StudyPlanGenerator",
        instructions=_SYSTEM_PROMPT,
        tools=tools,
    )
