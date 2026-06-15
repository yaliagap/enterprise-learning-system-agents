# Enterprise Learning System

> **Reasoning – Enterprise Learning System**  
> AI-powered, multi-agent certification learning platform built on **Azure AI Foundry** for the Microsoft Agents Hackathon.

An enterprise platform that automates the complete certification learning journey — from skill-gap analysis and adaptive learning path curation to personalized study scheduling, engagement nudges, grounded knowledge assessment, and structured post-assessment coaching. Every stage is handled by a specialized AI agent reasoning over enterprise data, grounded knowledge, and learner history.

> **⚠️ All data in this project is synthetic. No real customer, employee, or organizational data is used.**

**🌐 Live Demo:** https://enterprise-learning-frontend.mangosmoke-abb8c649.northcentralus.azurecontainerapps.io  
**🎬 Demo Video:** https://youtu.be/rQMbDs-XAU0

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

→ See [`docs/DIAGRAM.md`](docs/DIAGRAM.md) for the high-level architecture diagram (Mermaid flowchart).  
→ See [`docs/WORKFLOW.md`](docs/WORKFLOW.md) for the full Mermaid sequence diagram and state machine.  
→ See [`docs/AGENTS.md`](docs/AGENTS.md) for per-agent deep dives (tools, reasoning patterns, interesting details).  
→ See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system architecture and key design decisions.  
→ See [`docs/DATA.md`](docs/DATA.md) for the synthetic data catalog (fixtures, KB documents, and narrative reports).

---

## Azure AI Foundry — Hosted Agents

Every agent in this system runs as a **Foundry-hosted agent** on Azure AI Foundry. This means each agent is a stateless, independently deployable unit managed by the Foundry runtime — not a standalone process or a long-running service.

```
Azure AI Foundry Project
├── Agent: Learning Path Curator       (model: gpt-4o, tools: KB MCP + MS Learn MCP + Fabric IQ)
├── Agent: Study Plan Generator        (model: gpt-4o, tools: Work IQ + schedule closure)
├── Agent: Engagement Agent            (model: gpt-4o, tools: Work IQ)
├── Agent: Assessment Agent            (model: gpt-4o, tools: MS Learn MCP + KB MCP)
└── Agent: Certification Advisor       (model: gpt-4o, tools: team_benchmark + KB MCP)
```

Each agent is defined with:
- A **system prompt** scoped to its specific role and output contract
- A set of **registered tools** (Function Tools and MCPStreamableTools)
- A **response format** enforced via Pydantic — the agent is instructed to return structured JSON
- An **Azure OpenAI deployment** (GPT-4o) as its reasoning core

The **MAF Dispatcher** (`dispatcher.py`) orchestrates execution: on every incoming message, it reads `WorkflowState`, determines which `Executor` owns the current phase, instantiates the corresponding Foundry agent, and runs it. The agent's tool calls and responses are captured and written back to `WorkflowState` before the SSE snapshot is broadcast.

**KB as a Foundry MCPStreamableTool** — the enterprise knowledge base (Azure AI Search) is wired to the relevant agents as a `MCPStreamableTool`, enabling agentic (answer-synthesis) mode: the agent decides when to query, formulates its own query, and receives a synthesized answer with source references — not just raw search results.

---

## AG-UI Protocol

AG-UI is an **open standard protocol** for streaming agent state and messages from a backend agent to a frontend UI in real time. This project uses AG-UI over **Server-Sent Events (SSE)**.

### How it works

```
Backend (FastAPI)                           Frontend (Next.js)
─────────────────                           ──────────────────
POST /api/learn                             useAgentChat hook
  │                                           │
  ├── RunAgent(WorkflowState)                 ├── EventSource opens
  │     │                                     │
  │     ├── Agent executes tool calls         │
  │     ├── Agent streams text tokens         ├── TEXT_MESSAGE_CONTENT → chat bubble updates
  │     ├── WorkflowState mutated             │
  │     └── STATE_SNAPSHOT emitted ──────────►├── All tabs re-evaluate
  │                                           │     Tabs unlock based on state
  └── RUN_FINISHED emitted ─────────────────►└── isRunning = false
```

### Event types used

| Event | Payload | Effect |
|---|---|---|
| `STATE_SNAPSHOT` | Full `WorkflowState` JSON | Tabs unlock, content renders, agent label updates in UI |
| `TEXT_MESSAGE_START` | `messageId`, `role` | New chat bubble opens (streaming mode) |
| `TEXT_MESSAGE_CONTENT` | `delta` token | Bubble content appends live |
| `TEXT_MESSAGE_END` | `messageId` | Bubble finalized, KB panel attached if present |
| `TOOL_CALL_START` | `toolCallId`, `toolName` | Tool indicator shown |
| `TOOL_CALL_END` | `toolCallId` | Tool indicator removed |
| `RUN_FINISHED` | — | Controls re-enable, spinner stops |
| `RUN_ERROR` | `message` | Error shown in UI |

### Why AG-UI matters here

`STATE_SNAPSHOT` is the backbone of the entire UX. Every time an agent completes a meaningful step — returning cert options, finishing a study plan, producing an engagement proposal, delivering assessment questions, or generating the advisor result — it mutates `WorkflowState` and emits a `STATE_SNAPSHOT`. The frontend receives this snapshot and re-derives all display logic from it:

- Which of the 5 tabs is unlocked
- Which HITL controls are visible
- What content is rendered in each tab
- Which agent attribution label appears in the chat

