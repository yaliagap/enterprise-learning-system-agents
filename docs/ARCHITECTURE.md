# System Architecture — Enterprise Learning System

> AI-powered, multi-agent certification learning platform built on **Azure AI Foundry**.
> Hackathon project: *Reasoning – Enterprise Learning System*

**🌐 Live Demo:** https://enterprise-learning-frontend.mangosmoke-abb8c649.northcentralus.azurecontainerapps.io

→ For a visual overview, see [`DIAGRAM.md`](DIAGRAM.md) — high-level architecture flowchart (renders in GitHub).

---

## Overview

The Enterprise Learning System automates the complete certification learning journey for enterprise employees — from initial skill-gap assessment to adaptive study planning, engagement nudges, grounded knowledge testing, and personalized post-assessment coaching. Every stage is handled by a specialized AI agent that reasons over enterprise data, grounded knowledge, and learner history.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Azure AI Foundry                                   │
│                                                                             │
│   ┌──────────┐  AG-UI/SSE  ┌─────────────────────────────────────────┐    │
│   │          │◄────────────►│         MAF Workflow Engine              │    │
│   │ Next.js  │             │  ┌──────────────────────────────────┐   │    │
│   │ Frontend │             │  │         WorkflowState            │   │    │
│   │          │             │  │  (Pydantic v2 — shared mutable)  │   │    │
│   └──────────┘             │  └──────────┬───────────────────────┘   │    │
│                            │             │ AG-UI STATE_SNAPSHOT       │    │
│                            │  ┌──────────▼───────────────────────┐   │    │
│                            │  │    5 Specialized AI Agents       │   │    │
│                            │  │  Curator · StudyPlan · Engage    │   │    │
│                            │  │  Assessment · Advisor            │   │    │
│                            │  └──────────┬───────────────────────┘   │    │
│                            └─────────────┼───────────────────────────┘    │
│                                          │                                  │
│   ┌──────────────────────────────────────▼──────────────────────────────┐  │
│   │                      Azure Services Layer                           │  │
│   │                                                                     │  │
│   │  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │  │
│   │  │  Azure OpenAI   │  │  Azure AI Search │  │    MS Learn MCP  │  │  │
│   │  │   (GPT-4o)      │  │  (Foundry IQ KB) │  │   (grounding)    │  │  │
│   │  └─────────────────┘  └──────────────────┘  └──────────────────┘  │  │
│   │                                                                     │  │
│   │  ┌─────────────────┐  ┌──────────────────┐                        │  │
│   │  │   Fabric IQ     │  │    Work IQ       │                        │  │
│   │  │ (learner data)  │  │ (engagement sig) │                        │  │
│   │  └─────────────────┘  └──────────────────┘                        │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **Frontend** | Next.js 15, TypeScript, Tailwind CSS | Multi-tab agentic UI with real-time SSE streaming |
| **Frontend Hosting** | Azure Container Apps | Containerized Next.js with Edge Runtime proxy; scales to zero when idle |
| **Backend** | FastAPI, Python 3.11+, Pydantic v2 | API server + workflow orchestration |
| **Backend Hosting** | Azure AI Foundry Hosted Agent | Managed compute, Entra ID identity, built-in observability |
| **Agent Framework** | MAF (Microsoft Agent Framework) | Agent execution, tool dispatch, executor routing |
| **Protocol** | AG-UI (open standard) over SSE | Real-time agent ↔ UI communication |
| **LLM** | GPT-4o via Azure OpenAI | Reasoning core for all agents |
| **Knowledge Base** | Azure AI Search + Foundry IQ | Enterprise KB with agentic (answer synthesis) mode |
| **Grounding** | MS Learn MCP (streamable HTTP) | Microsoft documentation grounding for assessment/curation |
| **Learner Data** | Fabric IQ (fixture-backed) | Learner profiles, history, performance records |
| **Engagement Signals** | Work IQ (fixture-backed) | Focus patterns, channel preferences, availability |
| **State** | Pydantic `WorkflowState` | Single source of truth for all agents, serialized on every SSE tick |
| **Backend Deploy** | Azure Developer CLI (`azd`) | One-command deploy of Foundry Hosted Agent |
| **Frontend Deploy** | `az acr build` + `az containerapp` | Multi-stage Docker build → ACR → Container Apps |

---

## Key Design Decisions

### 1. AG-UI Protocol for Real-Time Streaming
The frontend receives `STATE_SNAPSHOT` events on every significant agent action. This means the UI renders progressively as agents execute — no polling, no refresh. Each agent step updates `WorkflowState` and broadcasts it over SSE, so tabs unlock and content appears as it's computed.

