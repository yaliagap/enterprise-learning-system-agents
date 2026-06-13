"use client";
import { useState } from "react";
import type { CuratorOutput } from "@/app/hooks/useAgentChat";

interface CuratorOutputCardProps {
  output: CuratorOutput;
}

export function CuratorOutputCard({ output }: CuratorOutputCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mb-2 w-full max-w-[85%] rounded-lg border border-slate-200 bg-slate-50 text-sm overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-slate-700 font-medium hover:bg-slate-100 transition-colors"
      >
        <span>📋 Curator Response</span>
        <span>{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <div className="px-3 pb-3 pt-1 border-t border-slate-200 space-y-3">
          <div className="flex flex-wrap gap-2">
            <div className="rounded-md bg-white border border-slate-200 px-3 py-2 flex-1 min-w-[120px]">
              <p className="text-xs text-slate-500 mb-0.5">Certification</p>
              <p className="text-sm font-semibold text-slate-800">{output.exam}</p>
            </div>
            <div className="rounded-md bg-white border border-slate-200 px-3 py-2 flex-1 min-w-[120px]">
              <p className="text-xs text-slate-500 mb-0.5">Level</p>
              <p className="text-sm font-semibold text-slate-800 capitalize">{output.user_level}</p>
            </div>
            <div className="rounded-md bg-white border border-slate-200 px-3 py-2 flex-1 min-w-[120px]">
              <p className="text-xs text-slate-500 mb-0.5">Learning Paths</p>
              <p className="text-sm font-semibold text-slate-800">{output.recommended_learning_paths.length}</p>
            </div>
          </div>

          {output.priority_domains.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 font-medium mb-1">Priority Domains</p>
              <ul className="space-y-1">
                {output.priority_domains.map((d, i) => (
                  <li key={i} className="flex items-center gap-2 text-xs">
                    <span className="w-[120px] shrink-0 text-slate-700 truncate">{d.domain_name}</span>
                    <div className="flex-1 bg-slate-200 rounded-full h-1.5">
                      <div
                        className="bg-amber-500 h-1.5 rounded-full"
                        style={{ width: `${Math.round(d.exam_weight * 100)}%` }}
                      />
                    </div>
                    <span className="text-slate-500 w-8 text-right">{Math.round(d.exam_weight * 100)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {output.coverage_summary && (
            <div>
              <p className="text-xs text-slate-500 font-medium mb-1">Coverage Summary</p>
              <p className="text-xs text-slate-600 whitespace-pre-wrap bg-white rounded p-2 border border-slate-200">
                {output.coverage_summary}
              </p>
            </div>
          )}

          {output.references && output.references.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 font-medium mb-1">
                Sources cited ({output.references.length})
              </p>
              <ul className="space-y-1">
                {output.references.map((ref, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs">
                    <span className="shrink-0 rounded px-1 bg-slate-100 text-slate-600">{ref.type}</span>
                    {ref.url?.startsWith("https://") ? (
                      <a
                        href={ref.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline break-all"
                      >
                        {ref.title}
                      </a>
                    ) : (
                      <span className="text-slate-600 break-all">{ref.title}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
