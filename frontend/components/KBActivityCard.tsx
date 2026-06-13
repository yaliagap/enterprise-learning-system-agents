"use client";
import { useState } from "react";
import type { KBActivity } from "@/app/hooks/useAgentChat";

interface KBActivityCardProps {
  activity: KBActivity;
}

export function KBActivityCard({ activity }: KBActivityCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mb-2 w-full max-w-[85%] rounded-lg border border-amber-200 bg-amber-50 text-sm overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-amber-700 font-medium hover:bg-amber-100 transition-colors"
      >
        <span>🔍 Foundry IQ - Knowledge Base</span>
        <span>{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <div className="px-3 pb-3 pt-1 border-t border-amber-200 space-y-3">
          <div>
            <p className="text-xs text-amber-600 font-medium mb-1">Query sent to KB</p>
            <p className="text-xs text-slate-600 whitespace-pre-wrap bg-white rounded p-2 border border-amber-100">{activity.query}</p>
          </div>
          {activity.response_text && (
            <div>
              <p className="text-xs text-amber-600 font-medium mb-1">KB Response</p>
              <p className="text-xs text-slate-600 whitespace-pre-wrap bg-white rounded p-2 border border-amber-100 max-h-48 overflow-y-auto">{activity.response_text}</p>
            </div>
          )}
          <div>
            <p className="text-xs text-amber-600 font-medium mb-1">
              References ({activity.references.length})
            </p>
            {activity.references.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No references retrieved from Knowledge Base</p>
            ) : (
              <ul className="space-y-1">
                {activity.references.map((ref, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs">
                    <span className="shrink-0 rounded px-1 bg-amber-100 text-amber-700">{ref.type}</span>
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
            )}
          </div>
        </div>
      )}
    </div>
  );
}