### 2. WorkflowState as the Single Source of Truth
All agents read from and write to a shared `WorkflowState` (Pydantic v2). The dispatcher threads this state through every executor. The frontend reflects this state directly — there is no secondary client state store. This makes the system deterministic and debuggable.

### 3. HITL (Human-in-the-Loop) Gates
Two explicit HITL moments exist in the workflow:
- **Certification selection**: the learner chooses from Curator's ranked options before Run 2 begins
- **Path confirmation**: the learner reviews the curated learning path before assessment scheduling

These gates keep the human in control of the most consequential decisions while agents handle the research and generation.

### 4. Grounded Generation over Pure Generation
Every agent that produces structured output grounds its responses:
- **Curator**: Azure AI Search KB + MS Learn MCP
- **Assessment**: MS Learn MCP + learner performance history
- **Advisor**: enterprise team benchmark (Function Tool) + qualitative team KB docs

Grounding is observable — the KB query, response text, and source references are surfaced in the chat UI as a "Foundry IQ" panel.

### 5. Deterministic Computation + LLM Narrative
Where precision matters, computation is done in Python and handed to the LLM as context:
- Study plan sessions are scheduled deterministically; the LLM only writes the narrative summary
- Assessment question counts per domain use the largest-remainder algorithm for exact proportional allocation
- Team benchmark percentile is computed in Python; the LLM reads the result, not the raw distribution
- Advisor's Bloom/scenario gap analysis is precomputed; the LLM produces structured JSON from structured inputs

### 6. Pydantic Validation on Every LLM Output
All agents produce typed output validated against Pydantic v2 models. On failure:
- Assessment agent: one corrective retry with the validation error + cert/learner context injected
- Advisor agent: one corrective retry, then a deterministic fallback that never surfaces errors to the user

---

## Project Structure

```
Proyecto/
├── backend/
│   ├── agents/                     # One Python module per agent
│   │   ├── curator.py              # Two-run cert recommendation + path curation
│   │   ├── study_plan.py           # Deterministic schedule + LLM narrative
│   │   ├── engagement.py           # Work IQ signals → engagement proposal
│   │   ├── assessment.py           # Grounded question generation (15 Qs, validated)
│   │   ├── advisor.py              # Structured AdvisorResult + team benchmark analysis
│   │   └── tools/
│   │       ├── advisor_tools.py    # get_team_benchmark @tool + percentile_rank
│   │       ├── work_iq_tools.py    # Engagement + schedule preference tools
│   │       ├── fabric_iq_tools.py  # Learner profile tool
│   │       ├── foundry_iq_tools.py # KB search tool
│   │       └── mslearn_catalog_tools.py  # MS Learn catalog tools
│   ├── workflow/
│   │   ├── state.py                # WorkflowState + all Pydantic models
│   │   └── dispatcher.py           # MAF executors + state machine
│   ├── grounding/
│   │   ├── base.py                 # Abstract grounding interfaces
│   │   └── mock/                   # Fixture-based mock implementations
│   ├── data/
│   │   ├── fixtures/               # Learner profiles, certs, Work IQ, benchmarks
│   │   └── kb_documents/           # Knowledge base documents (exam QA, team insights)
│   └── api/
│       └── server.py               # FastAPI app + AG-UI endpoint
├── frontend/
│   ├── app/
│   │   ├── page.tsx                # Main orchestration component (5-tab workflow UI)
│   │   ├── hooks/
│   │   │   └── useAgentChat.ts     # AG-UI client hook (SSE event handlers)
│   │   └── lib/
│   │       ├── assessment-types.ts
│   │       └── advisor-types.ts
│   └── components/
│       ├── AdvisorView.tsx          # Structured advisor result component
│       ├── AssessmentResults.tsx    # Per-question breakdown component
│       ├── ExamInterface.tsx        # 15-question exam UI
│       └── EngagementProposalView.tsx
├── docs/
│   ├── ARCHITECTURE.md             # This document
│   ├── AGENTS.md                   # Per-agent deep dive
│   └── WORKFLOW.md                 # Sequence diagram + state machine
└── infra/                          # Azure bicep + azd configuration
```

---

## State Machine Summary

```
planning
  └─► awaiting_cert_selection     (Curator Run 1 complete — learner chooses cert)
        └─► awaiting_path_confirmation  (Curator Run 2 complete — learner reviews path)
              └─► studying              (path confirmed — study plan generating)
                    └─► awaiting_engagement   (study plan ready — engagement scheduling)
                          └─► assessing        (engagement confirmed — generating assessment)
                                └─► exam_in_progress  (15 questions ready)
                                      ├─► passed           → Advisor (celebratory)
                                      ├─► exam_failed       → assessing (retry, max 1)
                                      └─► max_retries_reached → Advisor (constructive)
```
