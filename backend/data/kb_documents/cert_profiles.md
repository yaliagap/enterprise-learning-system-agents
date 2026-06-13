# Azure Certification Profiles

Detailed profiles for each certification tracked by the enterprise learning program.
Includes target role, level, prerequisites, exam domains, study guidance, LP UIDs
for the Microsoft Learn Catalog API, and lifecycle status (retired / beta).

Field legend:
- `lp_uids` — ordered list of self-paced learning path UIDs from the MS Learn Catalog API.
  Pass each UID to `get_learning_path(uid)` to retrieve module-level details and hours.
  Verified against the catalog on 2026-06-13.
- `retired: true` — certification is no longer earnable. Do NOT recommend to learners.
- `beta: true` — exam is in beta; content and dates may change. Recommend only to early
  adopters or when the learner explicitly requests the latest track.

---

## AZ-900 — Microsoft Azure Fundamentals

**Level:** Fundamentals
**Target roles:** All roles — universal entry point
**Prerequisites:** None
**Recommended study hours:** 24
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-fundamentals/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months (free online assessment)

**lp_uids:**
- learn.wwl.microsoft-azure-fundamentals-describe-cloud-concepts
- learn.wwl.azure-fundamentals-describe-azure-architecture-services
- learn.wwl.describe-azure-management-governance

**What this certification validates:**
Knowledge of cloud computing concepts including high availability, scalability, and
elasticity. Understanding of Azure's global infrastructure (regions, availability zones,
resource groups). Core Azure services: compute, networking, storage, and databases.
Azure management tools: portal, CLI, PowerShell, ARM templates. Governance services:
Azure Policy, Management Groups, Blueprints. Cost management: Pricing Calculator,
TCO Calculator, Azure Cost Management. Security: Microsoft Defender for Cloud,
Azure Sentinel basics. Compliance frameworks and shared responsibility model.

**Exam skill areas:**
- Describe cloud concepts (25–30%)
- Describe Azure architecture and services (35–40%)
- Describe Azure management and governance (30–35%)

**Enterprise observations:**
Average first-attempt pass rate: 88%. Learners who complete the full 24-hour recommended
path before attempting the exam pass at 94%. The exam takes 45 minutes and is accessible
at any Pearson VUE test center or online proctored. Ideal for any employee new to Azure
regardless of technical background.

---

## AZ-104 — Microsoft Azure Administrator Associate

**Level:** Associate
**Target roles:** Cloud Engineer, DevOps Engineer (as prerequisite)
**Prerequisites:** AZ-900 (recommended, not strictly required)
**Recommended study hours:** 96
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-administrator/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months

**lp_uids:**
- learn.az-104-manage-identities-governance
- learn.az-104-manage-virtual-networks
- learn.az-104-monitor-backup-resources
- learn.az-104-manage-compute-resources
- learn.az-104-manage-storage

**What this certification validates:**
Implementing and managing Azure identity and governance using Microsoft Entra ID,
RBAC, Azure Policy, and Management Groups. Deploying and managing storage accounts,
blob storage, and Azure Files. Managing virtual machines, container instances,
Azure Kubernetes Service basics, and App Service. Configuring virtual networks,
load balancers, VPN gateways, and network security groups. Monitoring workloads
with Azure Monitor, Log Analytics, and backup/disaster recovery with Azure Backup
and Site Recovery.

**Exam skill areas:**
- Manage Azure identities and governance (20–25%)
- Implement and manage storage (15–20%)
- Deploy and manage Azure compute resources (20–25%)
- Implement and manage virtual networking (15–20%)
- Monitor and maintain Azure resources (10–15%)

**Enterprise observations:**
Average first-attempt pass rate: 74%. Learners with a readiness score above 65
pass at 86%. The exam takes 100 minutes. Weak areas for our team: identity and
governance (average 58% on practice tests) and monitoring configuration.
Recommended: focus extra study on Entra ID conditional access and Azure Monitor
alert rules before exam day.

---

## AZ-204 — Developing Solutions for Microsoft Azure

**retired: true**
**Retirement date:** July 31, 2026

**Level:** Associate
**Target roles:** Developer, Software Engineer
**Prerequisites:** AZ-900 (recommended)
**Recommended study hours:** 80
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-developer/
**Passing score:** 700 / 1000

