"""MAF workflow dispatcher: orchestrates the full learner pipeline with HITL gate.

Topology:
    seed (list[Message] from AG-UI)
        -> SeedExecutor        (bridges AG-UI list -> LearnerMessage; reads WorkflowState from ctx)
                               If workflow_status == "awaiting_assessment": sends HITLConfirmedMessage
                               Otherwise: sends LearnerMessage
        -> CuratorExecutor     (LearningPathCurator — infers cert from topics, builds learning path)
        -> StudyPlanExecutor   (StudyPlanGenerator)
        -> EngagementExecutor  (EngagementAgent)
        -> HITLGateExecutor    (state-based pause — sets status="awaiting_assessment", ends run)
        -> AssessmentExecutor  (AssessmentAgent) — reached via HITLConfirmedMessage from SeedExecutor
            -> if PASS: workflow_status = "passed", done
            -> if FAIL + retries < max_retries: update weak_areas, back to CuratorExecutor
            -> if FAIL + retries >= max_retries: workflow_status = "max_retries_reached"

Manager branch (separate workflow):
    seed -> ManagerSeedExecutor (bridges list -> str) -> ManagerExecutor (ManagerInsightsAgent)

HITL state-based routing (replaces request_info suspension):
    Run 1: seed (status="planning") -> curator -> study_plan -> engagement -> hitl_gate
            hitl_gate sets status="awaiting_assessment", emits text prompt, ends run normally.
    Run 2: frontend sends new POST (same threadId, state.workflow_status="awaiting_assessment")
            seed detects status="awaiting_assessment" -> confirms, sends HITLConfirmedMessage
            -> AssessmentExecutor.handle_confirmed() -> assessment runs

AG-UI adapter note:
    agent_framework_ag_ui calls workflow.run(message=messages) where messages is a
    list[Message].  SeedExecutor / ManagerSeedExecutor bridge that list into the
    domain message types that downstream executors expect.  WorkflowState is read
    from the workflow context key "workflow_state" which is pre-seeded by the
    LearnerAgentFrameworkWorkflow wrapper in server.py before workflow.run() is called.
"""
import asyncio
import json
import logging
import math
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from ag_ui.core import (
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from agent_framework import (
    Agent,
    Executor,
    FunctionInvocationContext,
    FunctionMiddleware,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from agent_framework.foundry import FoundryChatClient

from observability.otel import trace_agent_invocation, trace_hitl_gate
from agents.assessment import generate_assessment_questions
from workflow.scoring import PASS_THRESHOLD, compute_overall_score, detect_weak_areas, score_question
from workflow.state import (
    AssessmentAnswers,
    AssessmentQuestion,
    AssessmentQuestionPublic,
    AssessmentResult,
    CurationResult,
    DomainWeight,
    EngagementAlert,
    EngagementProposal,
    EngagementStatus,
    GroundingReference,
    KBActivity,
    LearnerSchedulePreferences,
    LearningPathItem,
    QuestionResult,
    StudyMilestone,
    StudyPlanSession,
    UserAnswer,
    WorkIQSignals,
    WorkflowState,
)
from workflow.topics import EXAM_NAMES, TOPIC_DOMAINS, TOPIC_LABELS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AG-UI text message helper
# ---------------------------------------------------------------------------


async def _yield_text(ctx: WorkflowContext, text: str) -> None:
    """Emit a self-contained TEXT_MESSAGE_START/CONTENT/END triple via yield_output.

    The ag-ui adapter passes BaseEvent instances straight through without touching
    its internal flow.message_id tracker.  This means the text message is fully
    closed before the adapter emits RUN_FINISHED on the terminal status event,
    avoiding the "Cannot send RUN_FINISHED while text messages are still active"
    protocol violation that occurs when Content.from_text() is used (which emits
    START+CONTENT but defers END to _drain_open_message, which runs too late).
    """
    message_id = str(uuid.uuid4())
    await ctx.yield_output(TextMessageStartEvent(message_id=message_id, role="assistant"))
    await ctx.yield_output(TextMessageContentEvent(message_id=message_id, delta=text))
    await ctx.yield_output(TextMessageEndEvent(message_id=message_id))


# ---------------------------------------------------------------------------
# Shared message types that flow between executors
# ---------------------------------------------------------------------------


@dataclass
class LearnerMessage:
    """Seed message that carries the full WorkflowState through the pipeline."""

    state: WorkflowState


@dataclass
class PathConfirmedMessage:
    """Sent by SeedExecutor when the learner confirms the learning path.

    Routes directly to StudyPlanExecutor via the seed->study_plan edge,
    bypassing CuratorExecutor.
    """

    state: WorkflowState


@dataclass
class HITLConfirmedMessage:
    """Sent by SeedExecutor when resuming a workflow in awaiting_assessment state.

    The user's next plain-text message acts as the HITL confirmation.  SeedExecutor
    detects workflow_status == "awaiting_assessment", sets hitl_confirmed=True, and
    sends this message so AssessmentExecutor can be reached directly without needing
    a structured HITLResponse object from the frontend.
    """

    state: WorkflowState


@dataclass
class AssessmentAnswersMessage:
    """Sent by SeedExecutor when the learner submits answers for an active exam session.

    Detected when workflow_status == "exam_in_progress" AND state.assessment_answers is populated.
    Routes to AssessmentExecutor.handle_answers() for scoring.
    """

    state: WorkflowState


@dataclass
class CertSelectedMessage:
    """Sent by SeedExecutor when the learner picks a certification from the options list.

    Triggers CuratorExecutor.handle_cert_selected (Run 2) to build the full learning path.
    """

    state: WorkflowState
    selected_cert_id: str


@dataclass
class AssessmentPassedMessage:
    """Sent by AssessmentExecutor when the learner passes the assessment (score >= 70%).

    Routes to CertificationAdvisorExecutor for post-pass advice generation.
    """

    state: WorkflowState


# ---------------------------------------------------------------------------
# Executor: SeedExecutor
# ---------------------------------------------------------------------------


class SeedExecutor(Executor):
    """Bridges the AG-UI list[Message] seed into a LearnerMessage.

    The ag-ui adapter calls workflow.run(message=messages) where messages is a
    list[Message].  MAF routes that list to the start_executor.  This executor
    accepts the list, reads WorkflowState from the workflow context key
    "workflow_state" (pre-seeded by the LearnerAgentFrameworkWorkflow wrapper),
    and forwards a LearnerMessage to CuratorExecutor.
    """

    def __init__(self) -> None:
        super().__init__(id="seed")

    @handler
    async def handle(self, message: list, ctx: WorkflowContext) -> None:
        raw_state = ctx.get_state("workflow_state")
        if raw_state is None:
            raise RuntimeError(
                "[seed] WorkflowState not found in workflow context under key 'workflow_state'. "
                "Ensure LearnerAgentFrameworkWorkflow.run() pre-seeds the state before calling "
                "the workflow."
            )
        state = WorkflowState.model_validate(raw_state)

        # Reset attribution so seed/system text carries no agent label.
        state.current_agent = ""
        state.kb_activity = None

        if state.workflow_status == "awaiting_cert_selection":
            await self._handle_cert_selection(state, message, ctx)
        elif state.workflow_status == "awaiting_path_confirmation":
            await self._handle_path_confirmation(state, ctx)
        elif state.workflow_status == "exam_in_progress" and state.assessment_answers is not None:
            # The learner submitted answers for the active exam — route to scoring.
            logger.info(
                "[seed] Assessment answers received for learner=%s",
                state.learner.learner_id,
            )
            await _yield_text(ctx, "Grading your assessment...")
            await ctx.send_message(AssessmentAnswersMessage(state=state))
        elif state.workflow_status == "awaiting_assessment":
            # The user's next plain-text message is the HITL confirmation.
            # No structured HITLResponse needed — any message resumes the workflow.
            logger.info(
                "[seed] Resuming from HITL gate — confirming assessment for learner=%s",
                state.learner.learner_id,
            )
            state.hitl_confirmed = True
            state.workflow_status = "assessing"
            ctx.set_state("workflow_state", state.model_dump())
            await _yield_text(ctx, "Assessment confirmed! Starting now...")
            await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
            await ctx.send_message(HITLConfirmedMessage(state=state))
        elif state.workflow_status == "exam_failed":
            logger.info(
                "[seed] Retrying after exam failure for learner=%s (attempt %d of %d)",
                state.learner.learner_id,
                state.retry_count + 1,
                state.max_retries,
            )
            state.retry_count += 1
            state.workflow_status = "planning"
            state.hitl_confirmed = False
            state.assessment_answers = None
            state.assessment_questions = []
            ctx.set_state("workflow_state", state.model_dump())
            topics_display = ", ".join(state.learner.topics)
            await _yield_text(ctx, f"Rebuilding your learning path for retry {state.retry_count} of {state.max_retries}...")
            await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
            await ctx.send_message(LearnerMessage(state=state))
        else:
            topics_display = ", ".join(state.learner.topics)
            logger.info(
                "[seed] Bootstrapping workflow for learner=%s topics=%s",
                state.learner.learner_id,
                topics_display,
            )
            await _yield_text(ctx, f"Planning your learning path for topics: {topics_display}...")
            await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
            await ctx.send_message(LearnerMessage(state=state))

    async def _handle_cert_selection(
        self,
        state: WorkflowState,
        message: list,
        ctx: WorkflowContext,
    ) -> None:
        """Parse the learner's cert pick and route to CuratorExecutor Run 2.

        Accepts:
          - Exact cert_id match (e.g. "AI-900", "AZ-204")
          - Position number (e.g. "1", "2", "the first one")
          - Partial cert name match (case-insensitive substring)

        On no/ambiguous match: emits re-prompt text and ends run without status change.
        """
        import re  # noqa: PLC0415

        # Extract user text from the AG-UI messages list
        user_text: str = ""
        for msg in reversed(message):
            role = getattr(msg, "role", None)
            if isinstance(role, str) and role != "user":
                continue
            for content in reversed(getattr(msg, "contents", [])):
                if getattr(content, "type", None) != "text":
                    continue
                text_value = getattr(content, "text", None)
                if isinstance(text_value, str) and text_value.strip():
                    user_text = text_value.strip()
                    break
            if user_text:
                break

        cert_options = state.cert_options
        selected_id: str | None = None

        if cert_options and user_text:
            normalized = user_text.upper().strip()

            # 1. Exact cert_id match
            for opt in cert_options:
                if opt.cert_id.upper() == normalized or opt.cert_id.upper() in normalized.upper():
                    selected_id = opt.cert_id
                    break

            # 2. Position number (e.g. "1", "2", "option 1", "the first")
            if selected_id is None:
                ordinals = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
                for word, pos in ordinals.items():
                    if word in user_text.lower():
                        idx = pos - 1
                        if 0 <= idx < len(cert_options):
                            selected_id = cert_options[idx].cert_id
                        break
                if selected_id is None:
                    nums = re.findall(r"\b([1-9]\d?)\b", user_text)
                    for num_str in nums:
                        idx = int(num_str) - 1
                        if 0 <= idx < len(cert_options):
                            selected_id = cert_options[idx].cert_id
                            break

            # 3. Partial cert name match (case-insensitive)
            if selected_id is None:
                for opt in cert_options:
                    if opt.name.lower() in user_text.lower() or user_text.lower() in opt.name.lower():
                        selected_id = opt.cert_id
                        break

        if selected_id is not None:
            logger.info(
                "[seed] Cert selected: %s for learner=%s",
                selected_id,
                state.learner.learner_id,
            )
            state.selected_cert_id = selected_id
            ctx.set_state("workflow_state", state.model_dump())
            await ctx.send_message(CertSelectedMessage(state=state, selected_cert_id=selected_id))
        else:
            # Re-prompt: list available options
            options_text = "\n".join(
                f"  {i + 1}. {opt.cert_id} — {opt.name} ({int(opt.recommendation_pct)}% match)"
                for i, opt in enumerate(cert_options)
            )
            await _yield_text(
                ctx,
                f"I couldn't identify your selection. Please reply with the cert code or number:\n{options_text}",
            )

    async def _handle_path_confirmation(
        self,
        state: WorkflowState,
        ctx: WorkflowContext,
    ) -> None:
        """Any user message in awaiting_path_confirmation is treated as confirmation.

        Sets status=studying and forwards to StudyPlanExecutor via LearnerMessage.
        """
        logger.info(
            "[seed] Path confirmed for learner=%s — forwarding to study plan",
            state.learner.learner_id,
        )
        state.workflow_status = "studying"
        ctx.set_state("workflow_state", state.model_dump())
        await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
        await _yield_text(ctx, "Path confirmed! Building your study schedule...")
        await ctx.send_message(PathConfirmedMessage(state=state))


# ---------------------------------------------------------------------------
# Executor: ManagerSeedExecutor
# ---------------------------------------------------------------------------


class ManagerSeedExecutor(Executor):
    """Bridges the AG-UI list[Message] seed into a str for ManagerExecutor.

    Extracts the last user text from the incoming messages list.  Falls back to
    a generic prompt when the list is empty or contains no user text.
    """

    def __init__(self) -> None:
        super().__init__(id="manager_seed")

    @handler
    async def handle(self, message: list, ctx: WorkflowContext) -> None:
        user_text: str | None = None
        for msg in reversed(message):
            role = getattr(msg, "role", None)
            if isinstance(role, str) and role != "user":
                continue
            for content in reversed(getattr(msg, "contents", [])):
                if getattr(content, "type", None) != "text":
                    continue
                text_value = getattr(content, "text", None)
                if isinstance(text_value, str) and text_value.strip():
                    user_text = text_value.strip()
                    break
            if user_text:
                break

        prompt = user_text or "Generate manager team insights."
        logger.info("[manager_seed] Forwarding prompt to ManagerExecutor: %s", prompt[:80])
        await ctx.send_message(prompt)


# ---------------------------------------------------------------------------
# Helper: create a deterministic chat client
# ---------------------------------------------------------------------------


def _build_client() -> object:
    """Return a Foundry chat client authenticated via DefaultAzureCredential.

    Reads FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL env vars (native to FoundryChatClient).
    Falls back to a MagicMock stub when the endpoint is not configured (local dev
    without Azure access).
    """
    try:
        import config as cfg  # noqa: PLC0415  — triggers load_dotenv()
        from azure.identity import DefaultAzureCredential  # noqa: PLC0415

        if not cfg.FOUNDRY_PROJECT_ENDPOINT:
            raise ValueError("FOUNDRY_PROJECT_ENDPOINT is not set")

        credential = DefaultAzureCredential()
        return FoundryChatClient(credential=credential)
    except Exception as exc:  # pragma: no cover
        logger.warning("[dispatcher] Foundry client unavailable (%s); using mock stub", exc)
        from unittest.mock import MagicMock  # noqa: PLC0415

        return MagicMock()


# ---------------------------------------------------------------------------
# Helper: parse CurationResult from raw agent output
# ---------------------------------------------------------------------------


def _parse_curation_result(raw: Any, topics: list[str]) -> CurationResult:
    """Attempt to parse the curator agent output into a CurationResult.

    Strips accidental markdown fences, then tries json.loads + Pydantic validation.
    On any failure returns a deterministic fallback CurationResult derived from topics.

    Args:
        raw: Raw value returned by agent.run() — typically a str or MagicMock.
        topics: The learner's selected topic IDs (used as fallback input).

    Returns:
        A valid CurationResult (real or fallback).
    """
    try:
        text = str(raw) if raw else ""
        # Strip accidental ```json ... ``` fences
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # Remove first and last fence lines
            inner = [ln for ln in lines if not ln.startswith("```")]
            text = "\n".join(inner).strip()
        logger.info("[curator] Raw LLM output:\n%s", text)
        data = json.loads(text)
        return CurationResult.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[curator] Failed to parse CurationResult (%s); using fallback", exc)
        return _build_fallback_curation(topics)


def _build_fallback_curation(topics: list[str]) -> CurationResult:
    """Build a deterministic fallback CurationResult from the submitted topics.

    Looks up the first topic in TOPIC_DOMAINS to infer a cert ID; falls back to AZ-900.
    """
    exam = "AZ-900"
    for topic in topics:
        candidates = TOPIC_DOMAINS.get(topic, [])
        if candidates:
            exam = candidates[0]
            break

    return CurationResult(
        exam=exam,
        user_level="beginner",
        priority_domains=[],
        recommended_learning_paths=[
            LearningPathItem(
                resource_id="fallback-001",
                title=f"Official Microsoft Learn path for {exam}",
                cert_id=exam,
                estimated_hours=10.0,
                source_url="https://learn.microsoft.com/en-us/certifications/",
                domain_name="General",
                exam_weight=1.0,
            )
        ],
        coverage_summary=f"Fallback path for {exam} based on selected topics.",
    )


# ---------------------------------------------------------------------------
# Middleware: MCP tool call logger
# ---------------------------------------------------------------------------


class _MCPLoggingMiddleware(FunctionMiddleware):
    """Logs MCP tool call names, arguments, and truncated results for observability."""

    _mcp_logger = logging.getLogger("curator.mcp")

    async def process(self, context: FunctionInvocationContext, call_next: object) -> None:
        name = context.function.name
        args = dict(context.arguments) if context.arguments else {}
        self._mcp_logger.info("[MCP call] %s  args=%s", name, args)
        await call_next()  # type: ignore[operator]
        result = context.result
        result_preview = str(result)[:800] if result is not None else "<none>"
        self._mcp_logger.info("[MCP result] %s →\n%s", name, result_preview)


# ---------------------------------------------------------------------------
# Middleware: schedule context interceptor
# ---------------------------------------------------------------------------


_WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _next_study_date(from_date: date, preferred: set[str]) -> date:
    """Return the first date >= from_date whose lowercase weekday name is in preferred."""
    d = from_date
    for _ in range(14):
        if _WEEKDAY_NAMES[d.weekday()] in preferred:
            return d
        d += timedelta(days=1)
    return from_date


def _compute_deterministic_schedule(
    learning_path: list[LearningPathItem],
    domains_sorted: list[DomainWeight],
    preferred_days: list[str],
    session_hours: float,
    today_str: str,
) -> tuple[list[dict], list[dict]]:
    """Deterministic scheduler: one domain at a time, sessions on preferred weekdays only."""
    logger.info(
        "[schedule] INPUT — %d modules, session_hours=%.2f, days=%s",
        len(learning_path), session_hours, preferred_days,
    )
    for item in learning_path:
        logger.info(
            "[schedule]   module: %s | domain=%s | estimated_hours=%.4f",
            item.title, item.domain_name, item.estimated_hours,
        )

    today = date.fromisoformat(today_str)
    preferred = {d.lower() for d in preferred_days}

    # Group resources by domain in domain order
    domain_resources: dict[str, list[LearningPathItem]] = {dw.domain_name: [] for dw in domains_sorted}
    for item in learning_path:
        key = item.domain_name or ""
        if key in domain_resources:
            domain_resources[key].append(item)
        else:
            domain_resources.setdefault("Other", []).append(item)

    sessions: list[dict] = []
    milestones: list[dict] = []
    current_date = _next_study_date(today, preferred)
    day_counts: dict[str, int] = {}
    milestone_num = 1

    for dw in domains_sorted:
        resources = domain_resources.get(dw.domain_name, [])
        if not resources:
            continue

        domain_session_ids: list[str] = []
        domain_resource_ids = [r.resource_id for r in resources]

        # Pack resources within the domain: fill each session to session_hours,
        # carrying leftover capacity into the next resource. Domain boundary is
        # always a clean session cut (no cross-domain packing).
        slot_remaining = session_hours
        slot_topics: list[str] = []
        slot_resource_ids: list[str] = []
        slot_topic_hours: list[float] = []
        slot_hours: float = 0.0

        def _flush_slot() -> None:
            nonlocal slot_remaining, slot_topics, slot_resource_ids, slot_topic_hours, slot_hours, current_date
            if slot_hours <= 0:
                return
            ds = current_date.isoformat()
            count = day_counts.get(ds, 0) + 1
            day_counts[ds] = count
            sid = f"session-{ds.replace('-', '')}-{count:02d}"
            # Deduplicate topics preserving order; merge hours for repeated entries
            seen: dict[str, float] = {}
            seen_ids: dict[str, str] = {}
            for title, rid, th in zip(slot_topics, slot_resource_ids, slot_topic_hours):
                seen[title] = round(seen.get(title, 0.0) + th, 2)
                seen_ids[title] = rid
            dedup_topics = list(seen.keys())
            sessions.append({
                "session_id": sid,
                "date": ds,
                "hours": round(slot_hours, 2),
                "topics": dedup_topics,
                "resource_ids": [seen_ids[t] for t in dedup_topics],
                "topic_hours": [seen[t] for t in dedup_topics],
            })
            domain_session_ids.append(sid)
            current_date = _next_study_date(current_date + timedelta(days=1), preferred)
            slot_remaining = session_hours
            slot_topics = []
            slot_resource_ids = []
            slot_topic_hours = []
            slot_hours = 0.0

        for resource in resources:
            res_remaining = max(resource.estimated_hours, 0.0)
            while res_remaining > 0:
                chunk = min(slot_remaining, res_remaining)
                slot_hours += chunk
                slot_remaining -= chunk
                res_remaining = round(res_remaining - chunk, 6)
                slot_topics.append(resource.title)
                slot_resource_ids.append(resource.resource_id)
                slot_topic_hours.append(round(chunk, 2))
                if slot_remaining <= 0:
                    _flush_slot()

        # Emit any partial session at domain boundary
        _flush_slot()

        last_date = sessions[-1]["date"] if sessions else today_str
        diff_days = (date.fromisoformat(last_date) - today).days
        target_week = max(1, diff_days // 7 + 1)

        milestones.append({
            "milestone_id": f"milestone-{milestone_num:02d}",
            "domain_name": dw.domain_name,
            "exam_weight": dw.exam_weight,
            "target_week": target_week,
            "target_date": last_date,
            "resource_ids": domain_resource_ids,
            "session_ids": domain_session_ids,
            "status": "pending",
        })
        milestone_num += 1

    logger.info("[schedule] OUTPUT — %d sessions generated", len(sessions))
    for s in sessions:
        logger.info(
            "[schedule]   session %s | date=%s | hours=%.2f | topics=%s | topic_hours=%s",
            s["session_id"], s["date"], s["hours"], s["topics"], s.get("topic_hours", []),
        )

    return sessions, milestones


def _make_schedule_tool(
    learning_path: list[LearningPathItem],
    domains_sorted: list[DomainWeight],
    today_str: str,
    result_container: dict,
):
    """Return a compute_study_schedule async function bound to the current state."""
    from grounding.factory import IQProviderFactory  # noqa: PLC0415

    async def compute_study_schedule(employee_id: str) -> str:
        """Compute the complete study schedule deterministically from Work IQ availability.

        Schedules sessions domain by domain (heaviest domain first), placing each session
        only on the learner's preferred study days. Returns a summary of the computed plan.
        """
        av = IQProviderFactory().work().availability(employee_id)
        preferred_days: list[str] = av.preferred_study_days or ["Monday", "Wednesday", "Friday"]
        session_hours: float = max(av.session_duration_hours or 1.5, 0.5)

        computed_sessions, computed_milestones = _compute_deterministic_schedule(
            learning_path=learning_path,
            domains_sorted=domains_sorted,
            preferred_days=preferred_days,
            session_hours=session_hours,
            today_str=today_str,
        )

        result_container.update({
            "sessions": computed_sessions,
            "milestones": computed_milestones,
            "preferred_days": preferred_days,
            "session_hours": session_hours,
        })

        total_hours = sum(r.estimated_hours for r in learning_path)
        cap = session_hours * len(preferred_days)
        estimated_weeks = max(1, math.ceil(total_hours / cap)) if cap > 0 else 10

        return json.dumps({
            "status": "computed",
            "sessions_count": len(computed_sessions),
            "milestones_count": len(computed_milestones),
            "preferred_days": preferred_days,
            "session_hours": session_hours,
            "total_hours": total_hours,
            "estimated_weeks": estimated_weeks,
        })

    return compute_study_schedule


class _ScheduleContextMiddleware(FunctionMiddleware):
    """Intercepts get_learner_schedule_preferences results and writes them to WorkflowState."""

    _TARGET = "get_learner_schedule_preferences"

    def __init__(self, state: WorkflowState, ctx: WorkflowContext) -> None:
        self._state = state
        self._ctx = ctx

    async def process(self, context: FunctionInvocationContext, call_next: object) -> None:
        await call_next()  # type: ignore[operator]
        if context.function.name == self._TARGET:
            try:
                # MAF returns Content objects in context.result, not the Python return value.
                # Re-derive preferences directly from the grounding layer using the learner id.
                from grounding.factory import IQProviderFactory  # noqa: PLC0415
                employee_id = self._state.learner.learner_id
                av = IQProviderFactory().work().availability(employee_id)
                days = av.preferred_study_days or ["Monday", "Wednesday", "Friday"]
                cap = (av.session_duration_hours or 1.0) * len(days)
                if cap <= 0:
                    cap = 3.0
                cap = max(cap, 1.0)
                prefs = LearnerSchedulePreferences(
                    employee_id=employee_id,
                    preferred_study_days=days,
                    session_duration_hours=av.session_duration_hours if av.session_duration_hours > 0 else 1.0,
                    preferred_slot=av.preferred_slot,
                    capacity_hours_per_week=round(cap, 1),
                    source=av.source,
                    is_fallback=(av.source == "default"),
                )
                self._state.schedule_context = prefs
                await self._ctx.yield_output(StateSnapshotEvent(snapshot=self._state.model_dump()))
            except Exception as exc:  # noqa: BLE001
                logger.warning("[study_plan] Could not parse schedule_context: %s", exc)


# ---------------------------------------------------------------------------
# Helpers: priority domains reconstruction and study plan result application
# ---------------------------------------------------------------------------


def _reconstruct_priority_domains(learning_path: list[LearningPathItem]) -> list[DomainWeight]:
    """Deduplicate domain_name+exam_weight from a LearningPathItem list."""
    seen: dict[str, float] = {}
    for item in learning_path:
        if item.domain_name and item.exam_weight is not None:
            name = item.domain_name
            if name not in seen:
                seen[name] = float(item.exam_weight)
    return [DomainWeight(domain_name=k, exam_weight=v) for k, v in seen.items()]


def _apply_study_plan_result(
    state: WorkflowState,
    result: Any,
    domains: list[DomainWeight],
    today: str,
    precomputed: dict | None = None,
) -> None:
    """Populate state.study_plan and state.study_milestones.

    Uses precomputed (from compute_study_schedule tool) when available — the LLM result
    is only used as a last-resort fallback.
    """
    if precomputed and precomputed.get("sessions"):
        try:
            state.study_plan = [StudyPlanSession(**s) for s in precomputed["sessions"]]
            state.study_milestones = [StudyMilestone(**m) for m in precomputed["milestones"]]
            logger.info(
                "[study_plan] Used precomputed schedule: %d sessions, %d milestones",
                len(state.study_plan),
                len(state.study_milestones),
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("[study_plan] Failed to apply precomputed schedule (%s); falling back", exc)

    import re  # noqa: PLC0415

    try:
        text = str(result) if result else ""
        text = text.strip()
        # Strip markdown fences
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text.strip())
            text = text.strip()

        data = json.loads(text)

        # Parse study_plan sessions
        sessions: list[StudyPlanSession] = []
        session_id_pattern = re.compile(r"^session-\d{8}-\d{2}$")
        for i, raw_session in enumerate(data.get("study_plan", []), start=1):
            sid = str(raw_session.get("session_id", ""))
            if not session_id_pattern.match(sid):
                # Repair malformed session_id
                date_str = str(raw_session.get("date", today)).replace("-", "")
                sid = f"session-{date_str}-{i:02d}"
            sessions.append(
                StudyPlanSession(
                    session_id=sid,
                    date=str(raw_session.get("date", today)),
                    hours=float(raw_session.get("hours", 1.0)),
                    topics=list(raw_session.get("topics", [])),
                    resource_ids=list(raw_session.get("resource_ids", [])),
                )
            )

        # Parse study_milestones
        milestones: list[StudyMilestone] = []
        for raw_ms in data.get("study_milestones", []):
            raw_weight = float(raw_ms.get("exam_weight", 0.0))
            # Normalize: LLM sometimes returns percentage (e.g. 25.0) instead of fraction (0.25)
            if raw_weight > 1.0:
                raw_weight = raw_weight / 100.0
            milestones.append(
                StudyMilestone(
                    milestone_id=str(raw_ms.get("milestone_id", "milestone-01")),
                    domain_name=str(raw_ms.get("domain_name", "")),
                    exam_weight=raw_weight,
                    target_week=int(raw_ms.get("target_week", 1)),
                    target_date=str(raw_ms.get("target_date", today)),
                    resource_ids=list(raw_ms.get("resource_ids", [])),
                    session_ids=list(raw_ms.get("session_ids", [])),
                    status=raw_ms.get("status", "pending"),
                )
            )

        state.study_plan = sessions
        state.study_milestones = milestones

    except Exception as exc:  # noqa: BLE001
        logger.warning("[study_plan] Failed to parse study plan result (%s); using fallback", exc)
        # Deterministic fallback: one session per domain starting from today
        fallback_sessions: list[StudyPlanSession] = []
        for i, domain in enumerate(domains):
            domain_resources = [
                item.resource_id
                for item in state.learning_path
                if item.domain_name == domain.domain_name
            ] or [f"fallback-{i + 1:03d}"]
            date_str = today.replace("-", "")
            fallback_sessions.append(
                StudyPlanSession(
                    session_id=f"session-{date_str}-{i + 1:02d}",
                    date=today,
                    hours=1.0,
                    topics=[domain.domain_name],
                    resource_ids=domain_resources,
                )
            )
        if not fallback_sessions:
            fallback_sessions.append(
                StudyPlanSession(
                    session_id=f"session-{today.replace('-', '')}-01",
                    date=today,
                    hours=2.0,
                    topics=state.learner.topics,
                    resource_ids=["fallback-001"],
                )
            )
        state.study_plan = fallback_sessions
        state.study_milestones = []


# ---------------------------------------------------------------------------
# Executor: CuratorExecutor
# ---------------------------------------------------------------------------


class CuratorExecutor(Executor):
    """Runs the two-run LearningPathCurator interactive flow.

    Run 1 (handle LearnerMessage):
        Calls get_learner_profile + search_knowledge_base → recommends certs →
        sets workflow_status=awaiting_cert_selection and ends run.

    Run 2 (handle_cert_selected CertSelectedMessage):
        Builds full learning path via MS Learn MCP tools →
        sets workflow_status=awaiting_path_confirmation and ends run.
    """

    def __init__(self) -> None:
        super().__init__(id="curator")
        from agents.curator import (  # noqa: PLC0415
            create_curator_run1,
            create_curator_run2,
            create_kb_mcp_tool,
            create_ms_learn_mcp_tool,
        )

        self._client = _build_client()
        self._kb_mcp_tool = create_kb_mcp_tool()
        self._mcp_tool = create_ms_learn_mcp_tool()
        # Both run agents are created lazily inside their respective handlers,
        # after the MCP tool connects, so mcp_tool.functions is populated.

    @handler
    async def handle(self, message: LearnerMessage, ctx: WorkflowContext) -> None:
        """Run 1: recommend certs → set awaiting_cert_selection → end run."""
        from agents.curator import _parse_cert_options, create_curator_run1  # noqa: PLC0415

        state = message.state
        topics_display = ", ".join(TOPIC_LABELS.get(t, t) for t in state.learner.topics)
        logger.info(
            "[curator/run1] Starting for learner=%s topics=%s",
            state.learner.learner_id,
            topics_display,
        )

        experience = state.learner.experience_level or "intermediate"
        goals_line = (
            f"Goals: {'; '.join(state.learner.goals)}\n"
            if state.learner.goals
            else ""
        )
        seniority_line = (
            f"Seniority: {state.learner.seniority}\n"
            if getattr(state.learner, "seniority", None)
            else ""
        )
        roles_line = (
            f"Roles: {', '.join(state.learner.roles)}\n"
            if getattr(state.learner, "roles", None)
            else ""
        )
        prompt = (
            f"Learner ID: {state.learner.learner_id}\n"
            f"Role: {state.learner.role}\n"
            f"{roles_line}"
            f"Experience level: {experience}\n"
            f"{seniority_line}"
            f"Selected topics: {topics_display}\n"
            f"{goals_line}"
            "\nRecommend the most suitable Azure certifications for this learner. "
            "Return STRICT JSON as instructed."
        )

        kb_mcp = getattr(self, "_kb_mcp_tool", None)
        client = getattr(self, "_client", None) or _build_client()
        with trace_agent_invocation("learning_path_curator_run1", state.learner.learner_id):
            try:
                if kb_mcp is not None:
                    # Connect first so kb_mcp.functions is populated, then build the agent.
                    async with kb_mcp:
                        agent_run1 = create_curator_run1(client, kb_mcp)
                        result = await agent_run1.run(messages=prompt, middleware=[_MCPLoggingMiddleware()])  # type: ignore[arg-type]
                else:
                    # Use pre-built agent when available (test mocks set _agent_run1 directly).
                    agent_run1 = getattr(self, "_agent_run1", None) or create_curator_run1(client)
                    result = await agent_run1.run(messages=prompt, middleware=[_MCPLoggingMiddleware()])  # type: ignore[arg-type]
            except Exception as exc:
                logger.warning("[curator/run1] Agent call failed (%s); returning empty cert_options", exc)
                result = None

        cert_options = _parse_cert_options(result)
        n = len(cert_options)
        logger.info("[curator/run1] Parsed %d cert options", n)

        state.cert_options = cert_options
        state.current_agent = "curator"
        state.kb_activity = None
        state.curator_response = None
        state.workflow_status = "awaiting_cert_selection"
        ctx.set_state("workflow_state", state.model_dump())
        await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))

        if n > 0:
            options_text = "\n".join(
                f"  {i + 1}. {o.cert_id} — {o.name} ({int(o.recommendation_pct)}% match)"
                + (" [already obtained]" if o.already_obtained else "")
                for i, o in enumerate(cert_options)
            )
            await _yield_text(
                ctx,
                f"I've found {n} certification(s) that match your profile. "
                "Please review and select the one you'd like to pursue:\n" + options_text,
            )
        else:
            await _yield_text(
                ctx,
                "No matching certifications were found for your current profile. "
                "Please refine your profile or contact support.",
            )
        # Run ends here — SeedExecutor will route on the next user message.

    @handler
    async def handle_path_confirmed(
        self, message: PathConfirmedMessage, ctx: WorkflowContext
    ) -> None:
        """Path already confirmed — forward directly to StudyPlanExecutor via the chain."""
        await ctx.send_message(LearnerMessage(state=message.state))

    @handler
    async def handle_cert_selected(
        self,
        message: CertSelectedMessage,
        ctx: WorkflowContext,
    ) -> None:
        """Run 2: build full learning path for selected cert → set awaiting_path_confirmation."""
        state = message.state
        selected_cert_id = message.selected_cert_id

        logger.info(
            "[curator/run2] Building full path for cert=%s learner=%s",
            selected_cert_id,
            state.learner.learner_id,
        )

        selected_cert = next(
            (c for c in state.cert_options if c.cert_id == selected_cert_id), None
        )
        cert_name = selected_cert.name if selected_cert else selected_cert_id
        lp_uids = selected_cert.lp_uids if selected_cert else []
        lp_uids_line = (
            f"LP UIDs: {lp_uids}\n"
            if lp_uids
            else "LP UIDs: []\n"
        )
        prompt = (
            f"Cert code: {selected_cert_id}\n"
            f"Cert name: {cert_name}\n"
            f"{lp_uids_line}"
            "Build the full learning path for this certification. "
            "If LP UIDs are provided above, use them directly with get_learning_path — "
            "do NOT call search_learning_paths. "
            "If LP UIDs is empty, call search_learning_paths(exam_id) to discover them. "
            "Return STRICT JSON as instructed."
        )

        client = getattr(self, "_client", None) or _build_client()
        with trace_agent_invocation("learning_path_curator_run2", state.learner.learner_id):
            try:
                async with self._mcp_tool:
                    from agents.curator import create_curator_run2  # noqa: PLC0415
                    # Use pre-built agent when available (test mocks set _agent_run2 directly).
                    agent_run2 = getattr(self, "_agent_run2", None) or create_curator_run2(client, self._mcp_tool)
                    result = await agent_run2.run(messages=prompt, middleware=[_MCPLoggingMiddleware()])  # type: ignore[arg-type]
            except Exception as exc:
                logger.warning("[curator/run2] Agent call failed (%s); using fallback curation", exc)
                result = None

        curation = _parse_curation_result(result, state.learner.topics)

        state.recommended_cert_id = curation.exam
        state.recommended_cert_name = EXAM_NAMES.get(curation.exam, f"Microsoft Azure {curation.exam}")
        state.coverage_summary = curation.coverage_summary
        state.grounding_references = curation.references
        state.learning_path = list(curation.recommended_learning_paths)
        state.priority_domains = (
            list(curation.priority_domains)
            if curation.priority_domains
            else _reconstruct_priority_domains(state.learning_path)
        )

        # Clear cert selection fields now that Run 2 is complete
        state.cert_options = []
        state.selected_cert_id = None

        state.current_agent = "curator"
        state.kb_activity = None
        state.curator_response = None
        state.workflow_status = "awaiting_path_confirmation"
        ctx.set_state("workflow_state", state.model_dump())
        await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))

        cert_name = state.recommended_cert_name or selected_cert_id
        await _yield_text(
            ctx,
            f"Your learning path for {cert_name} is ready. "
            "Send any message to confirm and proceed to your study schedule.",
        )
        # Run ends here — SeedExecutor routes on next user message (awaiting_path_confirmation).


