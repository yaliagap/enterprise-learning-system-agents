/**
 * Azure certification topic taxonomy — frontend mirror.
 * Backend source of truth: backend/workflow/topics.py — keep in sync.
 */

export interface AzureTopic {
  id: string;
  label: string;
  certFamily: "Fundamentals" | "Associate" | "Expert" | "Specialty";
}

export type TopicId =
  | "az900-cloud-concepts"
  | "az900-azure-architecture"
  | "az900-management-governance"
  | "az900-security-compliance"
  | "az900-pricing-support"
  | "az104-identity-access"
  | "az104-networking"
  | "az104-storage"
  | "az104-compute"
  | "az104-monitoring"
  | "az204-azure-compute"
  | "az204-storage-solutions"
  | "az204-security-solutions"
  | "az204-api-management"
  | "az204-event-driven"
  | "az204-caching-cdn"
  | "az305-identity-governance"
  | "az305-data-storage-design"
  | "az305-business-continuity"
  | "az305-infrastructure-design"
  | "az305-app-architecture"
  | "az305-migration"
  | "az400-devops-processes"
  | "az400-source-control"
  | "az400-ci-pipelines"
  | "az400-cd-release"
  | "az400-security-compliance"
  | "ai102-ai-workloads"
  | "ai102-computer-vision"
  | "ai102-nlp"
  | "ai102-knowledge-mining"
  | "ai102-conversational-ai"
  | "dp203-data-storage"
  | "dp203-data-processing"
  | "dp203-data-security";

export const AZURE_TOPICS: AzureTopic[] = [
  // AZ-900 — Fundamentals
  { id: "az900-cloud-concepts", label: "Cloud Concepts", certFamily: "Fundamentals" },
  { id: "az900-azure-architecture", label: "Azure Architecture & Services", certFamily: "Fundamentals" },
  { id: "az900-management-governance", label: "Management & Governance", certFamily: "Fundamentals" },
  { id: "az900-security-compliance", label: "Security, Compliance & Identity", certFamily: "Fundamentals" },
  { id: "az900-pricing-support", label: "Pricing & Support", certFamily: "Fundamentals" },
  // AZ-104 — Azure Administrator (Associate)
  { id: "az104-identity-access", label: "Identity & Access Management", certFamily: "Associate" },
  { id: "az104-networking", label: "Azure Networking", certFamily: "Associate" },
  { id: "az104-storage", label: "Azure Storage", certFamily: "Associate" },
  { id: "az104-compute", label: "Azure Compute (VMs, VMSS)", certFamily: "Associate" },
  { id: "az104-monitoring", label: "Monitoring & Backup", certFamily: "Associate" },
  // AZ-204 — Azure Developer (Associate)
  { id: "az204-azure-compute", label: "Azure Compute Solutions", certFamily: "Associate" },
  { id: "az204-storage-solutions", label: "Azure Storage Solutions", certFamily: "Associate" },
  { id: "az204-security-solutions", label: "Azure Security Solutions", certFamily: "Associate" },
  { id: "az204-api-management", label: "API Management & Integration", certFamily: "Associate" },
  { id: "az204-event-driven", label: "Event-Based & Message Solutions", certFamily: "Associate" },
  { id: "az204-caching-cdn", label: "Caching & CDN", certFamily: "Associate" },
  // AZ-305 — Azure Solutions Architect (Expert)
  { id: "az305-identity-governance", label: "Identity & Governance Design", certFamily: "Expert" },
  { id: "az305-data-storage-design", label: "Data Storage Design", certFamily: "Expert" },
  { id: "az305-business-continuity", label: "Business Continuity Design", certFamily: "Expert" },
  { id: "az305-infrastructure-design", label: "Infrastructure Solutions Design", certFamily: "Expert" },
  { id: "az305-app-architecture", label: "Application Architecture Design", certFamily: "Expert" },
  { id: "az305-migration", label: "Migration Design", certFamily: "Expert" },
  // AZ-400 — Azure DevOps Engineer (Expert)
  { id: "az400-devops-processes", label: "DevOps Processes & Agile", certFamily: "Expert" },
  { id: "az400-source-control", label: "Source Control Management", certFamily: "Expert" },
  { id: "az400-ci-pipelines", label: "CI Pipeline Design", certFamily: "Expert" },
  { id: "az400-cd-release", label: "CD & Release Management", certFamily: "Expert" },
  { id: "az400-security-compliance", label: "Security & Compliance in DevOps", certFamily: "Expert" },
  // AI-102 — Azure AI Engineer (Associate)
  { id: "ai102-ai-workloads", label: "AI Workloads & Considerations", certFamily: "Associate" },
  { id: "ai102-computer-vision", label: "Computer Vision Solutions", certFamily: "Associate" },
  { id: "ai102-nlp", label: "Natural Language Processing", certFamily: "Associate" },
  { id: "ai102-knowledge-mining", label: "Knowledge Mining", certFamily: "Associate" },
  { id: "ai102-conversational-ai", label: "Conversational AI", certFamily: "Associate" },
  // DP-203 — Azure Data Engineer (Associate)
  { id: "dp203-data-storage", label: "Data Storage Design", certFamily: "Associate" },
  { id: "dp203-data-processing", label: "Data Processing & Pipelines", certFamily: "Associate" },
  { id: "dp203-data-security", label: "Data Security & Compliance", certFamily: "Associate" },
];

export type CertFamily = AzureTopic["certFamily"];

export const CERT_FAMILY_ORDER: CertFamily[] = ["Fundamentals", "Associate", "Expert", "Specialty"];

/**
 * Returns topics grouped by cert family, in the display order defined by
 * CERT_FAMILY_ORDER. Families with no topics are omitted.
 */
export function getTopicsByFamily(): Map<CertFamily, AzureTopic[]> {
  const map = new Map<CertFamily, AzureTopic[]>();
  for (const family of CERT_FAMILY_ORDER) {
    const filtered = AZURE_TOPICS.filter((t) => t.certFamily === family);
    if (filtered.length > 0) {
      map.set(family, filtered);
    }
  }
  return map;
}
