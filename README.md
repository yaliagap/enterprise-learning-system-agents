# Enterprise Learning System

> **Reasoning – Enterprise Learning System**  
> AI-powered, multi-agent certification learning platform built on **Azure AI Foundry** for the Microsoft Agents Hackathon.

An enterprise platform that automates the complete certification learning journey — from skill-gap analysis and adaptive learning path curation to personalized study scheduling, engagement nudges, grounded knowledge assessment, and structured post-assessment coaching. Every stage is handled by a specialized AI agent reasoning over enterprise data, grounded knowledge, and learner history.

> **⚠️ All data in this project is synthetic. No real customer, employee, or organizational data is used.**

---

## Key Highlights

- **5 specialized AI agents** coordinated by a MAF workflow dispatcher
- **AG-UI protocol** (SSE streaming) — UI updates in real time as agents execute
- **Azure AI Foundry** — hosted agents with GPT-4o, Azure AI Search (Foundry IQ KB), MS Learn MCP
- **HITL gates** — learner controls two pivotal decisions before agents proceed
- **Grounding observable** — every KB query, response, and source citation surfaces in the chat UI
- **Deterministic + LLM hybrid** — computation-heavy steps (scheduling, scoring, percentile ranking) done in Python; LLM handles language and judgment

---

## Agent Pipeline

```
Learner Input
     │
     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    MAF Dispatcher (SeedExecutor)                     │
│              Routes messages → typed Executor via state machine      │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │         Learning Path Curator        │  Tab 1
          │  Run 1: KB + learner profile →       │
          │         ranked cert options (HITL)   │
          │  Run 2: MS Learn MCP + KB →          │
          │         curated path + domain map    │
          └──────────────────┬──────────────────┘
                             │ path confirmed (HITL)
          ┌──────────────────▼──────────────────┐
          │         Study Plan Generator         │  Tab 2
          │  Work IQ signals → deterministic     │
          │  schedule + LLM narrative            │
          └──────────────────┬──────────────────┘
          ┌──────────────────▼──────────────────┐
          │          Engagement Agent            │  Tab 3
          │  Work IQ → 4 personalized alerts    │
          │  (reminder/milestone/motivation/risk)│
          └──────────────────┬──────────────────┘
                             │ engagement confirmed
          ┌──────────────────▼──────────────────┐
          │          Assessment Agent            │  Tab 4
          │  MS Learn MCP + KB → 15 grounded    │
          │  questions (Bloom-tagged, validated) │
          └──────────────────┬──────────────────┘
                             │ pass / max_retries_reached
          ┌──────────────────▼──────────────────┐
          │        Certification Advisor         │  Tab 5
          │  Bloom gap analysis + team benchmark │
          │  → structured AdvisorResult JSON     │
          └─────────────────────────────────────┘
```

→ See [`docs/WORKFLOW.md`](docs/WORKFLOW.md) for the full Mermaid sequence diagram and state machine.  
→ See [`docs/AGENTS.md`](docs/AGENTS.md) for per-agent deep dives (tools, reasoning patterns, interesting details).  
→ See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system architecture and key design decisions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11+, Pydantic v2 |
| **Agent Framework** | MAF (Microsoft Agent Framework) |
| **Streaming Protocol** | AG-UI (open standard) over SSE |
| **LLM** | GPT-4o via Azure OpenAI |
| **Knowledge Base** | Azure AI Search (Foundry IQ, agentic mode) |
| **Grounding** | MS Learn MCP (streamable HTTP) |
| **Learner Data** | Fabric IQ (fixture-backed) |
| **Engagement Signals** | Work IQ (fixture-backed) |
| **Deployment** | Azure Developer CLI (`azd`) |

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Node.js | 18+ | |
| Azure CLI | latest | `az login` required for real Azure mode |
| Azure AI Foundry project | — | Required for `USE_REAL_IQ=true` |

For **mock mode** (all fixture-backed, no Azure required), only Python and Node.js are needed.

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/yaliagap/enterprise-learning-system-agents.git
cd enterprise-learning-system-agents
```

### 2. Install Python dependencies

```bash
pip install -e ".[dev]"
# or
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Minimum for mock mode: set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY
```

Backend variables (`.env`):

| Variable | Description | Required |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | **Yes** |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | **Yes** |
| `AZURE_OPENAI_DEPLOYMENT` | GPT-4o deployment name | **Yes** |
| `USE_REAL_IQ` | `true` to enable Azure AI Search + real IQ providers | No (default: `false`) |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint | Only if `USE_REAL_IQ=true` |
| `AZURE_SEARCH_API_KEY` | Azure AI Search API key | Only if `USE_REAL_IQ=true` |
| `FOUNDRY_IQ_KB_NAME` | Knowledge base name in Azure AI Search | Only if `USE_REAL_IQ=true` |
| `FOUNDRY_IQ_OUTPUT_MODE` | KB output mode (`extractive` or `generative`) | Only if `USE_REAL_IQ=true` |

Frontend variables (`frontend/.env.local`, copy from `frontend/env.local.example`):

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_AGENT_URL` | Backend AG-UI endpoint (default: `http://localhost:8000/api/learn`) |

### 4. Start the backend

```bash
cd backend
uvicorn api.server:app --reload
# Running at http://localhost:8000
# AG-UI SSE endpoint: POST http://localhost:8000/api/learn
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Running at http://localhost:3000
```