**lp_uids:**
- learn.wwl.az-204-implement-iaas-solutions
- learn.wwl.az-204-develop-solutions-that-use-azure-cosmos-db
- learn.wwl.az-204-develop-solutions-that-use-blob-storage
- learn.wwl.az-204-implement-azure-security
- learn.wwl.az-204-connect-to-azure-services
- learn.wwl.az-204-implement-caching-for-solutions
- learn.wwl.az-204-monitor-troubleshoot-optimize-azure-solutions
- learn.wwl.az-204-implement-api-management

**What this certification validates:**
Developing Azure compute solutions including Azure Functions (serverless), containers,
and App Service. Implementing Azure storage solutions: Blob Storage, Cosmos DB,
Azure Cache for Redis, and CDN. Securing applications with Azure Key Vault, managed
identities, and Microsoft Entra. Monitoring and troubleshooting with Application
Insights and Azure Monitor. Connecting to and consuming Azure services and third-party
APIs via Service Bus, Event Grid, Event Hubs, and API Management.

**Exam skill areas:**
- Develop Azure compute solutions (25–30%)
- Develop for Azure storage (15–20%)
- Implement Azure security (20–25%)
- Monitor, troubleshoot, and optimize Azure solutions (15–20%)
- Connect to and consume Azure services and third-party services (15–20%)

**Enterprise observations:**
Average first-attempt pass rate: 71%. Developers with active project experience on
Azure pass at 83%. Common failure area: Azure Storage SDK specifics and Cosmos DB
partition key design. Recommend hands-on labs with Cosmos DB before the exam.

---

## AZ-305 — Designing Microsoft Azure Infrastructure Solutions

**Level:** Expert
**Target roles:** Solutions Architect, Senior Cloud Engineer
**Prerequisites:** AZ-104 (required)
**Recommended study hours:** 120
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-solutions-architect/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months

**lp_uids:**
- learn.wwl.microsoft-azure-architect-design-prerequisites
- learn.wwl.design-infranstructure-solutions
- learn.wwl.design-data-storage-solutions
- learn.wwl.design-identity-governance-monitor-solutions
- learn.wwl.design-business-continuity-solutions

**What this certification validates:**
Designing identity, governance, and monitoring solutions using Azure Well-Architected
Framework principles. Designing data storage solutions: relational, non-relational,
data integration, and data flow architecture. Designing business continuity solutions:
backup, disaster recovery, high availability, and RTO/RPO planning. Designing
infrastructure: compute, networking, application delivery, and migration strategies.

**Exam skill areas:**
- Design identity, governance, and monitoring solutions (25–30%)
- Design data storage solutions (25–30%)
- Design business continuity solutions (10–15%)
- Design infrastructure solutions (25–30%)

**Enterprise observations:**
Average first-attempt pass rate: 61%. Expert certs require demonstrated architectural
experience. Learners with 5+ years of Azure experience and practice scores above 80
pass at 79%. Commonly failed area: business continuity design (RTO/RPO trade-offs).
Recommended: supplement with Well-Architected Framework review sessions.

---

## AZ-400 — Designing and Implementing Microsoft DevOps Solutions

**Level:** Expert
**Target roles:** DevOps Engineer, Platform Engineer
**Prerequisites:** AZ-104 or AZ-204 (one required)
**Recommended study hours:** 100
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/devops-engineer/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months

**lp_uids:**
- learn.az-400-develop-instrumentation-strategy
- learn.az-400-develop-sre-strategy
- learn.az-400-implement-process-for-continuous-feedback
- learn.az-400-design-implement-release-strategy
- learn.az-400-design-implement-source-control-strategy
- learn.az-400-implement-security-validate-code-bases-compliance
- learn.wwl.az-400-implement-security-validate-code-basescompliance
- learn.wwl.az-400-design-implement-pipelines-strategy
- learn.wwl.az-400-design-implement-flow-work

**What this certification validates:**
Configuring processes and communications for DevOps workflows. Designing and implementing
source control with GitHub and Azure Repos including branching strategies and pull
request policies. Building and releasing pipelines with Azure Pipelines and GitHub Actions
including multi-stage deployments, gates, and approvals. Developing security and
compliance plans including SAST, DAST, dependency scanning, and compliance as code.
Implementing instrumentation strategy with Azure Monitor, Application Insights, and
distributed tracing.

