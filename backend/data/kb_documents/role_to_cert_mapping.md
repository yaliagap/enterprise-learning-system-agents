# Azure Certification Roadmap by Role

This guide maps enterprise employee roles to the recommended Azure certification track,
including prerequisites, seniority considerations, and suggested order of pursuit.

Lifecycle key:
- *(retiring <date>)* — cert can still be earned but will stop being available on that date.
  Recommend only if the learner can complete before the deadline.
- *(beta)* — exam is in beta; content may change before GA. Suitable for early adopters.
- *(retired)* — no longer earnable. Do not recommend.

---

## Cloud Engineer

Cloud Engineers manage and operate Azure infrastructure. They provision resources, configure
virtual networks, manage identity and access, and monitor workloads.

**Recommended certification path:**
- Start with **AZ-900 (Azure Fundamentals)** if no prior Azure exposure — 24 hours.
- Core cert: **AZ-104 (Azure Administrator Associate)** — 96 hours. Validates ability to manage
  Azure environments including virtual networks, storage, compute, identity, and governance.
- Advanced: **AZ-305 (Azure Infrastructure Solutions Expert)** — 120 hours. Requires AZ-104.
  Designed for senior engineers and architects responsible for designing entire Azure solutions.

**By seniority:**
- Junior: AZ-900 → AZ-104. Do not skip AZ-900 even with some cloud experience — it
  solidifies governance and compliance foundations.
- Mid: AZ-104 is the primary target. AZ-900 may be skipped with 1+ year of hands-on Azure.
- Senior / Lead: AZ-305 after AZ-104. Focuses on Well-Architected Framework, high
  availability, disaster recovery, and cost optimization.

---

## Developer

Developers build applications on Azure using compute, storage, messaging, and security
services. They work with APIs, SDKs, serverless functions, and managed databases.

**Recommended certification path:**
- Start with **AZ-900** if no Azure foundation.
- Core cert: **AI-200 (Azure AI Cloud Developer Associate)** *(beta)* — 90 hours. Replaces
  AZ-204 (retiring July 31, 2026). Covers containerized AI solutions, AI backend with
  Cosmos DB and PostgreSQL vector stores, Azure messaging/eventing, API Management, and
  Azure Monitor. Designed for developers building AI-powered back-end services on Azure.
- Interim path: **AZ-204 (Azure Developer Associate)** *(retiring July 31, 2026)* — 80 hours.
  Still earnable until July 31, 2026. Recommend only if AI-200 is not yet GA or the
  learner needs the cert immediately.

**By seniority:**
- Junior: AZ-900 → AI-200. Python proficiency and basic Azure SDK experience expected
  before attempting. If AI-200 is still in beta, use AZ-204 as the interim cert.
- Mid: AI-200 is the primary target. If AZ-204 already held, transition to AI-200 for
  the AI backend specialization. Pair with AZ-305 for architectural depth.
- Senior: AI-200 baseline for AI-focused developers. AZ-305 or AZ-400 as next step
  depending on whether the role leans architectural or DevOps.

**Note:** AZ-204 retires July 31, 2026. AI-200 is its direct replacement with an expanded
AI backend scope. Developers should target AI-200 as the primary cert going forward.

---

## DevOps Engineer

DevOps Engineers build and maintain CI/CD pipelines, infrastructure as code, and automation.
They work closely with development and operations teams to improve delivery velocity.

**Recommended certification path:**
- Start with **AZ-900** if no Azure foundation.
- Infrastructure baseline: **AZ-104 (Azure Administrator)** — recommended before DevOps cert.
- Core cert: **AZ-400 (DevOps Solutions Expert)** — 100 hours. Covers Azure Pipelines,
  GitHub Actions, Bicep/ARM templates, security scanning, and compliance as code.
  Requires AZ-104 or AZ-204 as prerequisite. Note: AZ-204 retires July 31, 2026 —
  use AZ-104 as the prerequisite path going forward.

**By seniority:**
- Junior: AZ-900 → AZ-104. AZ-400 is Expert-level and not recommended as a first cert.
- Mid: AZ-400 is the target after AZ-104. Focus on CI/CD pipelines, security
  integration, and infrastructure as code.
