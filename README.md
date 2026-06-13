# Enterprise Learning System

An AI-powered learning and certification platform that orchestrates a multi-agent pipeline to build personalized study plans, deliver adaptive assessments, and surface team readiness insights — built for the **Agents League / Microsoft Hackathon**.

> **⚠️ All data in this project is synthetic. No real customer, employee, or organizational data is used.**

---

## Overview

The system uses **5 specialized AI agents** coordinated through a **Microsoft Agent Framework (MAF)** workflow dispatcher. A **Next.js 14 + CopilotKit** frontend streams the pipeline results to the learner via the **AG-UI protocol** (Server-Sent Events).

### Agent Pipeline

```
Learner Input
     │
     ▼
┌─────────────────────┐
│  Dispatcher (MAF)   │  ← Workflow orchestrator; emits RUN_STARTED / RUN_FINISHED
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Learning Path      │  ← Curator: role-aware cert matching via Foundry IQ + Fabric IQ
│  Curator            │    Output: LearningPath (ranked cert list)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Study Plan         │  ← Generator: time-boxed schedule via Work IQ availability
│  Generator          │    Streams: STATE_DELTA per session
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Engagement Agent   │  ← Nudges, streaks, next-best-action via Fabric IQ progress signals
└─────────┬───────────┘
          │
          ▼
     [HITL Gate]          ← Learner must confirm "Yes, I'm ready" before assessment
          │
          ▼
┌─────────────────────┐
│  Assessment Agent   │  ← Exam generation + chain-of-thought grading via Foundry IQ
└─────────────────────┘

                           (independent branch)
┌─────────────────────┐
│  Manager Insights   │  ← Team readiness dashboard via Fabric IQ (generative-UI)
│  Agent              │
└─────────────────────┘
```

### IQ Grounding Layers

| Layer | Mock Provider | Real Target (stub) |
|---|---|---|
| **Foundry IQ** | ChromaDB + SentenceTransformer (in-process) | Azure AI Search |
| **Fabric IQ** | JSON fixtures (learner_profiles, team_aggregates) | Microsoft Fabric REST |
| **Work IQ** | JSON fixtures (calendar_signals) | Microsoft Graph Calendar |

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker + Docker Compose | any recent |
| Azure CLI | latest (`az login` required for real IQ only) |
| Azure AI Foundry project | required for `USE_REAL_IQ=true` only |

For the default **mock mode** (all fixture-backed), only Python and Node are required. Docker is needed only for the Aspire Dashboard (optional for local dev).

---

## Quick Start

### 1. Clone the repository

```bash
git clone <repo-url>
cd enterprise-learning-system
```

### 2. Install Python dependencies

```bash
pip install -e ".[dev]"
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env — see the Environment Variables table below.
# Minimum required for mock mode: OPENAI_API_KEY
```

### 4. Start the Aspire Dashboard (optional — for OTel traces)

```bash
docker compose up -d
# Dashboard UI: http://localhost:18888
# OTLP endpoint: localhost:4317
```

### 5. Start the backend

```bash
cd backend
uvicorn api.server:app --reload
# API: http://localhost:8000
# AG-UI SSE endpoint: http://localhost:8000/api/learn
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
# App: http://localhost:3000
```

### 7. Open the app

Navigate to **http://localhost:3000** in your browser.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values.

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for the LLM backbone | **Yes** |
| `USE_REAL_IQ` | Set to `true` to enable real Azure IQ providers | No (default: `false`) |
| `AZURE_FOUNDRY_ENDPOINT` | Azure AI Foundry project endpoint URL | Only if `USE_REAL_IQ=true` |
| `AZURE_FOUNDRY_API_KEY` | Azure AI Foundry API key | Only if `USE_REAL_IQ=true` |
| `CHROMA_DB_PATH` | Persistent ChromaDB path (omit for in-memory) | No |
| `OTLP_ENDPOINT` | OTLP gRPC endpoint for traces | No (default: `http://localhost:4317`) |
| `BACKEND_URL` | Backend URL used by the frontend CopilotKit runtime | No (default: `http://localhost:8000`) |

Frontend environment variables go in `frontend/.env.local` (copy from `frontend/env.local.example`):

| Variable | Description | Required |
|---|---|---|
| `NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL` | CopilotKit runtime URL (usually `/api/copilotkit`) | **Yes** |
| `OPENAI_API_KEY` | OpenAI key used by the CopilotKit Next.js runtime | **Yes** |
| `BACKEND_URL` | FastAPI backend base URL | No (default: `http://localhost:8000`) |