# ---------------------------------------------------------------------------
# Executor: StudyPlanExecutor
# ---------------------------------------------------------------------------


class StudyPlanExecutor(Executor):
    """Builds a deterministic study schedule via a compute_study_schedule tool.

    The agent calls two tools:
    1. get_learner_schedule_preferences — triggers middleware → preferences card in UI
    2. compute_study_schedule — Python does the date math, writes to result_container
    The agent's LLM output is only used if the tool never fires (fallback).
    """

    def __init__(self) -> None:
        super().__init__(id="study_plan")

    @handler
    async def handle(self, message: LearnerMessage, ctx: WorkflowContext[LearnerMessage]) -> None:
        from agents.study_plan import create_study_plan_generator  # noqa: PLC0415

        state = message.state
        logger.info("[study_plan] Building schedule for learner=%s", state.learner.learner_id)

        today = date.today().isoformat()
        cert_ref = state.recommended_cert_id or "your certification"

        domains = state.priority_domains or _reconstruct_priority_domains(state.learning_path)
        domains_sorted = sorted(domains, key=lambda d: d.exam_weight, reverse=True)

        # Shared container: compute_study_schedule tool writes here; executor reads it
        result_container: dict = {}
        schedule_tool = _make_schedule_tool(state.learning_path, domains_sorted, today, result_container)

        domains_text = "\n".join(
            f"  - {d.domain_name} (exam_weight: {d.exam_weight:.2f})" for d in domains_sorted
        ) or "  (no domains provided)"
        path_text = "\n".join(
            f"  - [{item.resource_id}] {item.title} ({item.estimated_hours}h)"
            + (f" — domain: {item.domain_name}" if item.domain_name else "")
            for item in state.learning_path
        ) or "  (no resources provided)"

        prompt = (
            f"Today is {today}.\n"
            f"Learner: {state.learner.learner_id}\n"
            f"Employee ID: {state.learner.employee_id}\n"
            f"Target certification: {cert_ref}\n\n"
            f"Priority exam domains:\n{domains_text}\n\n"
            f"Learning path resources:\n{path_text}\n\n"
            "Call these two tools IN ORDER using the employee_id above:\n"
            "1. get_learner_schedule_preferences(employee_id) — retrieves schedule preferences\n"
            "2. compute_study_schedule(employee_id) — computes the complete schedule\n\n"
            'After both calls, return ONLY this JSON (no markdown, no prose):\n'
            '{"plan_header": {"cert": "<cert_id>", "slot": "<slot>", '
            '"weekly_capacity_hours": <float>, "estimated_weeks": <int>}}'
        )

        agent = create_study_plan_generator(_build_client(), schedule_tool=schedule_tool)
        mw = _ScheduleContextMiddleware(state, ctx)
        with trace_agent_invocation("study_plan_generator", state.learner.learner_id):
            try:
                result = await agent.run(messages=prompt, middleware=[mw, _MCPLoggingMiddleware()])  # type: ignore[arg-type]
            except Exception as exc:
                logger.warning("[study_plan] Agent call failed (%s); using fallback", exc)
                result = None

        _apply_study_plan_result(state, result, domains_sorted, today, precomputed=result_container)

        state.current_agent = "study_plan"
        state.kb_activity = None
        ctx.set_state("workflow_state", state.model_dump())
        await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
        await _yield_text(ctx, "Study schedule created. Setting up engagement and readiness check...")
        await ctx.send_message(LearnerMessage(state=state))


