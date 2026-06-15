# Synthetic Data — Enterprise Learning System

All data in this project is synthetic. No real customer, employee, or organizational data is used at any point.

The `backend/data/` folder is organized into three layers, each serving a different purpose in the system:

```
backend/data/
├── fixtures/          # Fabric IQ + Work IQ simulation (fixture-backed providers)
├── kb_documents/      # Foundry IQ Knowledge Base — uploaded to Azure AI Search
│   ├── exam_qa/       # Per-cert exam Q&A grounding documents
│   └── team_insights/ # Qualitative team insights per certification
└── synthetic/         # Narrative reports — also uploaded to Foundry IQ KB
```

---

## `fixtures/` — Fabric IQ & Work IQ simulation

These JSON files back the two enterprise data providers used by the agents at runtime. When `USE_REAL_IQ=false` (local/mock mode), the `IQProviderFactory` loads from these fixtures instead of hitting real Azure data services.

| File | Provider | Description |
|---|---|---|
| `learner_profiles.json` | Fabric IQ | 5 synthetic learner personas — role, seniority, current skills, target certs, completed certs, readiness score, learning style, timezone, weekly study hours |
| `learner_performance.json` | Fabric IQ | 20 assessment attempt records across learners and certifications — per-domain scores, weak areas, attempt history. Domain names match official exam skill areas from `cert_profiles.md` exactly (used for adaptive question distribution) |
| `calendar_signals.json` | Work IQ | Calendar and work activity signals for 5 employees — focus peak hours, meeting windows, preferred study days, session duration, channel response rates, streak days. Drives Study Plan Generator and Engagement Agent |
| `team_aggregates.json` | Work IQ | Team-level learning aggregates — readiness distribution, at-risk members, cert coverage, retry queue, capacity summary |
| `team_benchmark.json` | Advisor (Function Tool) | Pre-computed benchmark data for AI-900, AI-102, AZ-900, AZ-104 — team average score, score distribution (20 data points), domain-level averages. Used by the Certification Advisor to compute learner percentile rank |
| `certification_catalog.json` | Fabric IQ / Curator | 20 Azure certifications with exam codes, roles, passing scores, domain weights, skill tags, and lifecycle status (`active`, `retiring`, `beta`). The Curator validates all recommended certs against this catalog |
| `learning_resources.json` | Curator | Supplementary learning resource metadata |

All fixture files include a `_metadata` block with `"synthetic": true`, generation date, and a description.

---

## `kb_documents/` — Foundry IQ Knowledge Base

These Markdown files are the source documents **uploaded to Azure AI Search** (the Foundry IQ KB). Agents query this KB via `MCPStreamableTool` in agentic mode — the search service synthesizes an answer with citations rather than returning raw chunks.

### Core KB documents

| File | Used by | Description |
|---|---|---|
| `cert_profiles.md` | Curator, Assessment | Detailed profiles for all tracked certifications — target role, level, prerequisites, exam domains, LP UIDs for MS Learn Catalog API, lifecycle status |
| `role_to_cert_mapping.md` | Curator | Maps enterprise roles to recommended certification tracks, including prerequisites and suggested pursuit order |
| `seniority_tracks.md` | Curator | Which certifications are appropriate per seniority level, with historical pass rate context |
| `study_patterns.md` | Curator, Study Plan | Enterprise-observed study patterns, time estimates, and completion guidance based on aggregated learner data |

### `exam_qa/` — Per-cert grounding documents

Q&A documents for each certification. The Assessment Agent queries these when generating grounded questions, cross-referencing official MS Learn content with enterprise-specific context.

| File | Certification |
|---|---|
| `AI-900.md` | Azure AI Fundamentals |
| `AI-103.md` | Azure AI Engineer (variant) |
| `AI-200.md` | Azure AI track |
| `AI-300.md` | Azure AI track |
| `AI-901.md` | Azure AI track |
| `AZ-104.md` | Azure Administrator Associate |
| `AZ-305.md` | Azure Solutions Architect Expert |
| `AZ-308.md` | Azure track |
| `AZ-400.md` | Azure DevOps Engineer Expert |
| `AZ-900.md` | Azure Fundamentals |
| `DP-700.md` | Microsoft Fabric Data Engineer |
| `SC-500.md` | Microsoft Security Operations Analyst |
| `SC-900.md` | Microsoft Security Fundamentals |

### `team_insights/` — Qualitative team KB documents

Instructor-authored qualitative reports per certification, also uploaded to Azure AI Search. The **Certification Advisor** queries these to enrich `closing_note` and `resource_hint` fields with context that can't be derived from numbers alone — common stumbling blocks, instructor notes, domain-specific pain points observed across the team cohort.

| File | Certification | Content |
|---|---|---|
| `team_insights_AI-900.md` | Azure AI Fundamentals | Domain-by-domain instructor notes, most missed question types, common conceptual gaps, MS Learn resource hints |
| `team_insights_AI-102.md` | Azure AI Engineer Associate | 6-domain breakdown, Knowledge Mining flagged as lowest accuracy (58.9%), instructor feedback on scenario-based questions |

---

## `synthetic/` — Narrative reports (also in Foundry IQ KB)

Three long-form narrative Markdown documents, written as enterprise reports, that are **also indexed in Azure AI Search**. They provide richer qualitative grounding — especially useful for the Curator when reasoning about role fit and study capacity, since they contain narrative patterns that short KB docs don't capture.

Each file is explicitly self-described as synthetic at the top.

| File | Description |
|---|---|
| `engineering_certification_guide.md` | Certification roadmap written from the perspective of an engineering team — role-to-cert mapping in narrative format, includes reasoning about when to pursue each cert |
| `team_learning_report.md` | Simulated Q1/Q2 2026 team learning report — completion rates, trends, at-risk signals, recommended actions |
| `workload_insights_report.md` | Simulated capacity analysis — study hours available by role and seniority, focus patterns, peak learning periods |

---

## How agents consume this data

```
Agent                 Fixture (mock mode)          KB (Azure AI Search)
─────────────────     ────────────────────         ──────────────────────────────────
Curator               learner_profiles.json        cert_profiles.md
                      certification_catalog.json   role_to_cert_mapping.md
                                                   seniority_tracks.md
                                                   study_patterns.md
                                                   synthetic/*.md

Study Plan Gen.       calendar_signals.json        —

Engagement Agent      calendar_signals.json        —

Assessment Agent      learner_performance.json     exam_qa/<cert>.md
                                                   cert_profiles.md

Certification Advisor team_benchmark.json          team_insights/<cert>.md
                      (Function Tool — not KB)
```
