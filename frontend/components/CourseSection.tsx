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
  necessary_learn?: boolean;
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
  pathEfficiencyReasoning?: string;
  checkedModules?: Record<string, boolean>;
  onCheckedChange?: (resourceId: string) => void;
  locked?: boolean;
  onStartStudyPlan?: (checkedResourceIds: string[]) => void;
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

function ModuleRow({
  item,
  checked,
  onToggle,
  disabled,
}: {
  item: LearningPathItem;
  checked: boolean;
  onToggle: (resourceId: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 px-4 py-2.5 hover:bg-blue-50 transition-colors group">
      <input
        type="checkbox"
        checked={checked}
        onChange={() => onToggle(item.resource_id)}
        onClick={(e) => e.stopPropagation()}
        disabled={disabled}
        className="h-3.5 w-3.5 shrink-0 rounded accent-amber-500 cursor-pointer disabled:cursor-not-allowed"
        aria-label={`Mark "${item.title}" as ${checked ? "not needed" : "needed"}`}
      />
      <a
        href={item.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className={`flex flex-1 items-center gap-3 min-w-0 ${checked ? "" : "opacity-50"}`}
      >
        <span className={`flex-1 text-xs leading-snug group-hover:text-blue-700 ${checked ? "text-slate-700" : "text-slate-400"}`}>
          {item.title}
        </span>
        <span className={`shrink-0 text-xs ${checked ? "text-slate-400" : "text-slate-300"}`}>
          {item.estimated_hours}h
        </span>
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
    </div>
  );
}

function LPCard({
  group,
  checkedModules,
  onToggle,
  locked,
}: {
  group: LPGroup;
  checkedModules: Record<string, boolean>;
  onToggle: (resourceId: string) => void;
  locked?: boolean;
}) {
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
            <ModuleRow
              key={mod.resource_id}
              item={mod}
              checked={checkedModules[mod.resource_id] ?? true}
              onToggle={onToggle}
              disabled={locked}
            />
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
  pathEfficiencyReasoning = "",
  checkedModules: checkedModulesProp,
  onCheckedChange,
  locked,
  onStartStudyPlan,
}: CourseSectionProps) {
  const [reasoningExpanded, setReasoningExpanded] = useState(false);
  const [localChecked, setLocalChecked] = useState<Record<string, boolean>>(() =>
    items.reduce((acc, item) => ({ ...acc, [item.resource_id]: item.necessary_learn !== false }), {} as Record<string, boolean>)
  );
  const isControlled = checkedModulesProp !== undefined;
  const checkedModules = isControlled ? checkedModulesProp! : localChecked;

  const groups = groupByLP(items, priorityDomains);
  const totalHours = Math.round(groups.reduce((s, g) => s + g.total_hours, 0) * 10) / 10;
  const totalModules = items.length;

  const checkedItems = items.filter((item) => checkedModules[item.resource_id] ?? true);
  const personalizedHours = Math.round(checkedItems.reduce((s, i) => s + i.estimated_hours, 0) * 10) / 10;
  const personalizedModules = checkedItems.length;
  const personalizedPaths = new Set(checkedItems.map((i) => i.domain_name ?? "General")).size;

  function handleToggle(resourceId: string) {
    if (locked) return;
    if (isControlled) onCheckedChange?.(resourceId);
    else setLocalChecked((prev) => ({ ...prev, [resourceId]: !prev[resourceId] }));
  }

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
        <div className="flex items-center gap-2 mt-2 text-xs text-blue-200">
          <span className="uppercase tracking-wider font-medium text-blue-300">Official</span>
          <span>·</span>
          <span>{groups.length} learning paths</span>
          <span>·</span>
          <span>{totalModules} modules</span>
          <span>·</span>
          <span>{totalHours}h</span>
        </div>
        <div className="flex items-center gap-2 mt-1 text-xs">
          <span className="uppercase tracking-wider font-semibold text-amber-300">Personalized</span>
          <span className="text-blue-200">·</span>
          <span className="text-white font-medium">{personalizedPaths} learning paths</span>
          <span className="text-blue-200">·</span>
          <span className="text-white font-medium">{personalizedModules} modules</span>
          <span className="text-blue-200">·</span>
          <span className="text-white font-medium">{personalizedHours}h</span>
        </div>
      </div>

      {/* Path efficiency reasoning panel */}
      {pathEfficiencyReasoning && (
        <div className="mx-5 mt-4 mb-0 rounded-xl border border-amber-200 bg-amber-50 overflow-hidden">
          <button
            type="button"
            onClick={() => setReasoningExpanded((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-2.5 text-left"
          >
            <div className="flex items-center gap-2">
              <svg className="h-3.5 w-3.5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              <span className="text-xs font-semibold text-amber-700">Curator Reasoning · Path Efficiency</span>
            </div>
            <svg className={`h-3.5 w-3.5 text-amber-500 transition-transform ${reasoningExpanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {reasoningExpanded && (
            <div className="px-4 pb-3 border-t border-amber-100">
              <p className="text-xs text-amber-800 leading-relaxed mt-2">{pathEfficiencyReasoning}</p>
            </div>
          )}
        </div>
      )}

      {/* LP cards grid */}
      <div className="p-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {groups.map((group) => (
          <LPCard
            key={group.domain_name}
            group={group}
            checkedModules={checkedModules}
            onToggle={handleToggle}
            locked={locked}
          />
        ))}
      </div>

      {items.length > 0 && onStartStudyPlan && (
        <div className="px-5 pb-5">
          <button
            type="button"
            disabled={!!locked}
            onClick={() => {
              const checkedResourceIds = Object.entries(checkedModules)
                .filter(([, v]) => v)
                .map(([k]) => k);
              onStartStudyPlan(checkedResourceIds);
            }}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-6 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Build my intelligent study plan →
          </button>
        </div>
      )}
    </div>
  );
}
