# Agent Catalog — Enterprise Learning System

Five specialized agents collaborate in a sequential multi-agent workflow. Each agent owns a distinct phase of the learning journey, with clearly defined inputs, outputs, tools, and reasoning strategies.

---

## Agent 1 — Learning Path Curator

**File:** `backend/agents/curator.py`
**Executor:** `CuratorExecutor`

### Objective
Recommend the best certification for the learner and build a grounded, prioritized learning path tailored to their role, skill gaps, and seniority. Operates in two sequential runs separated by a HITL gate.

### Two-Run Architecture

**Run 1 — Certification Recommendation**
The agent analyzes the learner's profile and knowledge base to produce a ranked list of 3–5 certification options, each with a recommendation score and explanation.

| Tool | Source | Purpose |
|---|---|---|
| `get_learner_profile` | Fabric IQ | Retrieve learner role, seniority, skill gaps, completed certs, goals |
| `search_knowledge_base` | Foundry IQ (Azure AI Search, agentic mode) | Ground recommendations in enterprise-specific cert requirements |

Output: `cert_options: list[CertOption]` — triggers `awaiting_cert_selection` state.

**Run 2 — Learning Path Curation**
After the learner selects a certification, the agent builds a full learning path with prioritized resources, domain weights, and MS Learn references.

| Tool | Source | Purpose |
|---|---|---|
| `search_learning_paths` | MS Learn MCP | Find official learning paths for the selected cert |
| `get_learning_path` | MS Learn MCP | Fetch full learning path content |
| `get_module_details` | MS Learn MCP | Get module metadata and estimated hours |
| `search_azure_certifications` | MS Learn catalog | Verify exam domain weights |
| `get_certification_info` | MS Learn catalog | Fetch official cert metadata |
| KB MCPStreamableTool | Foundry IQ (Azure AI Search) | Ground path selection in enterprise KB |

Output: `CurationResult` — full learning path with `necessary_learn` flags, domain weights, and MS Learn URLs.

### Reasoning Pattern
**Grounded multi-run with HITL gate.** The first run is exploratory (KB + learner profile → options), the second is constructive (MS Learn + KB → curated path). The human decision in between anchors the second run to the learner's chosen direction.

The agent also applies an **autonomous learner profile tool** in Run 2 to mark resources as `necessary_learn: true/false` — filtering out content the learner has already mastered based on their strongest domains and completed certs.

### Interesting Details
- KB query, response text, and references are captured via `_KBCaptureMiddleware` and surfaced in the UI as a "Foundry IQ" panel — making grounding transparent.
- Run 2 uses both MS Learn MCP and the enterprise KB simultaneously, letting the agent cross-reference official Microsoft content with internal training data.
- The `CurationResult` schema includes `path_efficiency_reasoning` — the agent's explanation of why certain modules were marked as skip-worthy.

---

## Agent 2 — Study Plan Generator

**File:** `backend/agents/study_plan.py`
**Executor:** `StudyPlanExecutor`

### Objective
Build a weekly study schedule that fits the learner's real work availability, focus patterns, and capacity — then explain the prioritization decisions in plain language.

### Tools

| Tool | Source | Purpose |
|---|---|---|
| `get_learner_schedule_preferences` | Work IQ | Retrieve preferred study days, session duration, focus peak hours, weekly capacity |
| `compute_study_schedule` | Python (injected closure) | Deterministic session scheduler bound to the learner's learning path and domains |

### Reasoning Pattern
**LLM as narrative layer over deterministic computation.** The Python scheduler produces the complete session list (dates, hours, topics, resource IDs) algorithmically — the LLM reads the schedule context and writes only the `study_plan_reasoning` narrative (2–3 sentences explaining prioritization decisions). This guarantees schedule correctness while preserving natural language explanations.

The `compute_study_schedule` tool is not a static function — it is a **closure** created by the executor that closes over the learner's specific learning path and milestone data, injected as a tool at runtime.

### Interesting Details
- Work IQ signals drive scheduling: if a learner's `focusPeakStart` is 19:00, sessions are scheduled to start in the evening.
- The agent produces domain-level `StudyMilestone` objects alongside session-level `StudyPlanSession` objects, enabling progress tracking at both granularities.
- The `_ScheduleContextMiddleware` captures schedule preferences during tool calls and attaches them to the workflow state as `LearnerSchedulePreferences`.