**Exam skill areas:**
- Configure processes and communications (10–15%)
- Design and implement source control (15–20%)
- Design and implement build and release pipelines (40–45%)
- Develop a security and compliance plan (10–15%)
- Implement an instrumentation strategy (10–15%)

**Enterprise observations:**
Average first-attempt pass rate: 65%. The pipeline design section (40–45%) is the
most heavily weighted. Learners who have built real Azure Pipelines YAML from scratch
pass at 78%. Weak area for our team: security scanning integration (average 51%
on practice tests). Recommend dedicated study on Defender for DevOps and
GitHub Advanced Security before the exam.

---

## AZ-500 — Microsoft Azure Security Technologies

**retired: true**
**Retirement date:** August 31, 2026
**Replaced by:** SC-500 — see profile below

**Level:** Associate
**Target roles:** Security Engineer, Cloud Engineer (security track)
**Prerequisites:** AZ-104 (recommended); security background helpful
**Recommended study hours:** 90
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-security-engineer/
**Passing score:** 700 / 1000

**lp_uids:**
- learn.wwl.secure-azure-services-workloads
- learn.wwl.implement-resource-mgmt-security
- learn.wwl.secure-networking
- learn.wwl.secure-compute-storage-databases

**What this certification validates:**
Managing identity and access with Microsoft Entra ID, Privileged Identity Management,
and Conditional Access. Implementing platform protection: network security groups,
Azure Firewall, DDoS protection, and Azure Bastion. Securing data and applications
using Azure Key Vault, storage security, and database threat protection. Managing
security operations with Microsoft Defender for Cloud, Microsoft Sentinel (SIEM/SOAR),
and Azure Monitor security alerts.

**Exam skill areas:**
- Manage identity and access (25–30%)
- Secure networking (20–25%)
- Secure compute, storage, and databases (20–25%)
- Manage security operations (25–30%)

**Enterprise observations:**
Average first-attempt pass rate: 68%. Requires both Azure infrastructure knowledge
(AZ-104 level) and security fundamentals. Learners coming from a pure development
background often underestimate the networking security section. Recommend allocating
30% of study time to Defender for Cloud and Sentinel alert rules — consistently
the weakest area in practice assessments.

---

## SC-500 — Microsoft Certified: Cloud and AI Security Engineer Associate *(Beta)*

**beta: true**
**Replaces:** AZ-500 (retiring August 31, 2026)

**Level:** Associate
**Target roles:** Security Engineer, Cloud Engineer (security track)
**Prerequisites:** AZ-104 (recommended); security background and familiarity with Microsoft Entra required
**Recommended study hours:** 95
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/cloud-and-ai-security-engineer-associate/
**Passing score:** 700 / 1000
**Exam duration:** 100 minutes

**lp_uids:**
- learn.wwl.secure-azure-services-workloads-defender-cloud
- learn.wwl.secure-azure-using-microsoft-defender-cloud-sentinel
- learn.wwl.secure-networking
- learn.wwl.secure-compute-storage-databases
- learn.wwl.implement-ai-security

**What this certification validates:**
Managing identity, access, and governance: Microsoft Entra ID, Privileged Identity
Management, Conditional Access, and Azure RBAC for cloud and AI workloads. Securing
storage, databases, and networking: encryption, private endpoints, network security
groups, Azure Firewall, and DDoS protection. Securing compute: VM hardening, container
security, and App Service security configurations. Managing and monitoring security
posture with Microsoft Defender for Cloud (regulatory compliance controls, CSPM),
Microsoft Sentinel (SIEM/SOAR), and AI-specific security controls including content
safety and responsible AI guardrails.

**Exam skill areas:**
- Manage identity, access, and governance (20–25%)
- Secure storage, databases, and networking (20–25%)
- Secure compute (20–25%)
- Manage and monitor security posture (30–35%)

**Enterprise observations:**
Beta — no enterprise pass rate data. Expands AZ-500's scope to include AI workload
security — a critical addition given the enterprise's Azure AI Foundry adoption.
Engineers holding AZ-500 should plan to certify on SC-500 before the August 31, 2026
retirement date. The added AI security domain (content safety, AI model governance)
differentiates SC-500 from its predecessor.

---

## SC-900 — Microsoft Security, Compliance, and Identity Fundamentals

