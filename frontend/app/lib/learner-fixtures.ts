// ---------------------------------------------------------------------------
// Learner fixtures — typed mock data for multi-screen UX
// ---------------------------------------------------------------------------

const CERT_NAMES: Record<string, string> = {
  "AZ-900": "Azure Fundamentals",
  "AZ-104": "Azure Administrator",
  "AZ-204": "Azure Developer Associate",
  "AZ-305": "Azure Solutions Architect Expert",
  "AZ-400": "Azure DevOps Engineer Expert",
  "AI-900": "Azure AI Fundamentals",
  "AI-102": "Azure AI Engineer Associate",
  "DP-203": "Azure Data Engineer Associate",
  "DP-600": "Microsoft Fabric Analytics Engineer",
  "SC-900": "Microsoft Security Fundamentals",
};

export interface CertificationCatalogItem {
  cert_id: string;
  cert_name: string;
  status: "completed" | "in_progress" | "failed_attempt";
  completedAt?: string;
  failedAt?: string;
  score?: number;
  learningPath?: Array<{ title: string; estimated_hours: number; domain_name: string | null }>;
  studyPlan?: Array<{ date: string; hours: number; topics: string[] }>;
  engagementSummary?: { preferred_slot: string; reminders_sent: number; next_reminder: string | null };
  assessments?: Array<{ attempt: number; score: number; passed: boolean; weak_areas: string[] }>;
  overallProgress?: number;
}

export interface LearnerProfile {
  learner_id: string;
  roles: string[];
  seniority: string;
  team_id: string;
  streak_days: number;
  study_hours_per_week: number;
  readiness_score: number;
  progress: number;
  current_skills: string[];
  strongest_domains?: string[];
  certifications: CertificationCatalogItem[];
}

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