# ---------------------------------------------------------------------------
# Engagement tool helpers
# ---------------------------------------------------------------------------



def _make_engagement_tool(state: WorkflowState, result_container: dict):
    """Return an async submit_engagement_proposal closure bound to *state*.

    Mirrors _make_schedule_tool: the closure validates the JSON submitted by the
    Engagement Agent, writes the validated dict to result_container["proposal"],
    and returns a short JSON ack so the agent stops naturally.

    On validation failure: returns a rejection JSON (normal tool result — does NOT
    raise) so the agent receives a natural retry signal and can resubmit.
    """

    async def submit_engagement_proposal(proposal: dict) -> str:
        """Submit the structured engagement proposal for validation and storage.

        Args:
            proposal: Dict matching the EngagementProposal schema with workIQSignals
                and alerts list.

        Returns:
            JSON string: {"status": "accepted", "alerts": 4} on success, or
            {"status": "rejected", "error": "<message>"} on validation failure.
        """
        try:
            logger.info("[engagement] submit_engagement_proposal called")
            raw = proposal
            engagement_proposal = EngagementProposal.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[engagement] Proposal validation failed: %s", exc)
            return json.dumps({"status": "rejected", "error": str(exc)})

        alert_types = {a.type for a in engagement_proposal.alerts}
        required_types = {"reminder", "milestone", "motivation", "risk"}
        if alert_types != required_types:
            msg = f"Missing alert types: {required_types - alert_types}"
            logger.warning("[engagement] %s", msg)
            return json.dumps({"status": "rejected", "error": msg})

        result_container["proposal"] = raw
        logger.info("[engagement] Proposal accepted — %d alerts stored", len(engagement_proposal.alerts))
        return json.dumps({"status": "accepted", "alerts": len(engagement_proposal.alerts)})

    return submit_engagement_proposal