**Level:** Fundamentals
**Target roles:** All roles — entry point for security track; compliance officers; GRC analysts
**Prerequisites:** None
**Recommended study hours:** 16
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/security-compliance-and-identity-fundamentals/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months

**lp_uids:**
- learn.wwl.describe-concepts-of-security-compliance-identity

**What this certification validates:**
Core security concepts: zero trust, defense in depth, CIA triad, encryption, and
authentication methods. Microsoft Entra ID (identity and access management): authentication,
authorization, conditional access, and identity protection. Microsoft security solutions:
Microsoft Defender for Cloud, Microsoft Sentinel, Microsoft 365 Defender suite.
Microsoft compliance solutions: Purview compliance portal, information protection,
data lifecycle management, and eDiscovery.

**Exam skill areas:**
- Describe the concepts of security, compliance, and identity (10–15%)
- Describe the capabilities of Microsoft Entra (25–30%)
- Describe the capabilities of Microsoft security solutions (35–40%)
- Describe the capabilities of Microsoft compliance solutions (20–25%)

**Enterprise observations:**
High completion rate — 93% first-attempt pass. Accessible to non-technical staff
including legal, compliance, and HR roles who need to understand the security landscape.
Ideal prerequisite before AZ-500 or SC-200 for engineers pivoting to the security track.

---

## AI-900 — Microsoft Azure AI Fundamentals

**Level:** Fundamentals
**Target roles:** AI Engineer (junior), Data Engineer with AI interest, all roles exploring AI
**Prerequisites:** None
**Recommended study hours:** 16
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-fundamentals/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months

**lp_uids:** []
**Note:** No self-paced learning paths currently published in the MS Learn Catalog for AI-900
(verified June 2026). Use the Microsoft Learn exam page and practice assessments directly.

**What this certification validates:**
Core machine learning concepts: supervised vs. unsupervised learning, classification,
regression, and clustering. Azure Machine Learning Studio and automated ML basics.
Azure AI Services overview: Vision, Speech, Language, Decision, and OpenAI services.
Responsible AI principles: fairness, reliability, privacy, inclusiveness, transparency,
and accountability. Natural language processing concepts and conversational AI with
Azure Bot Service.

**Exam skill areas:**
- Describe artificial intelligence workloads and considerations (20–25%)
- Describe fundamental principles of machine learning on Azure (25–30%)
- Describe features of computer vision workloads on Azure (15–20%)
- Describe features of NLP workloads on Azure (15–20%)
- Describe features of generative AI workloads on Azure (15–20%)

**Enterprise observations:**
Average first-attempt pass rate: 91%. Shortest and most accessible cert in the catalog.
Junior AI Engineers who complete AI-900 before AI-102 show 40% higher pass rates on
AI-102 first attempt. Strongly recommended as the stepping stone cert for anyone
exploring the AI track regardless of their technical background.

---

## AI-102 — Designing and Implementing a Microsoft Azure AI Solution

**retired: true**
**Retirement date:** June 30, 2026
**Replaced by:** AI-103 (beta) — see profile below

**Level:** Associate
**Target roles:** AI Engineer
**Prerequisites:** AZ-900 (required); AI-900 strongly recommended
**Recommended study hours:** 80
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-engineer/
**Passing score:** 700 / 1000

**lp_uids:** []
**Note:** Microsoft removed the official self-paced training collection from the MS Learn
Catalog prior to the June 30 2026 retirement date. Do NOT recommend this certification
to learners — direct them to AI-103 instead.

**What this certification validates (historical reference):**
Planning and managing Azure AI solutions including resource provisioning, cost management,
and responsible AI implementation. Implementing content moderation with Azure AI Content
Safety. Building computer vision solutions with Azure AI Vision and Custom Vision.
Natural language processing with Azure AI Language: sentiment analysis, named entity
recognition, key phrase extraction, question answering, and custom text classification.
Knowledge mining with Azure AI Search including indexers, skillsets, and semantic search.
Building generative AI solutions with Azure OpenAI Service including prompt engineering,
retrieval-augmented generation (RAG), and fine-tuning.

**Enterprise observations (historical):**
Average first-attempt pass rate: 69%. NLP section (30–35%) was the highest-weighted
area and also where learners scored lowest on practice tests (average 55%).

---

## AI-103 — Azure AI Apps and Agents Developer Associate *(Beta)*

**beta: true**
**Replaces:** AI-102 (retired June 30, 2026)
**Expected GA:** Q4 2026 (subject to change)