- Senior / Lead: AZ-400 directly if AZ-104 is already held. May also pursue AZ-305
  to broaden into architecture.

---

## Security Engineer

Security Engineers implement, manage, and monitor security controls across Azure and
hybrid environments. They handle identity, network security, threat protection, and
compliance posture.

**Recommended certification path:**
- Start with **AZ-900** and **SC-900 (Security, Compliance, and Identity Fundamentals)** — 16 hours.
  SC-900 provides the conceptual security foundation before the engineering cert.
- Core cert: **SC-500 (Cloud and AI Security Engineer Associate)** *(beta)* — 95 hours.
  Replaces AZ-500 (retiring August 31, 2026). Covers identity and governance, network
  and compute security, Defender for Cloud, Microsoft Sentinel, and AI workload security.
  Requires AZ-104 level Azure knowledge and Microsoft Entra familiarity.

**By seniority:**
- Junior: AZ-900 → SC-900. SC-500 is Associate level and requires hands-on Azure
  infrastructure experience before attempting.
- Mid: SC-500 is the primary target after AZ-104 and SC-900. The added AI security
  domain (content safety, AI governance) makes it immediately relevant to enterprise
  Azure AI Foundry workloads.
- Senior: SC-500 baseline. Senior engineers may pursue SC-200 (Security Operations
  Analyst) or the Cybersecurity Architect Expert cert for broader security leadership.

**Note:** AZ-500 retires August 31, 2026. Engineers currently holding AZ-500 should
plan SC-500 certification before renewal becomes unavailable.

---

## Data Engineer

Data Engineers design and implement data pipelines, storage solutions, and analytics
workloads using Azure data services.

**Recommended certification path:**
- Start with **AZ-900** for cloud fundamentals.
- Core cert: **DP-700 (Microsoft Fabric Data Engineer Associate)** — 80 hours. Replaces
  DP-203 (retired). Covers Microsoft Fabric pipelines, lakehouses, Delta tables, OneLake,
  real-time intelligence with Eventstream, and Fabric workspace security.
- Databricks specialization: **DP-750 (Azure Databricks Data Engineer Associate)** — 95 hours.
  For teams using Azure Databricks as the primary data engineering platform. Covers
  Databricks environment setup, Unity Catalog governance, Delta Live Tables, and
  Databricks Workflows.
- Analytics specialization: **DP-600 (Microsoft Fabric Analytics Engineer Associate)**
  — 80 hours. Requires DP-700 or equivalent. Covers semantic models, Power BI datasets,
  and self-service analytics within Fabric.

**By seniority:**
- Junior: AZ-900 → DP-700. Accessible with foundational SQL, Python, and data pipeline
  knowledge.
- Mid: DP-700 is the primary target. If already held, choose DP-750 (Databricks track)
  or DP-600 (analytics track) based on team stack.
- Senior: DP-700 + specialization (DP-750 or DP-600). Senior engineers benefit from
  end-to-end Fabric or Databricks stack knowledge for leading data platform initiatives.

**Note:** DP-203 is retired. Do not recommend to new learners.

---

## AI Engineer

AI Engineers design and implement AI solutions using Azure AI services, including
natural language processing, computer vision, speech, and generative AI.

**Recommended certification path:**
- Start with **AZ-900** if no prior Azure exposure.
- AI Foundation: **AI-901 (Azure AI Fundamentals)** *(beta)* — 20 hours estimated.
  Next-generation fundamentals cert covering Azure AI Foundry, generative AI, responsible AI,
  and agentic AI concepts. Recommended entry point for the AI track.
  If AI-901 is not yet GA, use **AI-900** as the interim foundation — 16 hours.
- Core cert: **AI-103 (Azure AI Apps and Agents Developer Associate)** *(beta)* — 90 hours. Replaces
  AI-102 (retired June 30, 2026). Covers Azure AI Foundry, agentic AI, computer vision,
  NLP, knowledge mining, and generative AI solutions.