---

## Agent 3 — Engagement Agent

**File:** `backend/agents/engagement.py`
**Executor:** `EngagementExecutor`

### Objective
Design a personalized engagement plan — exactly 4 nudge alerts (reminder, milestone, motivation, risk) — calibrated to the learner's communication channel preferences, focus patterns, and study rhythm.

### Tools

| Tool | Source | Purpose |
|---|---|---|
| `get_engagement_profile` | Work IQ | Get Work IQ signals: focusPeak, meetingWindow, responseRateByChannel, avgStreakDays |
| `get_study_availability` | Work IQ | Get schedule availability for timing decisions |
| `submit_engagement_proposal` | Internal | Validated JSON submission endpoint — enforces schema compliance |

### Reasoning Pattern
**Decision rules encoded in the prompt, LLM fills creative fields.** The system prompt specifies exact algorithms for channel selection, timing computation, and trigger conditions:
- Channel: compare `responseRateByChannel["slack"]` vs `["email"]` → pick higher rate
- Reminder timing: `focusPeakStart - 30min`, adjusted if it falls inside the meeting window
- Risk trigger: `min(48, max((avgStreakDays - 1) * 24, 24))` hours of inactivity

The LLM is responsible only for `previewText` (the notification copy) and `reasoning` (the rationale). All structural fields are computed deterministically.

### Interesting Details
- `submit_engagement_proposal` acts as a schema enforcement gate — the agent cannot complete without producing a valid `EngagementProposal`.
- The `milestone` alert is always email regardless of channel preferences — an explicit product decision (achievement notifications belong in the inbox as a record).
- The `EngagementProposalView` component in the frontend renders the proposal as an interactive card, allowing the learner to confirm or request adjustments before the session proceeds to assessment.

---

## Agent 4 — Assessment Agent

**File:** `backend/agents/assessment.py`
**Executor:** `AssessmentExecutor`

### Objective
Generate exactly 15 certification-specific assessment questions, grounded in official Microsoft documentation and adapted to the learner's history, Bloom's taxonomy levels, and exam domain weights.

### Tools

| Tool | Source | Purpose |
|---|---|---|
| MS Learn MCP (streamable HTTP) | `https://learn.microsoft.com/api/mcp` | Ground questions in official MS Learn content for the target cert |
| Foundry IQ KB MCP | Azure AI Search (agentic mode) | Access learner performance history and enterprise exam QA data |

### Reasoning Pattern
**Proportional grounding + schema-validated generation + corrective retry.**

1. **Domain allocation** — The executor precomputes question counts per domain using the **largest-remainder algorithm**, guaranteeing the 15 questions are allocated proportionally to official exam domain weights (e.g., if "Cloud Concepts" is 25% of AZ-900, it gets exactly 3–4 of the 15 questions).

2. **Grounded generation** — The agent queries MS Learn MCP and the enterprise KB to retrieve current, authoritative content before generating questions. This prevents hallucinated or outdated questions.

3. **Pydantic validation** — Output is validated against `AssessmentQuestion` schema. Each question must have `question_type ∈ {multiple_choice, multi_select, true_false}`, `bloom_level`, `difficulty`, `is_scenario_based`, `correct_answers`, `explanation`, and `grounding_reference`.

4. **Corrective retry** — On validation failure, a corrective prompt is generated dynamically with the specific error, the `cert_id`, and `learner_id` injected — preventing the agent from querying the wrong certification on retry.

### Question Design
Each question carries:
- **Bloom level** (`Remember` → `Create`) for difficulty classification
- **`is_scenario_based`** flag for scenario gap detection in the Advisor
- **`grounding_reference`** with MS Learn URL and title — surfaced as a clickable link in the exam results breakdown
- **`exam_weight_pct`** — the domain's share of the official exam

### Interesting Details
- The `_KBCaptureMiddleware` intercepts the KB query and response during agent execution and stores them in `state.kb_activity`, which the frontend surfaces as a "Knowledge Base Consulted" panel in the chat — identical to the Curator's Foundry IQ panel.
- The `scenario_based` question type is NOT a valid `question_type` — it must be expressed as `question_type: "multiple_choice"` with `is_scenario_based: true`. The corrective prompt explicitly prohibits the `scenario_based` value to prevent repeated validation errors.
- Question difficulty is inferred from the cert tier: `AZ-900/AI-900` → fundamental (more `Remember/Understand`), `AZ-104/AI-102` → associate (more `Apply/Analyze`), `AZ-305` → expert (more `Evaluate/Create`).