**Level:** Associate
**Target roles:** AI Engineer
**Prerequisites:** AZ-900 (required); AI-901 (recommended)
**Recommended study hours:** 90 (estimated — beta content may expand)
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/ *(pending)*
**Passing score:** 700 / 1000 (provisional)

**lp_uids:**
- learn.wwl.develop-generative-ai-apps
- learn.wwl.develop-ai-agents-azure
- learn.wwl.develop-language-solutions-azure-ai
- learn.extract-insights-visual-data-azure

**Note:** LPs extracted from ILT course ai-103t00 (verified 2026-06-13). The certification
page renders these dynamically — pull from the static list above until a dedicated
self-paced collection is published in the catalog.

**What this certification validates:**
Designing and implementing enterprise-grade AI solutions on Azure AI Foundry. Building
agentic AI workflows with Azure AI Agent Service and the Semantic Kernel SDK. Implementing
multimodal AI solutions covering vision, speech, and language with the unified Azure AI
Services portfolio. Applying responsible AI and content safety controls at scale.
Knowledge mining with Azure AI Search, document intelligence, and RAG pipelines.
Integrating Azure OpenAI models into production applications with grounding and evaluation.

**Exam skill areas (preliminary):**
- Plan and manage Azure AI solutions (15–20%)
- Implement generative AI and agentic solutions (25–30%)
- Implement computer vision solutions (10–15%)
- Implement natural language processing solutions (20–25%)
- Implement knowledge mining and document intelligence (10–15%)
- Apply responsible AI and content safety (10–15%)

**Enterprise observations:**
Beta — no enterprise pass rate data. Early preview access available through Microsoft
Learn beta exam program. Recommend enrolling early adopters on the AI Engineer track
to validate readiness before GA.

---

## AI-901 — Microsoft Azure AI Fundamentals *(Beta)*

**beta: true**
**Replaces:** AI-900 (expected retirement aligned with AI-102 successor track)
**Expected GA:** Q1 2027 (subject to change)

**Level:** Fundamentals
**Target roles:** All roles exploring AI; prerequisite for AI-103
**Prerequisites:** None
**Recommended study hours:** 20 (estimated)
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/ *(pending)*
**Passing score:** 700 / 1000 (provisional)

**lp_uids:** []
**Note:** Learning paths not yet published in the MS Learn Catalog.

**What this certification validates:**
Foundational understanding of Azure AI Foundry, Azure OpenAI Service, and the Azure AI
Services portfolio. Core responsible AI concepts aligned to the Microsoft Responsible AI
Standard. Generative AI concepts: LLMs, prompting, RAG, and grounding. Introduction to
agentic AI patterns and orchestration frameworks. Azure AI Search and multimodal AI
capabilities overview.

**Exam skill areas (preliminary):**
- Describe AI concepts and Azure AI services (25–30%)
- Describe generative AI capabilities on Azure (30–35%)
- Describe responsible AI principles and practices (20–25%)
- Describe agentic AI concepts (15–20%)

**Enterprise observations:**
Beta — no enterprise pass rate data. Designed as the new fundamentals on-ramp for the
AI track. Recommend pairing with hands-on Azure AI Foundry playground sessions.

---

## AI-200 — Microsoft Certified: Azure AI Cloud Developer Associate *(Beta)*

**beta: true**
**Replaces:** AZ-204 (retiring July 31, 2026)

**Level:** Associate
**Target roles:** Developer, Software Engineer (AI-focused backend)
**Prerequisites:** Python proficiency required; Azure SDK and data services experience; AZ-900 recommended
**Recommended study hours:** 90 (estimated)
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-cloud-developer-associate/
**Passing score:** 700 / 1000 (provisional — beta exams not scored immediately)
**Exam duration:** 120 minutes

**lp_uids:**
- learn.wwl.get-started-ai-apps-agents
- learn.wwl.az-204-implement-iaas-solutions
- learn.wwl.develop-ai-solutions-azure-cosmos-db
- learn.wwl.develop-ai-solutions-azure-database-postgresql
- learn.wwl.az-204-develop-message-based-solutions
- learn.wwl.az-204-implement-api-management
- learn.wwl.az-204-implement-secure-cloud-solutions
- learn.wwl.az-204-instrument-solutions-to-support-monitoring-logging

