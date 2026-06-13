"use client";

import { useState } from "react";
import type { QuestionResult } from "@/app/lib/assessment-types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AssessmentResultsProps {
  score: number;
  passed: boolean;
  weakAreas: string[];
  perQuestionResults: QuestionResult[];
  recommendedCertName?: string | null;
  recommendedCertId?: string | null;
  onRetry?: () => void;
}

// ---------------------------------------------------------------------------
// Per-question result row (collapsible)
// ---------------------------------------------------------------------------

interface QuestionResultRowProps {
  result: QuestionResult;
  index: number;
}

function QuestionResultRow({ result, index }: QuestionResultRowProps) {
  const [expanded, setExpanded] = useState(false);

  const isCorrect = result.partial_score >= 1.0;
  const isPartial = result.partial_score > 0 && result.partial_score < 1.0;

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-white hover:bg-slate-50 transition-colors text-left"
        aria-expanded={expanded}
      >
        {/* Indicator */}
        <span
          className={`shrink-0 h-5 w-5 rounded-full flex items-center justify-center text-xs font-bold
            ${isCorrect
              ? "bg-emerald-100 text-emerald-700"
              : isPartial
              ? "bg-amber-100 text-amber-700"
              : "bg-rose-100 text-rose-700"
            }`}
          aria-hidden="true"
        >
          {isCorrect ? "✓" : isPartial ? "~" : "✗"}
        </span>

        <span className="flex-1 text-xs font-medium text-slate-700">
          Q{index + 1}
        </span>

        {/* Partial score badge */}
        {isPartial && (
          <span className="text-xs text-amber-600 font-semibold">
            {Math.round(result.partial_score * 100)}% credit
          </span>
        )}

        {/* Chevron */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
          className={`h-3.5 w-3.5 text-slate-400 transition-transform ${expanded ? "rotate-180" : ""}`}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-slate-100 px-4 py-3 bg-slate-50 space-y-2">
          {/* Your answer */}
          <div>
            <p className="text-xs font-semibold text-slate-500 mb-0.5">Your answer</p>
            <p className="text-xs text-slate-800">
              {result.user_answers.length > 0 ? result.user_answers.join(", ") : "(none)"}
            </p>
          </div>
          {/* Correct answer */}
          <div>
            <p className="text-xs font-semibold text-slate-500 mb-0.5">Correct answer</p>
            <p className="text-xs text-emerald-700 font-medium">
              {result.correct_answers.join(", ")}
            </p>
          </div>
          {/* Explanation */}
          {result.explanation && (
            <div>
              <p className="text-xs font-semibold text-slate-500 mb-0.5">Explanation</p>
              <p className="text-xs text-slate-600 leading-relaxed">{result.explanation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AssessmentResults — main component
// ---------------------------------------------------------------------------

export default function AssessmentResults({
  score,
  passed,
  weakAreas,
  perQuestionResults,
  recommendedCertName,
  recommendedCertId,
  onRetry,
}: AssessmentResultsProps) {
  const certId = recommendedCertId ?? null;
  const certName = recommendedCertName ?? certId ?? null;
  const certUrl = certId
    ? `https://learn.microsoft.com/certifications/${certId.toLowerCase()}`
    : null;

  return (
    <div className="card animate-fade-in max-w-2xl mx-auto">
      {/* Score ring */}
      <div className="flex flex-col items-center mb-6">
        <div
          className={`flex h-24 w-24 items-center justify-center rounded-full border-4 mb-3
            ${passed ? "border-emerald-400" : "border-rose-400"}`}
        >
          <span
            className={`text-2xl font-bold ${passed ? "text-emerald-600" : "text-rose-600"}`}
          >
            {Math.round(score)}%
          </span>
        </div>

        <h2 className="text-lg font-bold text-slate-900">
          {passed ? "Assessment Passed!" : "Assessment Not Passed"}
        </h2>
        <p className="text-sm text-slate-500 text-center mt-1">
          {passed
            ? "You demonstrated sufficient knowledge for this certification path."
            : "You need 70% or higher to pass. Let's strengthen the weak areas."}
        </p>
      </div>

      {/* Cert info (pass only) */}
      {passed && certName && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 mb-5">
          <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1">
            Recommended certification
          </p>
          <p className="text-sm font-bold text-emerald-900 mb-2">{certName}</p>
          {certUrl && (
            <a
              href={certUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-emerald-700 underline hover:text-emerald-900"
            >
              View on Microsoft Learn
            </a>
          )}
        </div>
      )}

      {/* Weak areas */}
      {weakAreas.length > 0 && (
        <div className="mb-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            {passed ? "Areas to reinforce" : "Weak areas — study these before retrying"}
          </p>
          <div className="flex flex-wrap gap-2">
            {weakAreas.map((area) => (
              <span
                key={area}
                className="rounded-md bg-rose-50 border border-rose-200 px-2.5 py-1 text-xs font-medium text-rose-700"
              >
                {area}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Fail message */}
      {!passed && weakAreas.length > 0 && (
        <p className="text-xs text-slate-500 italic mb-5">
          Let&apos;s strengthen{" "}
          <span className="font-medium text-slate-700">{weakAreas.join(", ")}</span>.{" "}
          Rebuilding your learning path…
        </p>
      )}

      {/* Retry button (fail only, when retry is available) */}
      {!passed && onRetry && (
        <div className="mb-5">
          <button
            type="button"
            onClick={onRetry}
            className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Retry Assessment
          </button>
        </div>
      )}

      {/* Per-question breakdown */}
      {perQuestionResults.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Per-question breakdown
          </p>
          <div className="space-y-2">
            {perQuestionResults.map((result, idx) => (
              <QuestionResultRow key={result.question_id} result={result} index={idx} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
