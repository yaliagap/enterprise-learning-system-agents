# Architecture Diagram — Enterprise Learning System

High-level view of the system: actors, layers, agents, and Azure services.

```mermaid
flowchart TD
    Learner(["👤 Learner"])

    subgraph Frontend["Next.js 15 Frontend"]
        UI["Multi-tab UI\n(5 agent tabs)"]
        Hook["useAgentChat hook\nAG-UI SSE client"]
    end

    subgraph Foundry["Azure AI Foundry — Hosted Agent"]
        GW["FastAPI Gateway\nPOST /api/learn"]
        MAF["MAF Dispatcher\nSeedExecutor — state machine"]

        subgraph Agents["Specialized AI Agents"]
            CUR["🗂 Curator\nLearning Path"]
            SPL["📅 Study Plan\nGenerator"]
            ENG["🔔 Engagement\nAgent"]
            ASS["📝 Assessment\nAgent"]
            ADV["🎯 Certification\nAdvisor"]
        end
    end

    subgraph AzureServices["Azure Services"]
        AOI["Azure OpenAI\nGPT-4o"]
        AIS["Azure AI Search\nFoundry IQ KB"]
        MSL["MS Learn MCP\nStreamable HTTP"]
    end

    subgraph EnterpriseData["Enterprise Data (fixture-backed)"]
        FIQ["Fabric IQ\nLearner profiles"]
        WIQ["Work IQ\nEngagement signals"]
        BMK["Team Benchmark\nJSON fixture"]
    end

    Learner -- "AG-UI SSE\n(topics, selections, answers)" --> UI
    UI <-- "STATE_SNAPSHOT\n+ text stream" --> Hook
    Hook -- "POST /api/learn" --> GW

    GW --> MAF
    MAF --> CUR
    MAF --> SPL
    MAF --> ENG
    MAF --> ASS
    MAF --> ADV

    CUR --> AOI
    SPL --> AOI
    ENG --> AOI
    ASS --> AOI
    ADV --> AOI

    CUR --> AIS
    ASS --> AIS
    ADV --> AIS

    CUR --> MSL
    ASS --> MSL

    CUR --> FIQ
    SPL --> WIQ
    ENG --> WIQ
    ADV --> BMK

    style Frontend fill:#1e3a5f,color:#fff,stroke:#3b82f6
    style Foundry fill:#1a2e1a,color:#fff,stroke:#22c55e
    style Agents fill:#2d1a2e,color:#fff,stroke:#a855f7
    style AzureServices fill:#1e2a3a,color:#fff,stroke:#60a5fa
    style EnterpriseData fill:#2a1e1e,color:#fff,stroke:#f87171
```

---

## Layer Summary

| Layer | What it does |
|---|---|
| **Next.js 15 Frontend** | Renders the 5-tab agentic UI; `useAgentChat` hook handles SSE event parsing and `WorkflowState` hydration |
| **FastAPI Gateway** | Receives AG-UI `POST /api/learn`, opens SSE stream, delegates to MAF |
| **MAF Dispatcher** | Routes each message to the correct `Executor` based on `WorkflowState.workflow_status` |
| **Specialized Agents** | Each agent owns one phase; runs as a Foundry-hosted agent with its own tools and system prompt |
| **Azure OpenAI (GPT-4o)** | Reasoning core for all 5 agents |
| **Azure AI Search** | Foundry IQ KB — enterprise knowledge base in agentic mode (answer synthesis + citations) |
| **MS Learn MCP** | Official Microsoft documentation grounding for Curator and Assessment agents |
| **Fabric IQ** | Learner profile data (role, seniority, skill gaps, completed certs) |
| **Work IQ** | Engagement signals (focus peak, channel preferences, availability, streak data) |
| **Team Benchmark** | Pre-computed JSON fixture with team score distributions and domain averages per cert |