---

## Running Tests

Tests live in `backend/tests/` and use `pytest`. Run from the `backend/` directory:

```bash
cd backend
pytest tests/ -v
```

The test suite covers:

- **`tests/test_grounding.py`** — IQ provider smoke tests (MockFoundryIQ, MockFabricIQ, MockWorkIQ)
- **`tests/test_tools.py`** — MAF tool function smoke tests (search, profile, question generation, scoring)
- **`tests/test_workflow_state.py`** — WorkflowState lifecycle, retry logic, HITL guard

No external services or API keys are required to run tests (mock mode only).

---

## Demo Script

Follow these steps to walk judges through the full system in approximately 5 minutes.

### Learner Flow

1. Open **http://localhost:3000**
2. Enter learner ID **`EMP-001`** and select certification **AZ-204** from the dropdown
3. Click **Start Learning Path**
4. Watch the CopilotKit sidebar and main panel stream in real time:
   - **Curator agent** generates a ranked learning path → `LearningPathCard` components appear
   - **Study Plan agent** builds a time-boxed schedule → `StudyPlanTimeline` fills progressively
   - **Engagement agent** generates nudges and streak messaging
5. The **HITL gate** triggers: a full-screen confirmation overlay appears
   - Click **"Yes, I'm ready"** to proceed to assessment
   - (Clicking "Not yet" delivers the partial plan and ends the workflow gracefully)
6. The **Assessment agent** streams 5 practice questions with chain-of-thought grading
   - Answer each question using the radio options in `AssessmentPanel`
   - Watch the `ReadinessGauge` update after each submission
7. The final result screen shows: overall score, pass/fail, weak areas, next certification recommendation

### Aspire Dashboard (OTel Traces)

1. Open **http://localhost:18888**
2. Click on the most recent trace
3. Verify the trace tree shows child spans for all 5 agents plus IQ calls
4. Observe the temporal gap between the Engagement and Assessment spans — this is the HITL pause

### Manager Flow

1. Click **Manager View** in the navigation (or navigate to **http://localhost:3000/manager**)
2. Enter team ID **`TEAM-A`** and click **Load Team**
3. The generative-UI dashboard renders:
   - Team average readiness gauge
   - At-risk member count
   - `TeamRiskTable` with per-member status, hours studied, and readiness score

---

## Architecture Notes

### AG-UI Protocol

The backend exposes a single SSE endpoint (`POST /api/learn`) using `add_agent_framework_fastapi_endpoint`. The frontend binds to it via CopilotKit's `useCoAgent` hook. State updates flow as `STATE_DELTA` events; the HITL gate uses CopilotKit's `renderAndWaitForResponse` pattern.

### Port-Adapter Pattern (IQ Providers)

All grounding is behind abstract ports (`grounding/base.py`). Mock providers are the default. Real Azure provider stubs are wired behind `USE_REAL_IQ=true`. Swapping providers requires no changes outside `grounding/`.

### OTel Instrumentation

Every agent invocation and every IQ provider call is wrapped in an OpenTelemetry span. The `configure_otel_providers()` function at startup wires an OTLP exporter to the Aspire Dashboard collector.

---

## Responsible AI

- **Catalog grounding**: The Learning Path Curator filters out any cert ID not present in `certification_catalog.json`, preventing hallucinated certifications from reaching the learner.
- **Over-scheduling guard**: The Study Plan Generator never schedules more daily hours than the learner's declared availability.
- **HITL gate**: The Assessment Agent is blocked by `AssessmentNotConfirmedError` until the learner explicitly confirms readiness.
- **PII scope**: The Manager Insights Agent is constrained to `team_aggregates.json` scope — no individual names or identifiers outside that fixture are exposed.
- **Assessment approval mode**: The Assessment Agent runs with `approval_mode="always_require"`, ensuring every grading step is surfaced to the learner.
- **No hardcoded secrets**: All API keys and credentials are read from environment variables at startup.

---

## Hackathon Context

**Event**: Agents League — Microsoft Hackathon  
**Challenge**: Enterprise AI Agents with Microsoft Agent Framework + AG-UI  
**Stack**: Python 3.11 · FastAPI · Microsoft Agent Framework (MAF) · AG-UI SSE · Next.js 14 · CopilotKit · ChromaDB · OpenTelemetry · Aspire Dashboard  

> **⚠️ All data in this project is synthetic. No real customer, employee, or organizational data is used.**
