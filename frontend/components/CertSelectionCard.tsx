"use client";

import type { CertOption } from "@/app/hooks/useAgentChat";

interface CertSelectionCardProps {
  options: CertOption[];
  onSelect: (certId: string) => void;
}

const LEVEL_STYLES: Record<string, string> = {
  fundamentals: "bg-emerald-100 text-emerald-700",
  associate: "bg-blue-100 text-blue-700",
  expert: "bg-purple-100 text-purple-700",
};

function getLevelStyle(level: string): string {
  return LEVEL_STYLES[level.toLowerCase()] ?? "bg-slate-100 text-slate-600";
}

export function CertSelectionCard({ options, onSelect }: CertSelectionCardProps) {
  if (options.length === 0) return null;

  return (
    <div className="mb-2 w-full max-w-[85%] space-y-2">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-1">
        Choose a certification
      </p>
      {options.map((cert) => (
        <div
          key={cert.cert_id}
          className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden"
        >
          {/* Card header */}
          <div className="flex items-center gap-2 px-3 pt-3 pb-2">
            <span className="rounded-md bg-amber-100 text-amber-800 px-2 py-0.5 text-xs font-bold tracking-wide">
              {cert.cert_id}
            </span>
            <span className="text-sm font-semibold text-slate-800 flex-1 leading-tight">
              {cert.name}
            </span>
            {cert.level && (
              <span
                className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${getLevelStyle(cert.level)}`}
              >
                {cert.level}
              </span>
            )}
          </div>

          {/* Description */}
          {cert.description && (
            <p className="px-3 pb-2 text-xs text-slate-600 line-clamp-3 leading-relaxed">
              {cert.description}
            </p>
          )}

          {/* Recommendation bar */}
          <div className="px-3 pb-2">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-500 shrink-0">Match</span>
              <div className="flex-1 bg-slate-200 rounded-full h-1.5">
                <div
                  className="bg-amber-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, Math.round(cert.recommendation_pct)))}%` }}
                />
              </div>
              <span className="text-slate-600 font-medium w-8 text-right shrink-0">
                {Math.round(cert.recommendation_pct)}%
              </span>
            </div>
          </div>

          {/* Footer: badges + actions */}
          <div className="flex items-center justify-between gap-2 px-3 pb-3">
            <div className="flex items-center gap-2">
              {cert.already_obtained && (
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 text-slate-500 px-2 py-0.5 text-xs font-medium">
                  Already obtained ✓
                </span>
              )}
              {cert.ms_learn_url.startsWith("https://") && (
                <a
                  href={cert.ms_learn_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline"
                >
                  MS Learn ↗
                </a>
              )}
            </div>
            <button
              type="button"
              disabled={cert.already_obtained}
              onClick={() => onSelect(cert.cert_id)}
              className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors
                ${cert.already_obtained
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                  : "bg-blue-600 text-white hover:bg-blue-700"
                }`}
            >
              Select
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
