"use client";

import { useState } from "react";

interface LearningPathItem {
  resource_id: string;
  title: string;
  cert_id: string;
  estimated_hours: number;
  source_url: string;
  domain_name: string | null;
  exam_weight: number | null;
  citations?: string[];
}

interface DomainWeight {
  domain_name: string;
  exam_weight: number;
  level?: string;
  products?: string[];
  icon_url?: string;
}

interface LPGroup {
  domain_name: string;
  exam_weight: number | null;
  total_hours: number;
  modules: LearningPathItem[];
  level?: string;
  products?: string[];
  icon_url?: string;
}

interface CourseSectionProps {
  certName: string;
  certId: string;
  items: LearningPathItem[];
  priorityDomains?: DomainWeight[];
}

function groupByLP(items: LearningPathItem[], domains: DomainWeight[]): LPGroup[] {
  const domainMeta = new Map(domains.map((d) => [d.domain_name, d]));
  const map = new Map<string, LPGroup>();

  for (const item of items) {
    const key = item.domain_name ?? "General";
    if (!map.has(key)) {
      const meta = domainMeta.get(key);
      map.set(key, {
        domain_name: key,
        exam_weight: item.exam_weight,
        total_hours: 0,
        modules: [],
        level: meta?.level,
        products: meta?.products,
        icon_url: meta?.icon_url,
      });
    }
    const group = map.get(key)!;
    group.modules.push(item);
    group.total_hours = Math.round((group.total_hours + item.estimated_hours) * 10) / 10;
  }
  return Array.from(map.values());
}

const LEVEL_COLORS: Record<string, string> = {
  beginner: "bg-emerald-50 text-emerald-700",
  intermediate: "bg-blue-50 text-blue-700",
  advanced: "bg-violet-50 text-violet-700",
};

function LPCard({ group }: { group: LPGroup }) {
  const [expanded, setExpanded] = useState(true);
  const weightPct = group.exam_weight ? Math.round(group.exam_weight * 100) : null;
  const levelLabel = group.level ?? "";
  const levelClass = LEVEL_COLORS[levelLabel] ?? "bg-slate-100 text-slate-600";

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* LP header */}
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
        <div className="flex items-start gap-2.5">
          {group.icon_url && (
            <img
              src={group.icon_url}
              alt=""
              className="h-8 w-8 rounded shrink-0 object-contain mt-0.5"
            />
          )}
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-slate-800 leading-snug">
              {group.domain_name}
            </h4>
            <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
              {levelLabel && (
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${levelClass}`}>
                  {levelLabel}
                </span>
              )}
              {group.products?.map((p) => (
                <span
                  key={p}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 capitalize"
                >
                  {p.replace(/-/g, " ")}
                </span>
              ))}
            </div>
          </div>
          {weightPct !== null && (
            <span className="shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
              {weightPct}%
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
          <span>{group.modules.length} modules</span>
          <span>·</span>
          <span>{group.total_hours}h</span>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="ml-auto text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
          >
            {expanded ? "Hide" : "Show"}
          </button>
        </div>
      </div>

      {/* Scrollable module list */}
      {expanded && (
        <div className="overflow-y-auto max-h-52 divide-y divide-slate-100">
          {group.modules.map((mod) => (
            <a
              key={mod.resource_id}
              href={mod.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-4 py-2.5 hover:bg-blue-50 transition-colors group"
            >
              <span className="flex-1 text-xs text-slate-700 leading-snug group-hover:text-blue-700">
                {mod.title}
              </span>
              <span className="shrink-0 text-xs text-slate-400">{mod.estimated_hours}h</span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 16 16"
                fill="currentColor"
                className="h-3 w-3 shrink-0 text-slate-300 group-hover:text-blue-500"
              >
                <path
                  fillRule="evenodd"
                  d="M4.75 3.75a.75.75 0 000 1.5h4.19L3.22 11.03a.75.75 0 101.06 1.06l5.72-5.72v4.19a.75.75 0 001.5 0v-6a.75.75 0 00-.75-.75h-6z"
                  clipRule="evenodd"
                />
              </svg>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CourseSection({
  certName,
  certId,
  items,
  priorityDomains = [],
}: CourseSectionProps) {
  const groups = groupByLP(items, priorityDomains);
  const totalHours = Math.round(groups.reduce((s, g) => s + g.total_hours, 0) * 10) / 10;
  const totalModules = items.length;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Course header */}
      <div className="px-6 py-5 bg-gradient-to-r from-blue-600 to-blue-500">
        <div className="flex items-center gap-2 mb-1">
          <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-semibold text-white uppercase tracking-wider">
            Course
          </span>
          <span className="text-xs font-medium text-blue-100 uppercase tracking-wider">
            {certId}
          </span>
        </div>
        <h3 className="text-base font-bold text-white leading-snug">{certName}</h3>
        <div className="flex items-center gap-3 mt-2 text-xs text-blue-100">
          <span>{groups.length} learning paths</span>
          <span>·</span>
          <span>{totalModules} modules</span>
          <span>·</span>
          <span>{totalHours}h total</span>
        </div>
      </div>

      {/* LP cards grid */}
      <div className="p-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {groups.map((group) => (
          <LPCard key={group.domain_name} group={group} />
        ))}
      </div>
    </div>
  );
}