const LEARNERS: LearnerProfile[] = [
  // EMP-001 — Cloud Engineer / DevOps Engineer, mid
  {
    learner_id: "EMP-001",
    roles: ["Cloud Engineer", "DevOps Engineer"],
    seniority: "mid",
    team_id: "TEAM-A",
    streak_days: 12,
    study_hours_per_week: 6,
    readiness_score: 58,
    progress: 42,
    current_skills: ["python", "ci-cd", "azure-pipelines", "docker", "linux"],
    strongest_domains: ["CI/CD Pipelines", "Infrastructure as Code", "Container Technologies", "Azure DevOps"],
    certifications: [
      {
        cert_id: "AZ-900",
        cert_name: CERT_NAMES["AZ-900"],
        status: "completed",
        completedAt: "Aug 2024",
      },
      {
        cert_id: "AZ-104",
        cert_name: CERT_NAMES["AZ-104"],
        status: "in_progress",
        overallProgress: 42,
        learningPath: [
          { title: "Manage Azure identities and governance", estimated_hours: 8, domain_name: "Identity & Governance" },
          { title: "Implement and manage storage", estimated_hours: 6, domain_name: "Storage" },
          { title: "Deploy and manage Azure compute resources", estimated_hours: 10, domain_name: "Compute" },
        ],
        studyPlan: [
          { date: "2026-06-02", hours: 2, topics: ["RBAC", "Azure AD"] },
          { date: "2026-06-04", hours: 2, topics: ["Storage accounts", "Blob storage"] },
          { date: "2026-06-09", hours: 3, topics: ["VM deployment", "Scale sets"] },
          { date: "2026-06-11", hours: 2, topics: ["Load balancer", "App gateway"] },
        ],
        engagementSummary: {
          preferred_slot: "evening",
          reminders_sent: 4,
          next_reminder: "2026-06-16T19:00:00Z",
        },
        assessments: [
          { attempt: 1, score: 62, passed: false, weak_areas: ["identity", "governance"] },
          { attempt: 2, score: 74, passed: false, weak_areas: ["identity", "rbac-policies"] },
        ],
      },
      {
        cert_id: "AZ-400",
        cert_name: CERT_NAMES["AZ-400"],
        status: "in_progress",
        overallProgress: 5,
      },
    ],
  },

  // EMP-002 — Data Engineer, senior
  {
    learner_id: "EMP-002",
    roles: ["Data Engineer"],
    seniority: "senior",
    team_id: "TEAM-A",
    streak_days: 27,
    study_hours_per_week: 8,
    readiness_score: 71,
    progress: 68,
    current_skills: ["sql", "pyspark", "azure-synapse", "data-factory", "python"],
    strongest_domains: ["Azure Synapse Analytics", "Data Integration", "Batch Data Processing", "Python Data Engineering"],
    certifications: [
      {
        cert_id: "AZ-900",
        cert_name: CERT_NAMES["AZ-900"],
        status: "completed",
        completedAt: "Mar 2024",
      },
      {
        cert_id: "AZ-104",
        cert_name: CERT_NAMES["AZ-104"],
        status: "completed",
        completedAt: "Jul 2024",
      },
      {
        cert_id: "DP-203",
        cert_name: CERT_NAMES["DP-203"],
        status: "in_progress",
        overallProgress: 68,
        learningPath: [
          { title: "Design and implement data storage", estimated_hours: 10, domain_name: "Data Storage" },
          { title: "Develop data processing", estimated_hours: 12, domain_name: "Data Processing" },
          { title: "Secure, monitor and optimize data solutions", estimated_hours: 8, domain_name: "Security & Optimization" },
        ],
        studyPlan: [
          { date: "2026-06-10", hours: 3, topics: ["Stream Analytics", "Event Hub"] },
          { date: "2026-06-12", hours: 3, topics: ["Delta Lake", "Lakehouse patterns"] },
          { date: "2026-06-15", hours: 2, topics: ["Real-time ingestion patterns"] },
          { date: "2026-06-17", hours: 3, topics: ["Lakehouse optimization", "partitioning"] },
        ],
        engagementSummary: {
          preferred_slot: "morning",
          reminders_sent: 2,
          next_reminder: "2026-06-17T08:00:00Z",
        },
        assessments: [
          { attempt: 1, score: 68, passed: false, weak_areas: ["real-time-ingestion", "stream-analytics", "lakehouse-optimization"] },
        ],
      },
      {
        cert_id: "DP-600",
        cert_name: CERT_NAMES["DP-600"],
        status: "in_progress",
        overallProgress: 10,
      },
    ],
  },

  // EMP-003 — AI Engineer, junior
  {
    learner_id: "EMP-003",
    roles: ["AI Engineer"],
    seniority: "junior",
    team_id: "TEAM-A",
    streak_days: 3,
    study_hours_per_week: 4,
    readiness_score: 34,
    progress: 18,
    current_skills: ["python", "machine-learning", "azure-cognitive-services"],
    strongest_domains: ["Azure Cognitive Services", "Machine Learning Fundamentals", "Python Development"],
    certifications: [
      {
        cert_id: "AI-900",
        cert_name: CERT_NAMES["AI-900"],
        status: "completed",
        completedAt: "Jan 2025",
      },
      {
        cert_id: "AI-102",
        cert_name: CERT_NAMES["AI-102"],
        status: "in_progress",
        overallProgress: 18,
        learningPath: [
          { title: "Plan and manage an Azure AI solution", estimated_hours: 8, domain_name: "AI Solution Planning" },
          { title: "Implement computer vision solutions", estimated_hours: 10, domain_name: "Computer Vision" },
        ],
        studyPlan: [
          { date: "2026-06-13", hours: 2, topics: ["Azure AI services overview"] },
          { date: "2026-06-15", hours: 2, topics: ["Computer Vision API", "Custom Vision"] },
        ],
        engagementSummary: {
          preferred_slot: "afternoon",
          reminders_sent: 1,
          next_reminder: "2026-06-18T14:00:00Z",
        },
        assessments: [],
      },
      {
        cert_id: "AZ-900",
        cert_name: CERT_NAMES["AZ-900"],
        status: "in_progress",
        overallProgress: 8,
      },
    ],
  },

  // EMP-004 — Solutions Architect, senior
  {
    learner_id: "EMP-004",
    roles: ["Solutions Architect"],
    seniority: "senior",
    team_id: "TEAM-A",
    streak_days: 45,
    study_hours_per_week: 5,
    readiness_score: 82,
    progress: 75,
    current_skills: ["azure-architecture", "networking", "security", "cost-management", "high-availability"],
    strongest_domains: ["Azure Networking", "Azure Security", "High Availability and Disaster Recovery", "Azure Resource Management"],
    certifications: [
      {
        cert_id: "AZ-900",
        cert_name: CERT_NAMES["AZ-900"],
        status: "completed",
        completedAt: "Feb 2023",
      },
      {
        cert_id: "AZ-104",
        cert_name: CERT_NAMES["AZ-104"],
        status: "completed",
        completedAt: "Aug 2023",
      },
      {
        cert_id: "AZ-204",
        cert_name: CERT_NAMES["AZ-204"],
        status: "completed",
        completedAt: "Mar 2024",
      },
      {
        cert_id: "AZ-305",
        cert_name: CERT_NAMES["AZ-305"],
        status: "in_progress",
        overallProgress: 75,
        learningPath: [
          { title: "Design identity, governance, and monitoring solutions", estimated_hours: 10, domain_name: "Identity & Governance" },
          { title: "Design data storage solutions", estimated_hours: 8, domain_name: "Data Storage" },
          { title: "Design business continuity solutions", estimated_hours: 6, domain_name: "Business Continuity" },
          { title: "Design infrastructure solutions", estimated_hours: 10, domain_name: "Infrastructure" },
          { title: "Well-Architected Framework review", estimated_hours: 6, domain_name: "Architecture Governance" },
        ],
        studyPlan: [
          { date: "2026-06-08", hours: 3, topics: ["Identity federation", "Conditional Access"] },
          { date: "2026-06-10", hours: 2, topics: ["Storage redundancy", "geo-replication"] },
          { date: "2026-06-12", hours: 3, topics: ["Disaster recovery", "backup strategies"] },
          { date: "2026-06-14", hours: 3, topics: ["Hub-spoke networking", "ExpressRoute"] },
          { date: "2026-06-16", hours: 2, topics: ["Cost optimization", "WAF pillars"] },
        ],
        engagementSummary: {
          preferred_slot: "morning",
          reminders_sent: 6,
          next_reminder: "2026-06-16T09:00:00Z",
        },
        assessments: [
          { attempt: 1, score: 78, passed: true, weak_areas: ["cost-management"] },
        ],
      },
    ],
  },

  // EMP-005 — DevOps Engineer / Cloud Engineer, mid
  {
    learner_id: "EMP-005",
    roles: ["DevOps Engineer", "Cloud Engineer"],
    seniority: "mid",
    team_id: "TEAM-A",
    streak_days: 8,
    study_hours_per_week: 5,
    readiness_score: 50,
    progress: 35,
    current_skills: ["github-actions", "terraform", "kubernetes", "azure-devops", "monitoring"],
    strongest_domains: ["Continuous Integration", "Continuous Delivery", "Kubernetes", "Infrastructure Monitoring", "Terraform"],
    certifications: [
      {
        cert_id: "AZ-900",
        cert_name: CERT_NAMES["AZ-900"],
        status: "completed",
        completedAt: "Nov 2024",
      },
      {
        cert_id: "AZ-400",
        cert_name: CERT_NAMES["AZ-400"],
        status: "in_progress",
        overallProgress: 35,
        learningPath: [
          { title: "Configure processes and communications", estimated_hours: 6, domain_name: "Processes" },
          { title: "Design and implement source control strategies", estimated_hours: 8, domain_name: "Source Control" },
          { title: "Design and implement build and release pipelines", estimated_hours: 12, domain_name: "Pipelines" },
          { title: "Develop a security and compliance plan", estimated_hours: 8, domain_name: "Security & Compliance" },
        ],
        studyPlan: [
          { date: "2026-06-08", hours: 2, topics: ["GitHub Actions workflows"] },
          { date: "2026-06-11", hours: 3, topics: ["Pipeline security", "branch policies"] },
          { date: "2026-06-14", hours: 2, topics: ["Container scanning", "SAST integration"] },
        ],
        engagementSummary: {
          preferred_slot: "evening",
          reminders_sent: 3,
          next_reminder: "2026-06-17T19:00:00Z",
        },
        assessments: [
          { attempt: 1, score: 65, passed: false, weak_areas: ["security-scanning", "compliance-as-code"] },
        ],
      },
      {
        cert_id: "AZ-104",
        cert_name: CERT_NAMES["AZ-104"],
        status: "in_progress",
        overallProgress: 12,
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Lookup helper
// ---------------------------------------------------------------------------

export function getLearnerProfile(id: string): LearnerProfile | null {
  return LEARNERS.find((l) => l.learner_id === id.toUpperCase()) ?? null;
}