**What this certification validates:**
Designing, building, and implementing AI solutions on Azure with a focus on back-end
services and scalable architectures. Developing containerized solutions: Docker, Azure
Container Apps, and AKS integration. Developing AI solutions using Azure data management
services: Cosmos DB for NoSQL, Azure Database for PostgreSQL, and vector databases for
RAG patterns. Connecting to and consuming Azure services: Service Bus, Event Grid,
Event Hubs, and API Management. Securing, monitoring, and troubleshooting Azure AI
solutions: Key Vault, managed identities, Application Insights, and Azure Monitor.

**Exam skill areas:**
- Develop containerized solutions on Azure (20–25%)
- Develop AI solutions using Azure data management services (25–30%)
- Connect to and consume Azure services (25–30%)
- Secure, monitor, and troubleshoot Azure solutions (20–25%)

**Enterprise observations:**
Beta — no enterprise pass rate data. Positioned as the AI-era replacement for AZ-204,
extending developer skills into AI backend patterns (vector databases, AI SDK integration,
RAG pipelines) while retaining the core AZ-204 competencies around containers, messaging,
and API management. Developers holding AZ-204 should plan AI-200 certification before
the July 31, 2026 AZ-204 retirement deadline.

---

## AZ-308 — Designing Microsoft Azure AI Infrastructure Solutions *(Beta)*

**beta: true**
**New role:** Architect-level AI infrastructure — complements AZ-305 for AI-heavy workloads
**Expected GA:** Q4 2026 (subject to change)

**Level:** Expert
**Target roles:** Solutions Architect, AI Platform Architect
**Prerequisites:** AZ-305 (required); AI-200 or AI-103 (recommended)
**Recommended study hours:** 130 (estimated)
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/ *(pending)*
**Passing score:** 700 / 1000 (provisional)

**lp_uids:** []
**Note:** Learning paths not yet published in the MS Learn Catalog.

**What this certification validates:**
Designing enterprise AI architectures on Azure: hub-and-spoke AI platform topologies,
multi-region AI deployments, and Azure AI Foundry project organization. Architecting
data foundations for AI: data lakehouse design, vector store strategy, and real-time
feature engineering. Designing secure AI systems: private endpoints for AI services,
managed virtual networks, and AI content safety architecture. Planning for AI cost
governance: reserved capacity for AI compute, token throughput planning, and
chargeback models for internal AI platforms.

**Exam skill areas (preliminary):**
- Design AI platform architecture and governance (30–35%)
- Design data and knowledge architecture for AI (25–30%)
- Design AI security and compliance architecture (20–25%)
- Design AI cost and operational architecture (15–20%)

**Enterprise observations:**
Beta — no enterprise pass rate data. Positioned as the AI-specialized architect cert
alongside AZ-305. Ideal target for senior architects leading internal Azure AI platform
initiatives. Expected to become a prerequisite for AI Center of Excellence leadership roles.

---

## DP-100 — Designing and Implementing a Data Science Solution on Azure

**retired: true**
**Replaced by:** AI-300 — see profile below

**Level:** Associate
**Target roles:** Data Scientist, ML Engineer
**Prerequisites:** AZ-900 (recommended); Python and ML fundamentals required
**Recommended study hours:** 100
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-data-scientist/
**Passing score:** 700 / 1000

**lp_uids:** []
**Note:** Microsoft retired this certification and removed its training collection.
Do NOT recommend to learners — direct them to AI-300 instead.

**What this certification validated (historical reference):**
Designing and preparing Azure Machine Learning workspaces and compute. Exploring and
preparing data with Python and MLflow. Training, evaluating, and selecting models using
Azure ML automated ML and pipelines. Deploying models to real-time and batch inference
endpoints. Monitoring and retraining deployed models. Optimizing language models for
AI applications using Azure AI Foundry.

**Exam skill areas (historical):**
- Design and prepare a machine learning solution (20–25%)
- Explore data and run experiments (25–30%)
- Train and deploy models (35–40%)
- Optimize language models for AI applications (10–15%)

**Enterprise observations (historical):**
Average first-attempt pass rate: 63%. Hands-on Azure ML experience was the strongest
predictor of success. Learners without active ML project experience rarely passed on
the first attempt.

---

## AI-300 — Microsoft Certified: Machine Learning Operations Engineer Associate

**Replaces:** DP-100 (retired)