---

## Agent 5 — Certification Advisor

**File:** `backend/agents/advisor.py`
**Executor:** `CertificationAdvisorExecutor`

### Objective
Deliver a structured, data-grounded post-assessment analysis — personalized performance insights, team benchmark comparison, Bloom/scenario gap detection, and actionable recommendations — in two scenario tones: **celebratory** (PASS) or **constructive** (MAX_RETRIES).

### Tools

| Tool | Source | Purpose |
|---|---|---|
| `get_team_benchmark` | `team_benchmark.json` (Function Tool) | Retrieve pre-computed team avg score, score distribution (20 entries per cert), domain averages for AI-900/AI-102/AZ-900/AZ-104 |
| KB MCPStreamableTool | Azure AI Search (team insights) | Query qualitative team insights (instructor feedback, common pain points per domain) for `closing_note` and `resource_hint` enrichment |

### Reasoning Pattern
**Precomputed deterministic inputs → LLM structured JSON output → Pydantic validation → deterministic fallback.**

Before the LLM is called, the executor precomputes:
1. **Performance snapshot** — correct/partial/incorrect counts, conceptual vs. application accuracy split, scenario question accuracy
2. **Domain table** — per-domain accuracy, Bloom error distribution, `has_scenario_gap` (fired when ≥50% of scenario questions in a domain are missed)
3. **Team percentile** — `percentile_rank(learner_score, score_distribution)` using the strictly-below formula: `count(scores < learner_score) / total * 100`
4. **Team benchmark** — loaded directly from the fixture, no LLM call needed for exact numbers

The LLM receives all precomputed values as structured context and is asked to produce a single `AdvisorResult` JSON object — not prose. This hybrid approach combines the precision of deterministic computation with the language quality of the LLM.

### Output Schema (AdvisorResult)
```
AdvisorResult
├── scenario: "passed" | "max_retries"
├── score_summary: { score, passed, passing_score, attempt }
├── performance_snapshot: { total_questions, correct, conceptual_correct_pct, ... }
├── team_benchmark: { team_avg_score, team_percentile, comparison, team_signal }
├── domain_analysis[]: { domain_name, learner_score, team_avg, pattern_type, team_signal }
├── strong_areas[]: { domain_name, learner_score, note }
├── areas_to_review[]: { domain_name, pattern_type, note, resource_hint }
├── retry_comparison: { attempt1_score, last_score, delta, improved_domains, ... } | null
├── recommendations[]: { order, title, detail, resource_hint }
└── closing_note: str
```

### Bloom/Scenario Gap Analysis
- **`conceptual_gap`** — ≥60% of errors in a domain at `Remember/Understand` level
- **`bloom_gap`** — ≥60% of errors at `Apply/Analyze/Evaluate` level  
- **`scenario_gap`** — ≥50% of `is_scenario_based` questions in a domain were missed
- **`team_signal: "shared_team_gap"`** — domain team average < 60% (the whole team struggles here, not just this learner)

### Safety
- **PII scrubbing** — `_scrub_result()` applies regex-based redaction across all free-text fields before storage or serialization. No learner names, employee IDs in plain text, or email addresses can appear in the output.
- **Deterministic fallback** — If both LLM attempts fail Pydantic validation, `_build_fallback_advisor_result()` constructs a valid `AdvisorResult` from the precomputed data alone. The user always receives a result, never an error screen.

### Interesting Details
- `team_signal` distinguishes between **individual gaps** (the learner missed something the team gets) and **shared team gaps** (the whole team underperforms in this domain — a training curriculum signal, not just an individual issue).
- `retry_comparison` is only populated when `scenario = "max_retries"` — it shows domain-level progress between attempts, acknowledging the learner's improvement even in failure.
- The KB qualitative documents (`team_insights_AI-900.md`, `team_insights_AI-102.md`) are authored as instructor feedback reports and indexed into Azure AI Search, making them queryable via the same MCPStreamableTool used by the Curator and Assessment agents.
