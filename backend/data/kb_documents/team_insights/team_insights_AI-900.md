# AI-900 — Team Insights & Instructor Notes
> Source: internal cohort analytics + instructor feedback (anonymized)
> Last updated: 2026-Q1 | Cohort size: 15

## Team overview
The team shows solid conceptual grasp of AI fundamentals but consistently underperforms on scenario-based application questions. Average readiness entering the cohort was moderate; most engineers had cloud infrastructure backgrounds but limited hands-on AI/ML experience. The largest gains came after structured lab sessions in Azure AI Foundry and focused review of service-differentiation scenarios.

## Common stumbling blocks by domain

### Describe artificial intelligence workloads and considerations
- Stumbling block: Distinguishing Responsible AI principles in applied scenarios — engineers frequently conflate "fairness" with "inclusiveness" when both appear in the same question stem.
- Why it happens: Team members focus on the technical definition of each principle rather than its human-impact framing. Scenario questions require understanding stakeholder perspectives, not just the terminology.
- Instructor note: Recommend reviewing Microsoft's six Responsible AI principles with real-world case examples for each. The official Microsoft Learn module on Responsible AI uses concrete industry examples that significantly improved accuracy in follow-up practice runs.

### Describe fundamental principles of machine learning on Azure
- Stumbling block: Selecting the correct ML approach (classification vs. regression vs. clustering vs. anomaly detection) for a given business scenario. Questions of the form "which ML type would best solve X" had a 38% error rate in this cohort.
- Why it happens: Engineers understand the algorithmic definitions clearly but struggle to map them to business problem descriptions that use non-technical language. The gap is in domain-to-algorithm translation, not the algorithms themselves.
- Instructor note: Practice scenario-to-algorithm mapping exercises before the exam. The Microsoft Learn "Get started with AI on Azure" module's interactive labs help bridge the business-to-technical translation gap.

### Describe features of computer vision workloads on Azure
- Stumbling block: Differentiating Azure AI Vision capabilities — OCR vs. Image Analysis vs. Custom Vision vs. Face API. Service-selection questions ("which service would you use for X?") are the most error-prone question type in this domain.
- Why it happens: The team tends to treat Azure AI Vision as a monolithic service. Engineers who haven't built hands-on labs often pick the most familiar service name rather than the most appropriate one for the scenario.
- Instructor note: A side-by-side comparison exercise of all four Computer Vision services with concrete use cases improved accuracy by approximately 15 percentage points in mock assessments. The "Analyze images" and "Read text" Microsoft Learn modules are the most effective resources here.

### Describe features of NLP workloads on Azure
- Stumbling block: Distinguishing Azure AI Language service capabilities — CLU for intent recognition, QnA/knowledge bases, sentiment analysis, key phrase extraction, and named entity recognition often get conflated.
- Why it happens: Most engineers in this cohort had not built hands-on NLP labs before the assessment. Without direct experience with the Azure AI Language Studio, the services appear very similar in practice.
- Instructor note: Hands-on labs in Azure AI Language Studio are strongly recommended before the exam. The "Explore natural language processing" Microsoft Learn module combined with the Language Studio quickstarts produced the best outcomes. NLP service differentiation is the most common failure point in this cert for this team.

### Describe features of generative AI workloads on Azure
- Stumbling block: Scenario questions about when to use RAG vs. fine-tuning vs. prompt engineering. Several engineers also struggled to distinguish Azure OpenAI service capabilities from general OpenAI capabilities.
- Why it happens: Generative AI is the newest domain and team knowledge is most uneven. The rapid evolution of Azure OpenAI means some engineers studied materials that no longer reflect the current service architecture. Several noted that the Q2 Microsoft Learn module felt outdated relative to Azure AI Foundry's current capabilities.
- Instructor note: Supplement Microsoft Learn modules with current Azure AI Foundry documentation, particularly the sections on Azure OpenAI deployment and playground. The "Fundamentals of Generative AI" module is a solid foundation, but hands-on time in Azure AI Foundry is necessary to answer service-capability questions accurately.

## Recommended resources for weak areas
- Describe fundamental principles of machine learning on Azure: Microsoft Learn — "Get started with AI on Azure" + interactive ML type selection labs
- Describe features of computer vision workloads on Azure: Microsoft Learn — "Analyze images" and "Read text" modules; Azure AI Vision Studio quickstart
- Describe features of NLP workloads on Azure: Microsoft Learn — "Explore natural language processing"; Azure AI Language Studio quickstart labs
- Describe features of generative AI workloads on Azure: Microsoft Learn — "Fundamentals of Generative AI"; Azure AI Foundry portal documentation and playground

## Closing guidance
AI-900 is a breadth-first certification. The team's most reliable improvement path is: (1) complete hands-on labs in Azure AI Foundry sandbox for each service family, (2) review service differentiation across AI Vision, Language, and Speech with side-by-side comparison exercises, and (3) practice exclusively with scenario-based questions from Microsoft's official practice assessments. Conceptual knowledge is already strong — the gap is in applied scenario translation.