---

## Demo Walkthrough

The full learner flow takes approximately **8–10 minutes** end-to-end.

### Step 1 — Login
Enter a learner ID (e.g. `EMP-001`) and click **Sign in**. The dashboard shows the learner's profile, role, and seniority.

### Step 2 — Select topics + start session
Click **+ Start new certification**, pick 2–4 interest topics (e.g. *Natural Language Processing*, *Generative AI*), and click **Start learning session**. The workflow kicks off automatically.

### Step 3 — Curator Agent (Tab 1)
Watch the **Curator Agent** analyze the learner's profile and query the Knowledge Base. The **Foundry IQ** panel in the chat shows the KB query, synthesized response, and source citations. A ranked list of 3–5 certification options appears — select one (e.g. **AI-102**).

The agent then builds a full learning path with MS Learn resources, estimated hours per module, and domain weights. Resources are flagged as *necessary* or *optional* based on the learner's existing skills.

### Step 4 — Study Plan Agent (Tab 2)
Click **Build my intelligent study plan**. The **Study Plan Generator** reads Work IQ signals (preferred days, session duration, focus peak hours) and produces a week-by-week schedule. The timeline calendar renders progressively via SSE.

### Step 5 — Engagement Agent (Tab 3)
The **Engagement Agent** generates 4 personalized nudge alerts calibrated to the learner's channel preferences (Slack/email), response rates, and meeting windows. Review the proposal and click **Confirm engagement plan**.

### Step 6 — Assessment Agent (Tab 4)
The agent generates **15 grounded assessment questions** — distributed proportionally across exam domains, tagged with Bloom's taxonomy levels, and grounded in official MS Learn content. The KB consultation panel appears in the chat. Complete the exam and submit.

- **Pass (≥70%)** → Advisor tab unlocks automatically
- **Fail** → Retry button appears (max 1 retry)
- **Fail twice** → Advisor tab unlocks with constructive analysis

### Step 7 — Certification Advisor (Tab 5)
The **Advisor Agent** delivers a structured analysis:
- Score ring (green = pass / red = max retries reached)
- Team percentile bar (your score vs. 20-engineer team cohort)
- Domain cards with pattern badges (`conceptual_gap` / `bloom_gap` / `scenario_gap`)
- Retry comparison (if second attempt)
- Prioritized recommendations with MS Learn resource hints
- Closing note (celebratory or constructive tone)

Click **Finalize track** to return to the dashboard.

---

## Project Structure

```
├── backend/
│   ├── agents/                  # One module per agent
│   │   ├── curator.py           # Two-run cert recommendation + path curation
│   │   ├── study_plan.py        # Deterministic schedule + LLM narrative
│   │   ├── engagement.py        # Work IQ signals → engagement proposal
│   │   ├── assessment.py        # Grounded 15-question generation + validation
│   │   ├── advisor.py           # Structured AdvisorResult + team benchmark analysis
│   │   └── tools/               # @tool functions (advisor, work_iq, fabric_iq, mslearn)
│   ├── workflow/
│   │   ├── state.py             # WorkflowState + all Pydantic models
│   │   └── dispatcher.py        # MAF executors + state machine
│   ├── grounding/               # Abstract IQ provider ports + mock implementations
│   ├── data/
│   │   ├── fixtures/            # Learner profiles, cert catalog, Work IQ, team benchmarks
│   │   └── kb_documents/        # KB source documents (exam QA, team insights per cert)
│   └── api/server.py            # FastAPI app + AG-UI SSE endpoint
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Main 5-tab workflow orchestration component
│   │   ├── hooks/useAgentChat.ts # AG-UI SSE client hook
│   │   └── lib/                 # TypeScript type definitions
│   └── components/              # AdvisorView, AssessmentResults, ExamInterface, ...
├── docs/
│   ├── ARCHITECTURE.md          # System architecture + design decisions
│   ├── AGENTS.md                # Per-agent catalog (tools, reasoning, details)
│   └── WORKFLOW.md              # Mermaid sequence diagram + state machine
└── infra/                       # Azure bicep + azd configuration
```

---

## Responsible AI

| Concern | Mitigation |
|---|---|
| **Hallucinated certifications** | Curator validates all cert IDs against `certification_catalog.json` — unlisted certs are rejected |
| **PII in advisor output** | `_scrub_result()` applies regex-based redaction on all free-text fields before storage |
| **Over-scheduling** | Study Plan Generator never exceeds the learner's declared weekly capacity |
| **Assessment integrity** | `correct_answers` are stripped from the public `AssessmentQuestionPublic` projection sent to the frontend — server-side grading only |
| **Learner agency** | Two HITL gates (cert selection, path confirmation) ensure the learner controls key decisions |
| **No hardcoded secrets** | All keys and credentials read from environment variables at runtime |

---

## Hackathon Context

**Event**: Microsoft Agents Hackathon  
**Title**: Reasoning – Enterprise Learning System  
**Tagline**: *From skill gap to certified — one AI-powered journey*  
**Stack**: Python 3.11 · FastAPI · Microsoft Agent Framework (MAF) · AG-UI SSE · Azure AI Foundry · Azure OpenAI (GPT-4o) · Azure AI Search · MS Learn MCP · Next.js 15 · Tailwind CSS  

> **⚠️ All data in this project is synthetic. No real customer, employee, or organizational data is used.**