**Level:** Associate
**Target roles:** ML Engineer, MLOps Engineer, AI Platform Engineer
**Prerequisites:** Python proficiency required; Azure ML and entry-level DevOps experience; AI-103 or equivalent recommended
**Recommended study hours:** 90
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/operationalizing-machine-learning-and-generative-ai-solutions/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months
**Exam duration:** 120 minutes

**lp_uids:**
- learn.wwl.introduction-machine-learn-operations
- learn.wwl.build-first-machine-operations-workflow
- learn.wwl.operationalize-gen-ai-apps
- learn.azure.operationalize-ai-responsibly

**What this certification validates:**
Designing and implementing MLOps infrastructure on Azure Machine Learning: workspaces,
compute clusters, registries, and pipelines as code with GitHub Actions and Bicep.
Implementing ML model lifecycle: training automation, experiment tracking with MLflow,
model registration, packaging, and deployment to real-time and batch endpoints.
Designing GenAIOps infrastructure on Microsoft Foundry: prompt flows, evaluation
pipelines, and agent deployment. Implementing generative AI quality assurance:
content safety, output evaluation, and responsible AI observability dashboards.
Optimizing generative AI systems: fine-tuning, RAG pipeline optimization, and
throughput/cost governance.

**Exam skill areas:**
- Design and implement an MLOps infrastructure (20–25%)
- Implement machine learning model lifecycle and operations (25–30%)
- Design and implement a GenAIOps infrastructure (20–25%)
- Implement generative AI quality assurance and observability (15–20%)
- Optimize generative AI systems and model performance (10–15%)

**Enterprise observations:**
New cert — no enterprise pass rate data yet. Bridges the gap between data scientists
(who build models) and platform engineers (who operate AI at scale). Ideal next step
for engineers after AI-103 who want to specialize in AI platform operations. Exam is
currently available only in English.

---

## DP-203 — Microsoft Azure Data Engineer Associate

**retired: true**
**Replaced by:** DP-700 — see profile below

**Level:** Associate
**Target roles:** Data Engineer
**Prerequisites:** AZ-900 (recommended)
**Recommended study hours:** 100
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/azure-data-engineer/
**Passing score:** 700 / 1000

**lp_uids:**
- learn.wwl.get-started-data-engineering
- learn.wwl.data-integration-scale-azure-data-factory

**What this certification validates:**
Designing and implementing data storage with Azure Data Lake Storage Gen2, Azure Synapse
Analytics, and Azure Databricks. Developing data processing solutions with Azure Data
Factory, Synapse pipelines, and Apache Spark. Implementing data security: encryption,
masking, row-level security, and RBAC for data resources. Monitoring and optimizing
storage and processing performance. Designing real-time analytics solutions with
Azure Stream Analytics and Event Hubs.

**Exam skill areas:**
- Design and implement data storage (40–45%)
- Develop data processing (25–30%)
- Secure, monitor, and optimize data storage and data processing (30–35%)

**Enterprise observations:**
Average first-attempt pass rate: 67%. Jordan R. (EMP-002) scored 672 on first attempt
(passing: 700) — weak areas were real-time ingestion, stream analytics, and
lakehouse optimization. Team average on real-time ingestion practice tests: 49%.
Recommended: allocate 25% of study time specifically to Stream Analytics and
Event Hubs before attempting the exam.

---

## DP-700 — Microsoft Fabric Data Engineer Associate

**Replaces:** DP-203 (retired)

**Level:** Associate
**Target roles:** Data Engineer
**Prerequisites:** AZ-900 (recommended); familiarity with data engineering concepts
**Recommended study hours:** 80
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/fabric-data-engineer-associate/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months

**lp_uids:** []
**Note:** Learning paths not yet fully published in the MS Learn Catalog. Monitor for updates.

**What this certification validates:**
Designing and implementing data engineering solutions on Microsoft Fabric. Ingesting,
transforming, and orchestrating data using Fabric pipelines, notebooks, and dataflows.
Building and managing lakehouses with OneLake, Delta tables, and shortcuts. Implementing
real-time intelligence with Fabric Eventstream and KQL databases. Securing and monitoring
Fabric data engineering workloads: workspace permissions, sensitivity labels, and
Fabric capacity management.