This means **there is no separate client state store** — the frontend is a pure projection of `WorkflowState`. The `useAgentChat` hook in `frontend/app/hooks/useAgentChat.ts` handles all event parsing, message accumulation, and state hydration.

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

## Azure Deployment

The project ships as a **Foundry-hosted container agent** deployed via Azure Developer CLI (`azd`). A single `azd up` provisions all Azure resources and deploys the container.

### Deployment artifacts

#### `agent.yaml` — Foundry ContainerAgent definition

```yaml
kind: hosted
protocols:
  - protocol: invocations
    version: 1.0.0
code_configuration:
  runtime: python_3_13
  entry_point: backend/main.py
  dependency_resolution: remote_build
```

This is the schema that Foundry uses to register the agent. Key points:
- **`kind: hosted`** — the agent runs inside Foundry's managed container runtime, not on a custom VM
- **`protocol: invocations`** — activates the Foundry Invocations Protocol, which is the transport layer this project uses to bridge AG-UI events over Foundry's hosted infrastructure
- **`entry_point: backend/main.py`** — FastAPI app that exposes the `/api/learn` AG-UI SSE endpoint
- **`dependency_resolution: remote_build`** — Foundry builds the Python environment remotely from `pyproject.toml`, no pre-built image required in this mode

#### `agent.manifest.yaml` — parameterized template

The manifest version of `agent.yaml` uses `{{PLACEHOLDER}}` variables for all environment-specific values (`FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`, `AZURE_SEARCH_ENDPOINT`, etc.). This allows the same agent definition to be deployed across dev, staging, and prod without editing the file — values are injected at deploy time by AZD.

It also declares the GPT-4o model resource:
```yaml
resources:
  - kind: model
    id: gpt-4o
    name: FOUNDRY_MODEL
```

#### `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY backend/ ./backend/
RUN pip install --no-cache-dir --pre -e .
ENV PYTHONPATH=/app/backend
EXPOSE 8000
CMD ["python", "backend/main.py"]
```

The image omits `[local]` extras (ChromaDB, sentence-transformers) intentionally — in the container `USE_REAL_IQ=true`, so the system uses Azure AI Search for the knowledge base, not a local vector store.

#### `azure.yaml` — AZD entrypoint

```yaml
services:
  enterprise-learning-agent:
    host: azure.ai.agent
    language: docker
    docker:
      remoteBuild: true
infra:
  provider: bicep
  path: ./infra
```

- **`host: azure.ai.agent`** — tells AZD this is a Foundry agent host (not App Service, Container Apps, etc.)
- **`remoteBuild: true`** — the Docker image is built in Azure, not locally
- **`infra.provider: bicep`** — all Azure resources are declared in `infra/`

#### `infra/` — Bicep modules

```
infra/
├── main.bicep              # Subscription-scope entrypoint
├── main.parameters.json    # Environment parameters
└── core/
    ├── ai/                 # Azure AI Foundry project + AI Services account
    ├── host/               # Container host configuration
    ├── monitor/            # Application Insights + Log Analytics
    ├── search/             # Azure AI Search (Foundry IQ KB)
    └── storage/            # Storage account for artifacts
```

`main.bicep` deploys at subscription scope and provisions: Azure AI Foundry, Azure OpenAI (GPT-4o), Azure AI Search, Application Insights, and a storage account. Regions are restricted to locations where Azure AI Foundry Responses API is available.

### One-command deploy

```bash
# Login
az login
azd auth login

# Provision all Azure resources + deploy the container agent
azd up

# Environment variables are injected automatically from azure.yaml + infra outputs
```

After `azd up` completes, the Foundry hosted agent is live and the frontend can point `NEXT_PUBLIC_AGENT_URL` at the provisioned endpoint.

### Frontend — Azure Container Apps

The Next.js frontend is deployed separately as an Azure Container App using a multi-stage Docker build with `output: 'standalone'`.

**Build and push image to ACR:**

```bash
# Create ACR (first time only)
az acr create --name learningagentacr --resource-group <resource-group> --sku Basic --admin-enabled true

# Build image in Azure (no local Docker required)
az acr build --registry learningagentacr --image enterprise-learning-frontend:latest --file frontend/Dockerfile ./frontend
```

**Create Container Apps environment and deploy (first time):**

```bash
az containerapp env create \
  --name learning-agent-env \
  --resource-group <resource-group> \
  --location <location>

az containerapp create \
  --name enterprise-learning-frontend \
  --resource-group <resource-group> \
  --environment learning-agent-env \
  --image learningagentacr.azurecr.io/enterprise-learning-frontend:latest \
  --registry-server learningagentacr.azurecr.io \
  --target-port 3000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --cpu 0.5 --memory 1.0Gi \
  --env-vars FOUNDRY_AGENT_URL=<foundry-endpoint> \
  --secrets foundry-key=<foundry-api-key> \
  --env-vars FOUNDRY_API_KEY=secretref:foundry-key
```

**Redeploy after code changes:**

```bash
az acr build --registry learningagentacr --image enterprise-learning-frontend:latest --file frontend/Dockerfile ./frontend
az containerapp update --name enterprise-learning-frontend --resource-group <resource-group> --image learningagentacr.azurecr.io/enterprise-learning-frontend:latest
```

**Live deployment:** https://enterprise-learning-frontend.mangosmoke-abb8c649.northcentralus.azurecontainerapps.io

> `--min-replicas 0` scales to zero when idle — minimal cost for demo/hackathon usage.

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
