"""HITL validation harness — T-025.

Standalone script that validates the HITL gate in the learner pipeline
without requiring a frontend.

Usage:
    python scripts/test_hitl.py

What it does:
    1. Instantiates the dispatcher workflow with test learner L-1001 / AZ-204
       (mapped to fixture EMP-001 / AZ-204 which has matching profile data).
    2. Runs the pipeline until it reaches the HITL gate (request_info pause).
    3. Prints the workflow state at the HITL pause point.
    4. Simulates a "YES — ready to be assessed" confirmation.
    5. Resumes the workflow to completion.
    6. Prints the final WorkflowState and AssessmentResult.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure backend/ is on the Python path when running from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("test_hitl")

# Suppress noisy sub-module logs; keep just the dispatcher.
logging.getLogger("agent_framework").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


async def run_hitl_validation() -> None:
    """End-to-end HITL gate validation without a frontend."""
    from workflow.dispatcher import (
        HITLRequest,
        HITLResponse,
        LearnerMessage,
        build_learner_workflow,
    )
    from workflow.state import WorkflowState

    # ------------------------------------------------------------------
    # 1. Build the learner workflow
    # ------------------------------------------------------------------
    logger.info("Building learner workflow …")
    workflow = build_learner_workflow()
    logger.info("Workflow built: %s", workflow)

    # Seed message — use EMP-001 (existing fixture) and AZ-204.
    seed_state = WorkflowState.seed(
        learner_id="EMP-001",
        employee_id="EMP-001",
        target_cert_id="AZ-204",
        role="Cloud Engineer",
    )
    initial_message = LearnerMessage(state=seed_state)

    # ------------------------------------------------------------------
    # 2. Run until HITL gate
    # ------------------------------------------------------------------
    logger.info("Starting workflow run for EMP-001 / AZ-204 …")

    hitl_request_id: str | None = None
    hitl_request_data: HITLRequest | None = None
    events_before_hitl: list[str] = []

    event_stream = workflow.run(message=initial_message, stream=True)

    # Consume the entire stream — the workflow will naturally suspend after
    # emitting request_info and then emit IDLE_WITH_PENDING_REQUESTS status.
    async for event in event_stream:
        event_type = getattr(event, "type", "unknown")
        events_before_hitl.append(event_type)

        if event_type == "request_info":
            hitl_request_id = str(event.request_id)
            raw_data = event.data  # WorkflowEvent stores request_data in .data
            if isinstance(raw_data, HITLRequest):
                hitl_request_data = raw_data
            logger.info(
                "  *** HITL GATE REACHED — request_id=%s question=%r ***",
                hitl_request_id,
                raw_data.question if hasattr(raw_data, "question") else raw_data,
            )
            # Don't break — let the stream complete so the workflow reaches
            # IDLE_WITH_PENDING_REQUESTS state, which allows resume via responses.
        elif event_type == "status":
            state_val = getattr(event, "state", None)
            if state_val is not None:
                logger.info("  Status event: state=%s", state_val)
        else:
            logger.info("  Event: type=%s", event_type)

    # ------------------------------------------------------------------
    # 3. Print state at HITL pause point
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STATE AT HITL PAUSE POINT")
    print("=" * 60)

    if hitl_request_data:
        print(f"Question  : {hitl_request_data.question}")
        print(f"Learner   : {hitl_request_data.learner_id}")
        print(f"Attempt   : {hitl_request_data.attempt}")

    print(f"\nEvents emitted before pause: {events_before_hitl}")
    print("=" * 60 + "\n")

    if hitl_request_id is None:
        logger.warning(
            "HITL gate was NOT reached — the workflow completed without a request_info event.\n"
            "Possible reasons: agents skipped due to mock mode, or graph edges not wired.\n"
            "Events: %s",
            events_before_hitl,
        )
        print("\nWARNING: HITL gate not reached. Workflow may have completed without pausing.")
        print("This is expected when running in mock/stub mode without a real LLM key.")
        print("To fully test HITL, set OPENAI_API_KEY and USE_REAL_IQ=false.\n")
        return

    # ------------------------------------------------------------------
    # 4. Simulate "YES" confirmation
    # ------------------------------------------------------------------
    logger.info("Simulating 'YES — ready to be assessed' confirmation …")
    confirmation = HITLResponse(confirmed=True, learner_id="EMP-001")

    # ------------------------------------------------------------------
    # 5. Resume workflow with the confirmed response
    # ------------------------------------------------------------------
    logger.info("Resuming workflow after HITL confirmation (request_id=%s) …", hitl_request_id)

    final_state: WorkflowState | None = None
    resume_events: list[str] = []

    resume_stream = workflow.run(
        responses={hitl_request_id: confirmation},
        stream=True,
    )

    async for event in resume_stream:
        event_type = getattr(event, "type", "unknown")
        resume_events.append(event_type)
        logger.info("  Resume event: type=%s", event_type)

        if event_type == "output":
            data = getattr(event, "data", None)
            if isinstance(data, WorkflowState):
                final_state = data
                logger.info(
                    "  Final workflow status: %s", data.workflow_status
                )

    # ------------------------------------------------------------------
    # 6. Print final state and assessment result
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("FINAL WORKFLOW STATE")
    print("=" * 60)

    if final_state:
        print(f"Workflow status : {final_state.workflow_status}")
        print(f"HITL confirmed  : {final_state.hitl_confirmed}")
        print(f"Retry count     : {final_state.retry_count}")
        print(f"Learning path   : {len(final_state.learning_path)} items")
        print(f"Study plan      : {len(final_state.study_plan)} sessions")

        assessment = final_state.latest_assessment
        if assessment:
            print("\nASSESSMENT RESULT")
            print(f"  Attempt        : {assessment.attempt}")
            print(f"  Score          : {assessment.score:.1f}")
            print(f"  Passing score  : {assessment.passing_score:.1f}")
            print(f"  Passed         : {assessment.passed}")
            print(f"  Weak areas     : {assessment.weak_areas}")
            print(f"  Completed at   : {assessment.completed_at}")
        else:
            print("\nNo assessment result in final state.")
    else:
        print("No WorkflowState output found in resume stream.")
        print(f"Resume events: {resume_events}")

    print("=" * 60 + "\n")
    logger.info("HITL validation complete.")


def main() -> None:
    """Entry point for the HITL test harness."""
    asyncio.run(run_hitl_validation())


if __name__ == "__main__":
    main()