# ---------------------------------------------------------------------------
# Executor: EngagementExecutor
# ---------------------------------------------------------------------------


class EngagementExecutor(Executor):
    """Runs the EngagementAgent to produce a structured EngagementProposal.

    Provides the agent with study plan context (sessions, milestones, weeks, study days)
    so it can apply the decision rules from its system prompt using the Work IQ profile
    it retrieves via get_engagement_profile. The agent owns all field computation.
    """

    def __init__(self) -> None:
        super().__init__(id="engagement")

    @handler
    async def handle(self, message: LearnerMessage, ctx: WorkflowContext[LearnerMessage]) -> None:
        from agents.engagement import create_engagement_agent  # noqa: PLC0415

        state = message.state
        employee_id = state.learner.learner_id
        logger.info("[engagement] Engaging learner=%s", employee_id)

        # ------------------------------------------------------------------
        # 1. Build study plan context for the agent prompt
        # ------------------------------------------------------------------
        total_sessions = len(state.study_plan)
        total_weeks = max((m.target_week for m in state.study_milestones), default=1)
        total_milestones = len(state.study_milestones)
        study_days: list[str] = (
            state.schedule_context.preferred_study_days
            if state.schedule_context
            else ["Monday", "Wednesday", "Friday"]
        )
        last_study_day = study_days[-1] if study_days else "Friday"
        cert_ref = state.recommended_cert_id or "your certification"

        milestones_ctx = [
            {
                "domain_name": m.domain_name,
                "target_date": m.target_date,
                "target_week": m.target_week,
            }
            for m in state.study_milestones
        ]

        study_context = {
            "total_sessions": total_sessions,
            "total_weeks": total_weeks,
            "total_milestones": total_milestones,
            "study_days": study_days,
            "last_study_day": last_study_day,
            "milestones": milestones_ctx,
        }

        prompt = (
            f"Generate the engagement proposal for employee {employee_id} "
            f"studying {cert_ref}.\n\n"
            f"STUDY CONTEXT (use for repeatCounts, timing, and totals):\n"
            f"{json.dumps(study_context, indent=2)}\n\n"
            f"Call get_engagement_profile('{employee_id}') to get the Work IQ signals, "
            f"apply the decision rules from your instructions, then call "
            f"submit_engagement_proposal with the complete JSON."
        )

        # ------------------------------------------------------------------
        # 2. Run agent
        # ------------------------------------------------------------------
        result_container: dict = {}
        submit_tool = _make_engagement_tool(state, result_container)
        agent = create_engagement_agent(_build_client(), submit_tool=submit_tool)

        with trace_agent_invocation("engagement_agent", employee_id):
            try:
                await agent.run(messages=prompt)  # type: ignore[arg-type]
            except Exception as exc:
                logger.warning("[engagement] Agent call failed (%s); continuing", exc)

        # ------------------------------------------------------------------
        # 3. Store validated proposal (agent owns all field values)
        # ------------------------------------------------------------------
        proposal_raw = result_container.get("proposal")
        if proposal_raw is not None:
            try:
                state.engagement_proposal = EngagementProposal.model_validate(proposal_raw)
                logger.info(
                    "[engagement] Proposal stored — %d alerts", len(state.engagement_proposal.alerts)
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("[engagement] Failed to parse/store proposal: %s; skipping", exc)
                state.engagement_proposal = None
        else:
            logger.warning("[engagement] Agent did not call submit_engagement_proposal; skipping proposal")
            state.engagement_proposal = None

        # ------------------------------------------------------------------
        # 6. Backward-compat EngagementStatus write
        # ------------------------------------------------------------------
        state.engagement = EngagementStatus(
            reminders_sent=0,
            preferred_slot=state.learner.role.lower().replace(" ", "_"),
        )
        state.current_agent = "engagement"
        state.kb_activity = None
        ctx.set_state("workflow_state", state.model_dump())
        await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
        await _yield_text(ctx, "Engagement configured. Preparing readiness check...")
        await ctx.send_message(LearnerMessage(state=state))


# ---------------------------------------------------------------------------
# Executor: HITLGateExecutor
# ---------------------------------------------------------------------------


class HITLGateExecutor(Executor):
    """State-based HITL gate: sets workflow_status to "awaiting_assessment" and ends the run.

    The next user message (any text) will be handled by SeedExecutor which checks
    workflow_status == "awaiting_assessment" and sends HITLConfirmedMessage to
    AssessmentExecutor.  This avoids ctx.request_info() suspension which requires
    the frontend to send a structured HITLResponse object.
    """

    def __init__(self) -> None:
        super().__init__(id="hitl_gate")

    @handler
    async def handle(
        self,
        message: LearnerMessage,
        ctx: WorkflowContext[LearnerMessage, WorkflowState],
    ) -> None:
        state = message.state
        logger.info(
            "[hitl_gate] Suspending workflow for learner=%s — awaiting confirmation",
            state.learner.learner_id,
        )

        state.workflow_status = "awaiting_assessment"
        state.current_agent = ""
        state.kb_activity = None
        ctx.set_state("workflow_state", state.model_dump())

        # Record the HITL pause in the active trace.
        trace_hitl_gate("paused")

        await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
        await _yield_text(ctx, "Your learning path is ready. Send any message to confirm you want to proceed to assessment.")
        # Run ends here. SeedExecutor will resume on the next user message.


# ---------------------------------------------------------------------------
# Executor: AssessmentExecutor
# ---------------------------------------------------------------------------


class AssessmentExecutor(Executor):
    """Handles question generation and scoring for the assessment flow.

    handle(HITLConfirmedMessage): generates 15 questions via a grounded LLM agent
        (MS Learn MCP + learner history), stores them in ctx with correct answers,
        emits STATE_SNAPSHOT with public projection (no correct answers),
        sets status="exam_in_progress", ends run.

    handle_answers(AssessmentAnswersMessage): retrieves stored questions,
        scores the submitted answers, derives domain_scores, persists the attempt,
        emits result STATE_SNAPSHOT, and routes to CertificationAdvisorExecutor (pass)
        or CuratorExecutor (fail).
    """

    def __init__(self) -> None:
        super().__init__(id="assessment")
        from agents.curator import create_kb_mcp_tool, create_ms_learn_mcp_tool  # noqa: PLC0415

        self._client = _build_client()
        self._mcp_tool = create_ms_learn_mcp_tool()
        self._kb_mcp_tool = create_kb_mcp_tool()
        # Both MCP tools connected lazily inside handle() after connection so .functions is populated.

    @handler
    async def handle(
        self,
        message: HITLConfirmedMessage,
        ctx: WorkflowContext,
    ) -> None:
        """Generate 15 questions via grounded LLM agent; store with answers in ctx; emit public snapshot."""
        import datetime  # noqa: PLC0415

        state = message.state
        cert_ref = state.recommended_cert_id or "AZ-900"
        cert_display = state.recommended_cert_name or cert_ref
        learner_id = state.learner.learner_id

        logger.info(
            "[assessment] Generating questions for learner=%s cert=%s",
            learner_id,
            cert_ref,
        )

        reasoning: str | None = None
        with trace_agent_invocation("assessment_agent", learner_id):
            try:
                from agents.assessment import create_assessment_agent  # noqa: PLC0415
                from agents.tools.assessment_tools import get_learner_performance  # noqa: PLC0415

                kb_mcp = getattr(self, "_kb_mcp_tool", None)
                ms_mcp = self._mcp_tool

                async with ms_mcp:
                    ms_functions = list(getattr(ms_mcp, "functions", []) or [])
                    if kb_mcp is not None:
                        async with kb_mcp:
                            kb_functions = list(getattr(kb_mcp, "functions", []) or [])
                            agent = create_assessment_agent(
                                self._client,
                                get_learner_performance,
                                *kb_functions,
                                *ms_functions,
                            )
                            questions, reasoning = await generate_assessment_questions(
                                agent=agent,
                                cert_id=cert_ref,
                                learner_id=learner_id,
                            )
                    else:
                        agent = create_assessment_agent(
                            self._client,
                            get_learner_performance,
                            *ms_functions,
                        )
                        questions, reasoning = await generate_assessment_questions(
                            agent=agent,
                            cert_id=cert_ref,
                            learner_id=learner_id,
                        )
            except Exception as exc:
                logger.warning(
                    "[assessment] Grounded generation failed (%s); using fallback questions",
                    exc,
                )
                from agents.assessment import _build_fallback_questions  # noqa: PLC0415
                questions = _build_fallback_questions(cert_ref, {})
                reasoning = None

        # Stash reasoning_distribution for handle_answers
        ctx.set_state("assessment_reasoning_distribution", reasoning)

        # Store full questions (with correct answers) in MAF context — never sent to frontend
        ctx.set_state("assessment_questions_full", [q.model_dump() for q in questions])

        # Build public projection — strip correct_answers; include grounding_reference
        public_questions = [
            AssessmentQuestionPublic(
                id=q.id,
                text=q.text,
                question_type=q.question_type,
                options=q.options,
                correct_answer_count=len(q.correct_answers),
                domain=q.domain,
                exam_weight_pct=q.exam_weight_pct,
                explanation=q.explanation,
                difficulty=q.difficulty,
                bloom_level=q.bloom_level,
                is_scenario_based=q.is_scenario_based,
                scenario_context=q.scenario_context,
                grounding_reference=q.grounding_reference,
            )
            for q in questions
        ]

        state.assessment_questions = public_questions
        state.workflow_status = "exam_in_progress"
        state.current_agent = "assessment"
        state.kb_activity = None
        ctx.set_state("workflow_state", state.model_dump())

        await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
        await _yield_text(
            ctx,
            f"Your {cert_display} assessment is ready. Complete all 15 questions to proceed.",
        )
        # Run ends here — frontend renders ExamInterface; next run carries assessment_answers

    @handler
    async def handle_answers(
        self,
        message: AssessmentAnswersMessage,
        ctx: WorkflowContext,
    ) -> None:
        """Score submitted answers; route to advisor (pass) or curator (fail)."""
        import datetime  # noqa: PLC0415

        state = message.state

        # Retrieve full questions (with correct answers) from MAF context
        raw_questions = ctx.get_state("assessment_questions_full") or []
        full_questions = [AssessmentQuestion.model_validate(q) for q in raw_questions]

        if not full_questions:
            logger.error(
                "[assessment] No stored questions found in ctx for learner=%s — aborting scoring",
                state.learner.learner_id,
            )
            await _yield_text(ctx, "Assessment error: questions not found. Please restart.")
            return

        # Build answer lookup
        assert state.assessment_answers is not None
        answer_map: dict[str, list[str]] = {
            ua.question_id: ua.selected_answers
            for ua in state.assessment_answers.answers
        }

        # Score each question
        per_question_results: list[QuestionResult] = []
        for q in full_questions:
            user_ans = answer_map.get(q.id, [])
            partial = score_question(q.question_type, user_ans, q.correct_answers)
            is_correct = partial == 1.0
            per_question_results.append(
                QuestionResult(
                    question_id=q.id,
                    user_answers=user_ans,
                    correct_answers=q.correct_answers,
                    is_correct=is_correct,
                    partial_score=partial,
                    explanation=q.explanation,
                )
            )

        overall_score = compute_overall_score(per_question_results)
        passed = overall_score >= PASS_THRESHOLD
        weak_areas = detect_weak_areas(full_questions, per_question_results)

        # Derive per-domain scores from per_question_results grouped by question.domain
        qid_to_domain: dict[str, str] = {q.id: q.domain for q in full_questions}
        domain_to_scores: dict[str, list[float]] = {}
        for r in per_question_results:
            d = qid_to_domain.get(r.question_id, "General")
            domain_to_scores.setdefault(d, []).append(r.partial_score)
        domain_scores: dict[str, float] = {
            d: round(sum(v) / len(v) * 100, 1)
            for d, v in domain_to_scores.items()
        }

        cert_ref = state.recommended_cert_id or "AZ-900"

        assessment_result = AssessmentResult(
            attempt=state.retry_count + 1,
            score=overall_score,
            passed=passed,
            passing_score=PASS_THRESHOLD,
            weak_areas=weak_areas,
            completed_at=datetime.datetime.utcnow().isoformat() + "Z",
            per_question_results=per_question_results,
            domain_scores=domain_scores,
            reasoning_distribution=ctx.get_state("assessment_reasoning_distribution"),
        )
        state.assessment_results.append(assessment_result)

        # Persist attempt to learner_performance.json (non-blocking)
        try:
            from agents.tools.assessment_tools import save_assessment_attempt  # noqa: PLC0415
            save_assessment_attempt(
                state.learner.learner_id,
                cert_ref,
                overall_score,
                domain_scores,
                weak_areas,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[assessment] Could not persist attempt (%s); continuing", exc)

        if passed:
            state.workflow_status = "passed"
            state.current_agent = "assessment"
            state.kb_activity = None
            ctx.set_state("workflow_state", state.model_dump())
            await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
            await _yield_text(
                ctx,
                f"Congratulations! You passed with {overall_score:.1f}%. Generating your certification advice...",
            )
            await ctx.send_message(AssessmentPassedMessage(state=state))
        elif state.can_retry:
            logger.info(
                "[assessment] FAIL score=%.1f — pausing for learner review; retry available (%d/%d)",
                overall_score,
                state.retry_count + 1,
                state.max_retries,
            )
            state.workflow_status = "exam_failed"
            state.assessment_answers = None
            state.assessment_questions = []
            state.current_agent = "assessment"
            state.kb_activity = None
            ctx.set_state("workflow_state", state.model_dump())
            await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
            await _yield_text(
                ctx,
                f"Score: {overall_score:.1f}%. Weak areas: {', '.join(weak_areas) or 'none identified'}. "
                "Review your results below. Send any message when ready to retry.",
            )
            # Run ends here — SeedExecutor routes to curator on next run when status == "exam_failed"
        else:
            state.workflow_status = "max_retries_reached"
            state.current_agent = "assessment"
            state.kb_activity = None
            ctx.set_state("workflow_state", state.model_dump())
            await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
            await _yield_text(
                ctx,
                f"Score: {overall_score:.1f}%. Maximum retries reached. "
                "Please contact your learning administrator for further guidance.",
            )


# ---------------------------------------------------------------------------
# Executor: ManagerExecutor (separate branch)
# ---------------------------------------------------------------------------


class ManagerExecutor(Executor):
    """Runs the ManagerInsightsAgent and yields the report as workflow output."""

    def __init__(self) -> None:
        super().__init__(id="manager")
        from agents.manager import create_manager_insights_agent  # noqa: PLC0415

        self._agent: Agent = create_manager_insights_agent(_build_client())

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[None, str]) -> None:
        logger.info("[manager] Generating team insights for: %s", message)
        try:
            result = await self._agent.run(messages=message)  # type: ignore[arg-type]
            output = str(result) if result else "No insights generated."
        except Exception as exc:
            logger.warning("[manager] Agent call failed (%s); using fallback", exc)
            output = f"Manager insights unavailable: {exc}"
        await ctx.yield_output(output)


# ---------------------------------------------------------------------------
# Executor: CertificationAdvisorExecutor
# ---------------------------------------------------------------------------


class CertificationAdvisorExecutor(Executor):
    """Runs the CertificationAdvisorAgent after a learner passes the assessment.

    Receives AssessmentPassedMessage, generates personalised post-pass advice
    (feedback, official cert URL, next cert, reinforcement schedule), emits
    the advice as a chat message, and ends the run with status="passed".
    """

    def __init__(self) -> None:
        super().__init__(id="certification_advisor")
        from agents.advisor import create_certification_advisor_agent  # noqa: PLC0415

        self._advisor = create_certification_advisor_agent(_build_client())

    @handler
    async def handle(
        self,
        message: AssessmentPassedMessage,
        ctx: WorkflowContext,
    ) -> None:
        state = message.state
        latest = state.assessment_results[-1] if state.assessment_results else None

        score = latest.score if latest else 0.0
        weak_areas = latest.weak_areas if latest else []

        logger.info(
            "[advisor] Generating post-pass advice for learner=%s score=%.1f",
            state.learner.learner_id,
            score,
        )

        cert_id = state.recommended_cert_id or "AZ-900"
        with trace_agent_invocation("certification_advisor", state.learner.learner_id):
            advice = await self._advisor.generate(
                score=score,
                weak_areas=weak_areas,
                learner_role=state.learner.role,
                recommended_cert_id=cert_id,
            )

        state.workflow_status = "passed"
        state.current_agent = "certification_advisor"
        state.kb_activity = None
        ctx.set_state("workflow_state", state.model_dump())
        await ctx.yield_output(StateSnapshotEvent(snapshot=state.model_dump()))
        await _yield_text(ctx, advice)
        # Run ends here — no further routing needed


# ---------------------------------------------------------------------------
# Workflow factories
# ---------------------------------------------------------------------------


def build_learner_workflow() -> Any:
    """Build and return the learner pipeline MAF Workflow.

    The graph is: seed -> curator -> study_plan -> engagement -> hitl_gate
    HITL NO branch: hitl_gate -> engagement (loop, max 3)
    HITL YES branch: hitl_gate -> assessment
    Assessment FAIL+retry: assessment -> curator (loop)

    SeedExecutor is the start_executor so it receives the list[Message] that
    agent_framework_ag_ui passes as the seed and converts it to LearnerMessage.

    Returns:
        A compiled agent_framework.Workflow instance.
    """
    seed = SeedExecutor()
    curator = CuratorExecutor()
    study_plan = StudyPlanExecutor()
    engagement = EngagementExecutor()
    hitl_gate = HITLGateExecutor()
    assessment = AssessmentExecutor()
    advisor = CertificationAdvisorExecutor()

    workflow = (
        WorkflowBuilder(
            name="learner-pipeline",
            description="Enterprise learning pipeline with state-based HITL gate and retry loop",
            start_executor=seed,
        )
        .add_chain([seed, curator, study_plan, engagement, hitl_gate])
        # seed->curator already covered by add_chain.
        # Path confirmation: seed sends PathConfirmedMessage -> curator.handle_path_confirmed
        # -> LearnerMessage -> study_plan (via chain). No bypass edge needed.
        # State-based HITL resume: seed sends HITLConfirmedMessage -> assessment
        # AssessmentAnswersMessage also routes seed -> assessment (MAF dispatches by handler type)
        .add_edge(seed, assessment)
        # Assessment PASS path: assessment -> advisor
        .add_edge(assessment, advisor)
        # Assessment FAIL+retry path: assessment -> curator
        .add_edge(assessment, curator)
        .build()
    )
    return workflow


def build_manager_workflow() -> Any:
    """Build and return the manager insights MAF Workflow.

    ManagerSeedExecutor is the start_executor so it receives list[Message] from
    the AG-UI adapter and extracts the last user text to pass to ManagerExecutor.

    Returns:
        A compiled agent_framework.Workflow instance.
    """
    manager_seed = ManagerSeedExecutor()
    manager = ManagerExecutor()

    workflow = (
        WorkflowBuilder(
            name="manager-insights",
            description="Manager team insights workflow",
            start_executor=manager_seed,
        )
        .add_chain([manager_seed, manager])
        .build()
    )
    return workflow
