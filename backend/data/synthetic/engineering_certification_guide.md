# Azure Certification Guide for Engineering Roles
_Synthetic document — all data is illustrative and not sourced from real performance records._

## Role to Azure Certification Mapping

| Engineering Role | Primary Certification | Secondary Certification | Notes |
|---|---|---|---|
| Cloud Engineer | AZ-104 (Azure Administrator) | AZ-305 (Solutions Architect Expert) | AZ-104 is the foundational ops cert for cloud engineers |
| Data Engineer | DP-203 (Azure Data Engineer Associate) | DP-600 (Fabric Analytics Engineer) | Start with DP-203; DP-600 recommended for Fabric platform work |
| AI Engineer | AI-102 (Azure AI Engineer Associate) | AZ-104 | AI-102 requires Azure fundamentals — pair with AZ-900 first for juniors |
| Solutions Architect | AZ-305 (Azure Solutions Architect Expert) | AZ-500 (Security Engineer Associate) | Requires AZ-104 as prerequisite |
| DevOps Engineer | AZ-400 (Azure DevOps Engineer Expert) | AZ-104 | AZ-400 requires either AZ-104 or AZ-204 as prerequisite |
| Security Engineer | AZ-500 (Azure Security Engineer Associate) | AZ-104 | Strong overlap with AZ-104 content |
| Developer | AZ-204 (Azure Developer Associate) | AZ-400 | AZ-204 covers SDK, functions, containers, and app services |

## Recommended Study Patterns by Role

### Cloud Engineer (AZ-104)
- Focus areas: identity and access management (20%), storage (15%), networking (25%), compute (25%), monitoring (15%)
- Best approach: hands-on labs with Azure Portal and CLI alongside reading
- Common weak areas: RBAC scope hierarchies, NSG vs firewall rule evaluation order
- Recommended sequence: Fundamentals module → Identity → Networking → Compute → Storage → Governance

### Data Engineer (DP-203)
- Focus areas: data storage design (40–45%), data processing (25–30%), data security (10–15%), monitoring and optimization (10–15%)
- Best approach: combine reading with Synapse Analytics and Data Factory lab environments
- Common weak areas: streaming with Stream Analytics, lakehouse optimization in Synapse
- Recommended sequence: Storage accounts → Data Factory → Synapse Analytics → Stream Analytics → Security

### AI Engineer (AI-102)
- Focus areas: Azure Cognitive Services (30%), Azure OpenAI Service (20%), Conversational AI (25%), Custom Vision / Document Intelligence (25%)
- Best approach: video walkthroughs followed by hands-on REST API exploration
- Common weak areas: responsible AI design principles, Speech Service configuration
- Recommended sequence: AZ-900 (if needed) → Cognitive Services overview → OpenAI integration → Bot Framework → Custom AI

### Solutions Architect (AZ-305)
- Focus areas: identity and access (25%), data storage (25%), business continuity (10–15%), infrastructure (35–40%)
- Best approach: practice tests and architecture case studies; scenario reasoning is heavily weighted
- Common weak areas: Well-Architected Framework trade-offs, cost optimisation patterns, SLA composition
- Recommended sequence: AZ-104 completion → WAF pillars study → Networking deep-dive → HA / DR patterns → Practice exams

### DevOps Engineer (AZ-400)
- Focus areas: source control (10%), CI/CD pipelines (40–45%), dependency management (10%), application configuration (10%), security (15–20%)
- Best approach: hands-on pipeline builds with Azure DevOps or GitHub Actions
- Common weak areas: compliance as code, security scanning integration, dependency vulnerability management
- Recommended sequence: AZ-104 or AZ-204 completion → Azure DevOps → GitHub Actions → Pipeline security → Compliance gates

## Estimated Study Hours per Certification

| Certification | Beginner | Intermediate | Advanced | Notes |
|---|---|---|---|---|
| AZ-900 | 20–30 h | 10–15 h | 5–8 h | Introductory only |
| AZ-104 | 80–100 h | 50–65 h | 30–40 h | Broad scope; hands-on time is critical |
| AZ-204 | 90–110 h | 60–75 h | 35–50 h | SDK + code-heavy; requires Python or C# familiarity |
| AZ-305 | 100–120 h | 70–85 h | 40–55 h | Requires AZ-104 as foundation |
| AZ-400 | 90–110 h | 60–70 h | 35–45 h | Requires AZ-104 or AZ-204 as foundation |
| AZ-500 | 80–100 h | 55–65 h | 30–40 h | Heavy overlap with AZ-104 content |
| DP-203 | 90–110 h | 60–70 h | 35–45 h | Requires SQL and data pipeline experience |
| AI-102 | 80–100 h | 55–65 h | 30–40 h | Requires Python and REST API experience |

## Prerequisite Certification Paths

```
AZ-900 (Fundamentals)
  └── AZ-104 (Administrator)
        ├── AZ-305 (Solutions Architect Expert)
        │     └── AZ-500 (Security Engineer)
        └── AZ-400 (DevOps Engineer Expert)

AZ-900 (Fundamentals)
  └── AZ-204 (Developer Associate)
        └── AZ-400 (DevOps Engineer Expert)

AZ-900 (Fundamentals)
  └── DP-203 (Data Engineer Associate)
        └── DP-600 (Fabric Analytics Engineer)

AZ-900 (Fundamentals)
  └── AI-102 (AI Engineer Associate)
```

## Readiness Thresholds

Learners are considered ready to sit an exam when:
- Practice test average score ≥ 75% across at least 3 full practice exams
- Weak areas reduced to ≤ 2 domains below threshold
- Minimum study hours completed for their level (see table above)
- Streak ≥ 14 consecutive study days in the 4 weeks preceding the exam