- Expert track: **AZ-308 (Azure AI Infrastructure Solutions)** *(beta)* — 130 hours. For
  senior engineers and architects designing enterprise AI platforms at scale.

**By seniority:**
- Junior: AZ-900 → AI-901 (or AI-900) → AI-103. Do not skip the fundamentals cert —
  enterprise pass rate data shows 40% lower first-attempt success on AI-102 (the
  predecessor) without the foundation cert. The same pattern is expected for AI-103.
- Mid: AI-103 is the primary target after AZ-900 and AI-901/AI-900. Mid-level engineers
  with strong ML backgrounds may pursue AI-103 directly with 1+ year Azure AI experience.
- Senior: AI-103 baseline expected. Senior engineers should pursue AZ-308 for
  architecture depth or AI-300 for MLOps/GenAIOps specialization.

**Note:** AI-102 retired June 30, 2026. Do not recommend to any learner.

---

## ML Engineer / Data Scientist

ML Engineers and Data Scientists build, train, deploy, and monitor machine learning
models on Azure. They combine data science expertise with platform engineering skills.

**Recommended certification path:**
- Start with **AZ-900** if no Azure foundation.
- Core cert: **AI-300 (Machine Learning Operations Engineer Associate)** — 90 hours.
  Replaces DP-100 (retired). Covers MLOps infrastructure on Azure Machine Learning,
  ML model lifecycle with MLflow and GitHub Actions, GenAIOps on Microsoft Foundry,
  generative AI quality assurance, and AI system optimization.

**By seniority:**
- Junior: AZ-900 → AI-300. Requires Python proficiency and entry-level DevOps familiarity
  (Git, CLIs). The MLOps focus means some prior data science or ML project experience
  is expected before attempting.
- Mid: AI-300 is the primary target. Engineers with active ML project experience pass
  at significantly higher rates. Pair with hands-on Azure Machine Learning workspace.
- Senior: AI-300 baseline. Senior ML engineers may pursue AZ-308 (AI Infrastructure
  Solutions architect track) for broader AI platform leadership at enterprise scale.

**Note:** DP-100 is retired. Do not recommend to any learner.

---

## Solutions Architect

Solutions Architects design end-to-end cloud solutions and are responsible for
cross-service architecture decisions, governance, security, and cost management.

**Recommended certification path:**
- Prerequisites: AZ-104 (Administrator) strongly recommended. AZ-204 was also recommended
  but retires July 31, 2026 — prioritize AZ-104 as the primary prerequisite path.
- Core cert: **AZ-305 (Azure Infrastructure Solutions Expert)** — 120 hours. Covers identity
  design, data storage architecture, business continuity, infrastructure design, and
  monitoring. Designed for experienced Azure practitioners.
- AI Architecture specialization: **AZ-308 (Azure AI Infrastructure Solutions)** *(beta)*
  — 130 hours. Extends AZ-305 with AI platform architecture: hub-and-spoke AI topologies,
  vector store design, AI cost governance, and secure AI system architecture.

**By seniority:**
- Junior-to-mid: Build AZ-104 foundation first. AZ-305 is Expert-level and requires
  broad Azure experience across services. Do not recommend without 2+ years hands-on Azure.
- Senior: AZ-305 is the primary target after AZ-104. Architects leading AI platform
  initiatives should also pursue AZ-308 once it reaches GA.

---

## Cross-role notes

- **AZ-900** is the universal entry point for any role without prior Azure experience.
- **Expert-level certs (AZ-305, AZ-400)** require real-world Azure experience. First-attempt
  success strongly correlates with 2+ years of hands-on Azure work.
- **Beta certs (AI-103, AI-901, AI-200, SC-500, AZ-308)** are earnable now but content
  may evolve before GA. Suitable for early adopters and engineers on the leading edge.
- **Retiring certs (AZ-204, AZ-500)** can still be earned before their respective deadlines
  but do not recommend for learners who cannot complete before the cutoff date.
- **Retired certs (AI-102, DP-100, DP-203)** cannot be earned. Always redirect to replacements.
- Certifications renew every 24 months via a free online assessment — no full re-exam required.
