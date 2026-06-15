"use client";

import { useState } from "react";
import type {
  AdvisorResult,
  AdvisorDomainAnalysis,
  AdvisorRecommendation,
  AdvisorReviewArea,
  AdvisorStrongArea,
  PatternType,
} from "@/app/lib/advisor-types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AdvisorViewProps {
  advisorResult: AdvisorResult | null;
  onFinalize: () => void;
}

// ---------------------------------------------------------------------------
// Pattern badge
// ---------------------------------------------------------------------------

function PatternBadge({ pattern }: { pattern: PatternType }) {
  if (pattern === "none") return null;

  const styles: Record<string, string> = {
    conceptual_gap: "bg-amber-100 text-amber-700 border border-amber-200",
    application_gap: "bg-purple-100 text-purple-700 border border-purple-200",
    scenario_gap:   "bg-blue-100 text-blue-700 border border-blue-200",
    bloom_gap:      "bg-purple-100 text-purple-700 border border-purple-200",
  };

  const labels: Record<string, string> = {
    conceptual_gap:  "Conceptual gap",
    application_gap: "Application gap",
    scenario_gap:    "Scenario gap",
    bloom_gap:       "Bloom gap",
  };

  return (
    <span className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${styles[pattern] ?? "bg-slate-100 text-slate-600"}`}>
      {labels[pattern] ?? pattern}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Domain analysis row
// ---------------------------------------------------------------------------

function DomainRow({ domain }: { domain: AdvisorDomainAnalysis }) {
  const isStrong = domain.learner_score >= 85;
  const isWeak = domain.learner_score < 70;

  return (
    <div className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-700 truncate">{domain.domain_name}</p>
        {domain.team_avg != null && (
          <p className="text-[10px] text-slate-400 mt-0.5">
            Team avg: {domain.team_avg.toFixed(0)}%
            {domain.delta_vs_team != null && (
              <span className={`ml-1 font-semibold ${domain.delta_vs_team >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                ({domain.delta_vs_team >= 0 ? "+" : ""}{domain.delta_vs_team.toFixed(0)}%)
              </span>
            )}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className={`text-sm font-bold tabular-nums ${isStrong ? "text-emerald-600" : isWeak ? "text-rose-600" : "text-slate-700"}`}>
          {domain.learner_score.toFixed(0)}%
        </span>
        {domain.pattern_type !== "none" && (
          <PatternBadge pattern={domain.pattern_type} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Review area card
// ---------------------------------------------------------------------------

function ReviewAreaCard({ area }: { area: AdvisorReviewArea }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50 overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-rose-100/50 transition-colors"
        aria-expanded={expanded}
      >
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-slate-800 truncate">{area.domain_name}</p>
          <p className="text-[10px] text-rose-600 font-medium mt-0.5">
            {area.learner_score.toFixed(0)}% — needs review
          </p>
        </div>
        <PatternBadge pattern={area.pattern_type} />
        {(area.note || area.resource_hint) && (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className={`h-3.5 w-3.5 text-slate-400 transition-transform shrink-0 ${expanded ? "rotate-180" : ""}`}
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        )}
      </button>
      {expanded && (area.note || area.resource_hint) && (
        <div className="border-t border-rose-200 px-4 py-3 bg-white space-y-2">
          {area.note && (
            <p className="text-xs text-slate-600 leading-relaxed">{area.note}</p>
          )}
          {area.resource_hint && (
            <p className="text-[11px] text-indigo-600 leading-relaxed">
              <span className="font-semibold text-slate-500">Resource: </span>
              {area.resource_hint}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Strong area card
// ---------------------------------------------------------------------------

function StrongAreaCard({ area }: { area: AdvisorStrongArea }) {
  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold text-slate-800 truncate flex-1">{area.domain_name}</p>
        <span className="text-sm font-bold text-emerald-600 shrink-0 tabular-nums">
          {area.learner_score.toFixed(0)}%
        </span>
      </div>
      {area.note && (
        <p className="text-[10px] text-emerald-700 mt-1 leading-relaxed">{area.note}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recommendation row
// ---------------------------------------------------------------------------

function RecommendationRow({ rec }: { rec: AdvisorRecommendation }) {
  return (
    <div className="flex gap-3 items-start py-2.5 border-b border-slate-100 last:border-0">
      <span className="shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-bold text-indigo-700 mt-0.5">
        {rec.order}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-slate-800">{rec.title}</p>
        {rec.detail && (
          <p className="text-[11px] text-slate-600 leading-relaxed mt-0.5">{rec.detail}</p>
        )}
        {rec.resource_hint && (
          <p className="text-[10px] text-indigo-500 mt-1 leading-relaxed">{rec.resource_hint}</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AdvisorView — main component
// ---------------------------------------------------------------------------

export default function AdvisorView({ advisorResult, onFinalize }: AdvisorViewProps) {
  if (!advisorResult) {
    return (
      <div className="flex flex-col items-center gap-4 py-16">
        <div className="relative h-10 w-10">
          <div className="absolute inset-0 rounded-full border-2 border-indigo-100" />
          <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-indigo-500" />
        </div>
        <p className="text-sm text-slate-500">Generating your advisor report…</p>
      </div>
    );
  }

  const passed = advisorResult.scenario === "passed";
  const { score_summary, performance_snapshot, team_benchmark, retry_comparison } = advisorResult;

  return (
    <div className="space-y-4 max-w-2xl mx-auto">

      {/* Score ring + header */}
      <div className="rounded-xl border border-slate-200 shadow-sm bg-white p-5">
        <div className="flex flex-col items-center mb-4">
          <div
            className={`flex h-24 w-24 items-center justify-center rounded-full border-4 mb-3
              ${passed ? "border-emerald-400" : "border-rose-400"}`}
          >
            <span className={`text-2xl font-bold ${passed ? "text-emerald-600" : "text-rose-600"}`}>
              {Math.round(score_summary.score)}%
            </span>
          </div>
          <h2 className="text-lg font-bold text-slate-900">
            {passed ? "Assessment Passed!" : "Max Attempts Reached"}
          </h2>
          <p className="text-sm text-slate-500 text-center mt-1">
            {advisorResult.cert_name || advisorResult.cert_id}
            {" · "}Attempt {score_summary.attempt}
          </p>
        </div>

        {/* Cert link (passed only) */}
        {passed && advisorResult.official_cert_url && (
          <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3 mb-3">
            <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1">
              Official certification
            </p>
            <a
              href={advisorResult.official_cert_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-emerald-700 underline hover:text-emerald-900"
            >
              {advisorResult.cert_name} — View on Microsoft Learn
            </a>
          </div>
        )}

        {/* Next cert suggestion */}
        {advisorResult.next_cert_suggestion && (
          <p className="text-xs text-slate-500">
            <span className="font-semibold text-slate-600">Suggested next: </span>
            {advisorResult.next_cert_suggestion}
          </p>
        )}
      </div>

      {/* Team percentile bar */}
      {team_benchmark.has_data && (
        <div className="rounded-xl border border-slate-200 shadow-sm bg-white p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Team benchmark
          </p>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs text-slate-600">0%</span>
            <div className="flex-1 h-3 rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-700"
                style={{ width: `${Math.min(team_benchmark.team_percentile, 100)}%` }}
              />
            </div>
            <span className="text-xs text-slate-600">100%</span>
          </div>
          <p className="text-xs text-slate-600 text-center">
            <span className="font-bold text-indigo-600">{team_benchmark.team_percentile}th percentile</span>
            {" · "}Team avg: {team_benchmark.team_avg_score.toFixed(1)}%
            {" · "}
            <span className={
              team_benchmark.comparison === "above"
                ? "text-emerald-600 font-semibold"
                : team_benchmark.comparison === "below"
                ? "text-rose-600 font-semibold"
                : "text-slate-500"
            }>
              {team_benchmark.comparison === "above"
                ? "Above team average"
                : team_benchmark.comparison === "below"
                ? "Below team average"
                : "In line with team"}
            </span>
            {team_benchmark.sample_size > 0 && (
              <span className="text-slate-400"> (n={team_benchmark.sample_size})</span>
            )}
          </p>
        </div>
      )}

      {/* Retry comparison (max_retries only) */}
      {retry_comparison && (
        <div className="rounded-xl border border-amber-200 shadow-sm bg-amber-50 p-5">
          <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-3">
            Attempt comparison
          </p>
          <div className="flex items-center justify-center gap-6 mb-3">
            <div className="text-center">
              <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-0.5">Attempt 1</p>
              <p className="text-xl font-bold text-slate-700">{retry_comparison.first_attempt_score.toFixed(0)}%</p>
            </div>
            <div className="text-center">
              <p className={`text-lg font-bold ${retry_comparison.delta >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                {retry_comparison.delta >= 0 ? "+" : ""}{retry_comparison.delta.toFixed(1)}%
              </p>
            </div>
            <div className="text-center">
              <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-0.5">Last attempt</p>
              <p className="text-xl font-bold text-slate-700">{retry_comparison.last_attempt_score.toFixed(0)}%</p>
            </div>
          </div>
          {retry_comparison.improved_domains.length > 0 && (
            <div className="mb-2">
              <p className="text-[10px] font-semibold text-emerald-700 mb-1">Improved</p>
              <div className="flex flex-wrap gap-1">
                {retry_comparison.improved_domains.map((d) => (
                  <span key={d} className="rounded-md bg-emerald-100 border border-emerald-200 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                    {d}
                  </span>
                ))}
              </div>
            </div>
          )}
          {retry_comparison.regressed_domains.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-rose-600 mb-1">Still needs work</p>
              <div className="flex flex-wrap gap-1">
                {retry_comparison.regressed_domains.map((d) => (
                  <span key={d} className="rounded-md bg-rose-100 border border-rose-200 px-2 py-0.5 text-[10px] font-medium text-rose-700">
                    {d}
                  </span>
                ))}
              </div>
            </div>
          )}
          {retry_comparison.summary && (
            <p className="text-xs text-slate-600 mt-2 leading-relaxed">{retry_comparison.summary}</p>
          )}
        </div>
      )}

      {/* Strong areas */}
      {advisorResult.strong_areas.length > 0 && (
        <div className="rounded-xl border border-slate-200 shadow-sm bg-white p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Strong areas
          </p>
          <div className="space-y-2">
            {advisorResult.strong_areas.map((area) => (
              <StrongAreaCard key={area.domain_name} area={area} />
            ))}
          </div>
        </div>
      )}

      {/* Areas to review */}
      {advisorResult.areas_to_review.length > 0 && (
        <div className="rounded-xl border border-slate-200 shadow-sm bg-white p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Areas to review
          </p>
          <div className="space-y-2">
            {advisorResult.areas_to_review.map((area) => (
              <ReviewAreaCard key={area.domain_name} area={area} />
            ))}
          </div>
        </div>
      )}

      {/* Domain analysis */}
      {advisorResult.domain_analysis.length > 0 && (
        <div className="rounded-xl border border-slate-200 shadow-sm bg-white p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Domain breakdown
          </p>
          <div>
            {advisorResult.domain_analysis.map((domain) => (
              <DomainRow key={domain.domain_name} domain={domain} />
            ))}
          </div>
        </div>
      )}

      {/* Performance snapshot */}
      <div className="rounded-xl border border-slate-200 shadow-sm bg-white p-5">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
          Performance snapshot
        </p>
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
            <p className="text-xs text-slate-500 mb-1">Conceptual</p>
            <p className="text-lg font-bold text-slate-700">{performance_snapshot.conceptual_correct_pct.toFixed(0)}%</p>
          </div>
          <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
            <p className="text-xs text-slate-500 mb-1">Application</p>
            <p className="text-lg font-bold text-slate-700">{performance_snapshot.application_correct_pct.toFixed(0)}%</p>
          </div>
          <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
            <p className="text-xs text-slate-500 mb-1">Scenarios</p>
            <p className={`text-lg font-bold ${performance_snapshot.has_scenario_gap ? "text-rose-600" : "text-slate-700"}`}>
              {performance_snapshot.scenario_correct_pct.toFixed(0)}%
            </p>
          </div>
        </div>
        {performance_snapshot.has_scenario_gap && (
          <p className="text-[11px] text-rose-600 mt-2 text-center font-medium">
            Scenario-based questions are a gap area — focus practice here.
          </p>
        )}
      </div>

      {/* Recommendations */}
      {advisorResult.recommendations.length > 0 && (
        <div className="rounded-xl border border-slate-200 shadow-sm bg-white p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Recommendations
          </p>
          <div>
            {advisorResult.recommendations
              .slice()
              .sort((a, b) => a.order - b.order)
              .map((rec) => (
                <RecommendationRow key={rec.order} rec={rec} />
              ))}
          </div>
        </div>
      )}

      {/* Closing note */}
      {advisorResult.closing_note && (
        <div className="rounded-xl border border-slate-200 shadow-sm bg-white px-5 py-4">
          <p className="text-sm text-slate-500 italic leading-relaxed">{advisorResult.closing_note}</p>
        </div>
      )}

      {/* Finalize track CTA */}
      <button
        type="button"
        onClick={onFinalize}
        className="w-full rounded-xl bg-indigo-600 px-4 py-3.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 flex items-center justify-center gap-2"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
          className="h-4 w-4"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Finalize track
      </button>
    </div>
  );
}
