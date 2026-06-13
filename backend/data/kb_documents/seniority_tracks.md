# Azure Certification Tracks by Seniority Level

This document describes which Azure certifications are appropriate for each seniority
level, and the reasoning behind those recommendations based on historical pass rates
and learner readiness data from the enterprise learning program.

Lifecycle key used below:
- *(retiring <date>)* — still earnable but closing soon; recommend only if completable before deadline
- *(beta)* — in beta; earnable now, content may evolve before GA
- *(retired)* — no longer earnable; redirect to replacement

---

## Junior Level (0–2 years experience)

Junior employees are building foundational skills. They benefit most from
Fundamentals-level certifications before tackling Associate certs.

**Recommended certifications for junior employees:**

- **AZ-900 (Azure Fundamentals)** — universally appropriate. 24 hours. No prerequisites.
  The single most important first cert regardless of role.

- **SC-900 (Security, Compliance, and Identity Fundamentals)** — for juniors on the
  security track or compliance-adjacent roles. 16 hours. No prerequisites.

- **AI-901 (Azure AI Fundamentals)** *(beta)* — for junior AI Engineers, Developers
  with AI interest, and Data Scientists. 20 hours estimated. Covers Azure AI Foundry,
  generative AI, responsible AI, and agentic AI concepts. If AI-901 is not yet GA,
  use **AI-900** as the interim fundamentals cert.

- **DP-700 (Microsoft Fabric Data Engineer Associate)** — accessible for junior Data
  Engineers with SQL and Python skills. AZ-900 should come first.

**What junior employees should NOT start with:**
- AZ-305, AZ-400, AZ-308 (Expert level) — require broad multi-service Azure experience.
- AI-103, AI-200, AI-300, SC-500 (Associate level) — without fundamentals foundation,
  first-attempt pass rates drop significantly. Enterprise data shows 40% lower success
  on AI associate certs without the corresponding fundamentals cert completed first.
- ~~AI-102~~ *(retired)*, ~~DP-203~~ *(retired)*, ~~DP-100~~ *(retired)* — do not recommend.

**Team observation:** Junior learners with fewer than 4 streak days are at-risk of dropout.
Early engagement reminders sent at days 3 and 7 improve completion rates by 35%.

---

## Mid Level (2–5 years experience)

Mid-level employees have practical experience and are ready for Associate-level certifications
that validate role-specific skills.

**Recommended certifications by role:**

| Role | Primary target | Notes |
|------|---------------|-------|
| Cloud Engineer | **AZ-104** (Administrator Associate) — 96h | Validates operational Azure skills |
| Developer | **AI-200** *(beta)* — 90h | Replaces AZ-204 *(retiring Jul 31 2026)*; AI backend focus |
| DevOps Engineer | **AZ-400** (DevOps Solutions Expert) — 100h | Requires AZ-104 |
| Security Engineer | **SC-500** *(beta)* — 95h | Replaces AZ-500 *(retiring Aug 31 2026)* |
| Data Engineer | **DP-700** (Fabric Data Engineer) — 80h | Replaces DP-203 *(retired)* |
| Data Engineer (Databricks) | **DP-750** (Azure Databricks Data Engineer) — 95h | Databricks-stack specialization |
| AI Engineer | **AI-103** *(beta)* — 90h | Replaces AI-102 *(retired Jun 30 2026)* |
| ML Engineer / Data Scientist | **AI-300** (ML Operations Engineer) — 90h | Replaces DP-100 *(retired)* |

**Seniority-based adjustment:** A mid-level employee whose role does not yet match
the cert's primary role should start with the appropriate Fundamentals cert for the
new domain before pursuing the Associate cert.

**Retiring certs still earnable at mid level:**
- **AZ-204** *(retiring Jul 31 2026)* — recommend AI-200 instead unless the learner
  needs immediate certification and AI-200 is still in beta.
- **AZ-500** *(retiring Aug 31 2026)* — recommend SC-500 instead.

**Team observation:** Mid-level learners average 6–8 study hours per week.
At 6 hours/week, AZ-104 completion typically takes 16 weeks.
Readiness scores above 65 correlate strongly with first-attempt pass rates above 80%.

---

## Senior Level (5+ years experience)

Senior employees are ready for Expert-level certifications and specializations.
They typically hold one or more Associate certs already.

**Recommended certifications for senior employees:**

- **AZ-305 (Azure Infrastructure Solutions Expert)** — for senior Cloud Engineers and
  Solutions Architects. Requires AZ-104. 120 hours. Covers Well-Architected Framework,
  identity design, storage architecture, business continuity, and infrastructure design.

- **AZ-308 (Azure AI Infrastructure Solutions)** *(beta)* — for architects leading AI
  platform initiatives. Requires AZ-305. 130 hours. Extends AZ-305 with AI topology
  design, vector store architecture, AI cost governance, and secure AI system design.

- **AZ-400 (DevOps Solutions Expert)** — for senior DevOps Engineers. Requires AZ-104.
  100 hours. Covers Azure Pipelines, GitHub Actions, security scanning, and compliance as code.

- **DP-600 (Fabric Analytics Engineer Associate)** — for senior Data Engineers
  specializing in analytics. Pairs with DP-700. 80 hours. Covers semantic models,
  Power BI datasets, and self-service Fabric analytics.

- **DP-750 (Azure Databricks Data Engineer Associate)** — for senior Data Engineers on
  the Databricks stack. 95 hours. Covers Unity Catalog governance, Delta Live Tables,
  and Databricks Workflows.

**What senior employees should NOT be assigned:**
- AZ-900 as a primary target — appropriate only if the learner genuinely has no Azure
  exposure, which is rare at senior level.
- ~~AI-102~~ *(retired)*, ~~AZ-204~~ *(retiring)*, ~~AZ-500~~ *(retiring)* — redirect to replacements.

**Team observation:** Senior learners study more efficiently. Average practice scores
above 80 at readiness assessment predict high first-attempt success on Expert certs.
Senior employees with 45+ streak days have a 92% completion rate.

---

## Readiness score interpretation

The enterprise readiness score (0–100) is computed from:
- Practice test scores (weighted 40%)
- Study hours completed vs. recommended (30%)
- Streak consistency (20%)
- Self-assessment alignment (10%)

| Score | Interpretation | Recommendation |
|-------|---------------|----------------|
| 0–40  | At risk | Increase study frequency; assign engagement reminders |
| 41–65 | On track | Continue current pace; target exam in 8–12 weeks |
| 66–80 | Ready | Schedule exam within 4–6 weeks |
| 81–100 | High confidence | Schedule exam immediately; likely to pass on first attempt |