**Exam skill areas:**
- Implement and manage a data engineering solution (35–40%)
- Ingest and transform data (30–35%)
- Monitor and optimize data engineering solutions (15–20%)
- Implement security for data engineering (10–15%)

**Enterprise observations:**
Replaces DP-203 as the primary data engineering certification. Focuses entirely on the
Microsoft Fabric stack rather than Azure Synapse and Data Factory. Engineers holding
DP-203 should plan to certify on DP-700 as Fabric becomes the enterprise data platform
standard. No enterprise pass rate data yet — early adopters recommended for the team.

---

## DP-750 — Microsoft Certified: Azure Databricks Data Engineer Associate

**Level:** Associate
**Target roles:** Data Engineer (Databricks specialization)
**Prerequisites:** Python and SQL proficiency required; experience with Azure Data Factory, Microsoft Entra, Azure Monitor; Git/SDLC familiarity
**Recommended study hours:** 95
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/implementing-data-engineering-solutions-using-azure-databricks/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months
**Exam duration:** 120 minutes

**lp_uids:**
- learn.wwl.azure-databricks-data-engineer-setup-configure-environment
- learn.wwl.azure-databricks-data-engineer-secure-govern-unity-catalog
- learn.wwl.azure-databricks-data-engineer-prepare-process-data
- learn.wwl.azure-databricks-data-engineer-deploy-maintain-data-pipelines-workloads

**What this certification validates:**
Configuring and setting up Azure Databricks environments: workspaces, clusters, Databricks
Runtime, and Unity Catalog metastore setup. Securing and governing Unity Catalog objects:
schemas, tables, volumes, external locations, and row/column-level security. Preparing
and processing data with Databricks: ingestion with Auto Loader, Delta Lake, DLT pipelines,
SQL and Python transformations, and data quality with expectations. Deploying and
maintaining data pipelines and workloads: Databricks Workflows, job scheduling, monitoring
with Azure Monitor, and performance optimization for streaming and batch workloads.

**Exam skill areas:**
- Configure and set up an Azure Databricks environment (20–25%)
- Secure and govern Unity Catalog objects (20–25%)
- Prepare and process data (25–30%)
- Implement and maintain data pipelines and workloads (25–30%)

**Enterprise observations:**
Databricks-focused cert — ideal for data engineers who work primarily on Databricks
rather than the broader Azure Synapse/Fabric stack. Complements DP-700 for teams
that use both Databricks and Microsoft Fabric. No enterprise pass rate data yet.
Recommend pairing with a Databricks Community Edition workspace for hands-on practice
with Delta Live Tables and Unity Catalog before the exam.

---

## DP-600 — Microsoft Fabric Analytics Engineer Associate

**Level:** Associate
**Target roles:** Data Engineer (specialization)
**Prerequisites:** DP-203 (required)
**Recommended study hours:** 80
**Microsoft Learn URL:** https://learn.microsoft.com/en-us/credentials/certifications/fabric-analytics-engineer-associate/
**Passing score:** 700 / 1000
**Renewal:** Every 24 months

**lp_uids:**
- learn.wwl.implement-data-science-machine-learning-fabric
- learn.wwl.explore-analytics-data-stores
- learn.wwl.design-transform-analytics-data
- learn.wwl.prepare-ai-ready-analytics-data
- learn-wwl.work-with-data-warehouses-using-microsoft-fabric
- learn-wwl.implement-operational-databases-in-microsoft-fabric
- learn.wwl.ingest-data-with-microsoft-fabric
- learn.wwl.secure-govern-analytics-data

**What this certification validates:**
Implementing and managing Microsoft Fabric workspaces and capacities. Ingesting and
transforming data using Fabric pipelines, dataflows, and notebooks. Implementing
lakehouse analytics with Delta tables, shortcuts, and OneLake. Deploying and
managing semantic models and Power BI datasets. Creating and managing dataflows
for self-service data preparation.

**Exam skill areas:**
- Implement and manage Microsoft Fabric (25–30%)
- Ingest and transform data (25–30%)
- Implement and manage semantic models (20–25%)
- Explore and analyze data in Microsoft Fabric (20–25%)

**Enterprise observations:**
Newer cert in the catalog. Early adopters on the team show high motivation.
No enterprise pass rate data yet. Recommend pairing DP-600 study with the
Microsoft Fabric community resources and the free Fabric trial workspace for
hands-on practice with lakehouses and semantic models.
