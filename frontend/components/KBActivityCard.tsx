"use client";
import { useState } from "react";
import type { KBActivity } from "@/app/hooks/useAgentChat";

interface KBActivityCardProps {
  activity: KBActivity;
}

function parseRefIds(text: string): number[] {
  const matches = [...text.matchAll(/\[ref_id:(\d+)\]/g)];
  const unique = [...new Set(matches.map((m) => parseInt(m[1], 10)))];
  return unique.sort((a, b) => a - b);
}

export function KBActivityCard({ activity }: KBActivityCardProps) {
  const [expanded, setExpanded] = useState(false);
  const refIds = parseRefIds(activity.response_text ?? "");

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
              References ({refIds.length})
            </p>
            {refIds.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No references cited in KB response</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {refIds.map((id) => (
                  <span key={id} className="rounded px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[10px] font-mono">
                    ref_id:{id}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
