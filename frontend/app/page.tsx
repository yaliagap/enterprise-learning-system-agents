"use client";

import { useEffect, useRef, useState } from "react";
import { useAgentChat, type AgentName, type KBActivity, type CertOption } from "@/app/hooks/useAgentChat";
import { AZURE_TOPICS, getTopicsByFamily } from "@/app/lib/topics";
import { getLearnerProfile, type LearnerProfile, type CertificationCatalogItem } from "@/app/lib/learner-fixtures";

import CourseSection from "@/components/CourseSection";
import { KBActivityCard } from "@/components/KBActivityCard";
import { CuratorOutputCard } from "@/components/CuratorOutputCard";
import { CertSelectionCard } from "@/components/CertSelectionCard";
import StudyPlanTimeline from "@/components/StudyPlanTimeline";
import HITLConfirmation from "@/components/HITLConfirmation";
import EngagementProposalView, {
  type EngagementProposal,
  type StudySessionRef,
  type StudyMilestoneRef,
} from "@/components/EngagementProposalView";
import AssessmentPanel from "@/components/AssessmentPanel";
import ExamInterface from "@/components/ExamInterface";
import AssessmentResults from "@/components/AssessmentResults";
import type { AssessmentAnswers, AssessmentQuestion, QuestionResult } from "@/app/lib/assessment-types";

// ---------------------------------------------------------------------------
// Types — mirror backend WorkflowState / nested Pydantic schemas exactly
// ---------------------------------------------------------------------------

type WorkflowStatus =
  | "planning"
  | "studying"
  | "awaiting_assessment"
  | "assessing"
  | "exam_in_progress"
  | "exam_failed"
  | "passed"
  | "failed"
  | "max_retries_reached"
  | "awaiting_cert_selection"
  | "awaiting_path_confirmation";

interface LearnerContext {
  learner_id: string;
  employee_id: string;
  topics: string[];
  role: string;
  roles?: string[];
  seniority?: string;
  experience_level?: string;
}

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

interface StudyPlanSession {
  session_id?: string;
  date: string;
  hours: number;
  topics: string[];
  resource_ids?: string[];
  topic_hours?: number[];
}

interface StudyMilestone {
  milestone_id: string;
  domain_name: string;
  target_week: number;
  target_date: string;
  session_ids: string[];
}

interface EngagementStatus {
  reminders_sent: number;
  last_contact: string | null;
  preferred_slot: string;
  next_reminder: string | null;
}

interface AssessmentResult {
  attempt: number;
  score: number;
  passed: boolean;
  passing_score: number;
  weak_areas: string[];
  completed_at: string;
  per_question_results: QuestionResult[];
}

interface WorkflowState extends Record<string, unknown> {
  learner: LearnerContext;
  learning_path: LearningPathItem[];
  study_plan: StudyPlanSession[];
  engagement: EngagementStatus | null;
  engagement_proposal: EngagementProposal | null;
  assessment_results: AssessmentResult[];
  retry_count: number;
  max_retries: number;
  hitl_confirmed: boolean;
  workflow_status: WorkflowStatus;
  recommended_cert_id: string | null;
  recommended_cert_name: string | null;
  // Assessment exam fields (populated during exam_in_progress)
  assessment_questions: AssessmentQuestion[];
  assessment_answers: AssessmentAnswers | null;
  // Attribution fields (set by executors before each text message)
  current_agent?: string;
  kb_activity?: KBActivity | null;
  // Cert selection fields — populated by Curator Run 1
  cert_options?: CertOption[];
  selected_cert_id?: string | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PHASE_LABELS: Record<WorkflowStatus, string> = {
  planning: "Planning",
  studying: "Studying",
  awaiting_assessment: "Awaiting Assessment",
  assessing: "Assessing",
  exam_in_progress: "Assessment",
  passed: "Passed",
  failed: "Failed",
  exam_failed: "Review Results",
  max_retries_reached: "Max Retries",
  awaiting_cert_selection: "Choose Certification",
  awaiting_path_confirmation: "Confirm Path",
};

const PHASE_COLORS: Record<WorkflowStatus, string> = {
  planning:                  "bg-amber-50 text-amber-700 border border-amber-200",
  studying:                  "bg-blue-50 text-blue-700 border border-blue-200",
  awaiting_assessment:       "bg-violet-50 text-violet-700 border border-violet-200",
  assessing:                 "bg-pink-50 text-pink-700 border border-pink-200",
  exam_in_progress:          "bg-violet-50 text-violet-700 border border-violet-200",
  passed:                    "bg-emerald-50 text-emerald-700 border border-emerald-200",
  failed:                    "bg-rose-50 text-rose-700 border border-rose-200",
  exam_failed:               "bg-rose-50 text-rose-700 border border-rose-200",
  max_retries_reached:       "bg-rose-50 text-rose-700 border border-rose-200",
  awaiting_cert_selection:   "bg-amber-50 text-amber-700 border border-amber-200",
  awaiting_path_confirmation:"bg-blue-50 text-blue-700 border border-blue-200",
};

const AGENT_LABELS: Record<AgentName, string> = {
  curator: "Learning Path Curator Agent",
  study_plan: "Study Plan Agent",
  engagement: "Engagement Agent",
  assessment: "Assessment Agent",
  certification_advisor: "Assessment Agent",
};

const AGENT_COLORS: Record<AgentName, string> = {
  curator:               "bg-amber-50 text-amber-700 border border-amber-200",
  study_plan:            "bg-blue-50 text-blue-700 border border-blue-200",
  engagement:            "bg-violet-50 text-violet-700 border border-violet-200",
  assessment:            "bg-pink-50 text-pink-700 border border-pink-200",
  certification_advisor: "bg-pink-50 text-pink-700 border border-pink-200",
};

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// App screen type
// ---------------------------------------------------------------------------

type AppScreen = "login" | "dashboard" | "cert-detail" | "topic-selection" | "active-session";

// ---------------------------------------------------------------------------
// Topic picker
// ---------------------------------------------------------------------------

interface TopicPickerProps {
  selectedTopics: string[];
  onChange: (topics: string[]) => void;
}

function TopicPicker({ selectedTopics, onChange }: TopicPickerProps) {
  const grouped = getTopicsByFamily();

  function toggle(id: string) {
    if (selectedTopics.includes(id)) {
      onChange(selectedTopics.filter((t) => t !== id));
    } else if (selectedTopics.length < 10) {
      onChange([...selectedTopics, id]);
    }
  }

  const FAMILY_META: Record<string, { border: string; headerBg: string; text: string; dot: string; span?: string }> = {
    Fundamentals: { border: "border-emerald-200", headerBg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", span: "col-span-2" },
    Associate:    { border: "border-blue-200",    headerBg: "bg-blue-50",    text: "text-blue-700",    dot: "bg-blue-500" },
    Expert:       { border: "border-violet-200",  headerBg: "bg-violet-50",  text: "text-violet-700",  dot: "bg-violet-500" },
  };

  const entries = Array.from(grouped.entries());

  return (
    <div className="grid grid-cols-2 gap-3">
      {entries.map(([family, topics]) => {
        const meta = FAMILY_META[family] ?? { border: "border-slate-200", headerBg: "bg-slate-50", text: "text-slate-600", dot: "bg-slate-400" };
        const selectedInFamily = topics.filter(t => selectedTopics.includes(t.id)).length;
        return (
          <div key={family} className={`rounded-xl border ${meta.border} overflow-hidden ${meta.span ?? ""}`}>
            <div className={`flex items-center justify-between px-3 py-2 ${meta.headerBg} border-b ${meta.border}`}>
              <div className="flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
                <span className={`text-[11px] font-semibold uppercase tracking-wider ${meta.text}`}>{family}</span>
              </div>
              {selectedInFamily > 0 && (
                <span className={`text-[11px] font-bold ${meta.text}`}>{selectedInFamily} ✓</span>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5 p-2.5 bg-white">
              {topics.map((topic) => {
                const selected = selectedTopics.includes(topic.id);
                const atMax = !selected && selectedTopics.length >= 10;
                return (
                  <button
                    key={topic.id}
                    type="button"
                    disabled={atMax}
                    onClick={() => toggle(topic.id)}
                    aria-pressed={selected}
                    className={`topic-pill text-[11px] px-2.5 py-1 ${selected ? "topic-pill-active" : atMax ? "topic-pill-disabled" : "topic-pill-inactive"}`}
                  >
                    {selected && <span className="mr-0.5">✓</span>}
                    {topic.label}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chat sidebar
// ---------------------------------------------------------------------------

interface ChatSidebarProps {
  messages: Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    isStreaming: boolean;
    agentName?: AgentName;
    kbActivity?: KBActivity;
    curatorOutput?: import("@/app/hooks/useAgentChat").CuratorOutput;
    certOptions?: CertOption[];
    workflowStatus?: string;
  }>;
  isRunning: boolean;
  activeToolCalls: Array<{ toolCallId: string; name: string }>;
  error: string | null;
  onSend: (text: string) => void;
  onHITLConfirm?: () => void;
  onHITLDecline?: () => void;
  showHITL?: boolean;
  hitlHours?: number;
  engagementConfirmed?: boolean;
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Inline markdown renderer — handles **bold** and newlines in chat bubbles
// ---------------------------------------------------------------------------

function renderMarkdown(text: string): React.ReactNode {
  const lines = text.split("\n");
  return lines.map((line, li) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return (
      <span key={li}>
        {li > 0 && <br />}
        {parts.map((part, pi) =>
          part.startsWith("**") && part.endsWith("**")
            ? <strong key={pi} className="font-semibold">{part.slice(2, -2)}</strong>
            : part
        )}
      </span>
    );
  });
}

// ---------------------------------------------------------------------------
// Curator Reasoning Panel — shown below cert cards when awaiting_cert_selection
// ---------------------------------------------------------------------------

function CuratorReasoningPanel({
  reasoning,
  kbActivity,
}: {
  reasoning: string;
  kbActivity?: {
    query?: string;
    response_text?: string;
    references?: Array<{ title: string; url: string; type: string; score?: number | null }>;
  } | null;
}) {
  const [kbExpanded, setKbExpanded] = useState(false);

  if (!reasoning && !kbActivity?.query) return null;

  const refs = kbActivity?.references ?? [];

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-slate-100 bg-slate-50">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-amber-100">
          <svg className="h-3.5 w-3.5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        </div>
        <div>
          <p className="text-xs font-bold text-slate-700 leading-none">Learning Path Curator · Reasoning</p>
          <p className="text-[10px] text-slate-400 mt-0.5">Why these certifications were recommended</p>
        </div>
      </div>

      <div className="px-5 py-4 space-y-5">
        {/* Reasoning */}
        {reasoning && (
          <div>
            <p className="section-label mb-2">Agent Reasoning</p>
            <p className="text-sm text-slate-700 leading-relaxed">{reasoning}</p>
          </div>
        )}

        {/* KB References — collapsible */}
        {kbActivity?.query && (
          <div>
            <button
              onClick={() => setKbExpanded((v) => !v)}
              className="flex w-full items-center justify-between mb-2 group"
            >
              <p className="section-label">
                Knowledge Base References
                {refs.length > 0 && <span className="ml-1.5 font-normal normal-case text-slate-400">({refs.length} source{refs.length !== 1 ? "s" : ""})</span>}
              </p>
              <svg className={`h-3.5 w-3.5 text-slate-400 transition-transform ${kbExpanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {kbExpanded && (
              refs.length > 0 ? (
                <div className="space-y-2">
                  {refs.map((ref, i) => (
                    <div key={i} className="flex items-start gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                      <span className={`shrink-0 mt-px rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                        ref.type === "document" ? "bg-blue-100 text-blue-700"
                        : ref.type === "web" ? "bg-emerald-100 text-emerald-700"
                        : "bg-slate-100 text-slate-600"
                      }`}>
                        {ref.type}
                      </span>
                      <div className="min-w-0 flex-1">
                        {ref.url?.startsWith("https://") ? (
                          <a href={ref.url} target="_blank" rel="noopener noreferrer"
                            className="text-xs font-semibold text-blue-600 hover:underline leading-snug">
                            {ref.title}
                          </a>
                        ) : (
                          <p className="text-xs font-semibold text-slate-700 leading-snug">{ref.title}</p>
                        )}
                        {ref.url && !ref.url.startsWith("https://") && (
                          <p className="text-[10px] text-slate-400 mt-0.5 truncate">{ref.url}</p>
                        )}
                      </div>
                      {ref.score != null && (
                        <span className="shrink-0 text-[10px] font-medium text-slate-400 tabular-nums">
                          {Math.round(ref.score * 100)}%
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                /* Fallback: KB query + full response */
                <div className="rounded-lg border border-slate-200 overflow-hidden">
                  <div className="flex items-start gap-2.5 px-4 py-3 bg-slate-50 border-b border-slate-100">
                    <span className="inline-flex items-center rounded-md bg-blue-100 text-blue-700 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide shrink-0 mt-px">
                      document
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-slate-700 leading-snug">Enterprise Learning Knowledge Base</p>
                      <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{kbActivity.query}</p>
                    </div>
                  </div>
                  {kbActivity.response_text && (
                    <div className="px-4 py-3">
                      <p className="text-xs font-medium text-slate-500 mb-1.5">KB Response</p>
                      <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">
                        {kbActivity.response_text}
                      </p>
                    </div>
                  )}
                </div>
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cert Options Panel — shown in main area when awaiting_cert_selection
// ---------------------------------------------------------------------------

const AGENT_WORKFLOW_STEPS = [
  { key: "curator",    label: "Learning Path Curator", step: 1 },
  { key: "study_plan", label: "Study Plan Agent",      step: 2 },
  { key: "engagement", label: "Engagement Agent",      step: 3 },
  { key: "assessment", label: "Assessment Agent",      step: 4 },
];

const CERT_LEVEL_STYLES: Record<string, string> = {
  fundamentals: "bg-emerald-100 text-emerald-700",
  associate:    "bg-blue-100 text-blue-700",
  expert:       "bg-purple-100 text-purple-700",
};

function CertOptionsPanel({ options, onSelect }: { options: CertOption[]; onSelect: (id: string) => void }) {
  const topId = [...options]
    .filter((o) => !o.already_obtained)
    .sort((a, b) => b.recommendation_pct - a.recommendation_pct)[0]?.cert_id;

  return (
    <section>
      {/* Agent workflow tabs */}
      <div className="flex gap-0 border-b border-slate-200 mb-5 overflow-x-auto">
        {AGENT_WORKFLOW_STEPS.map((step, idx) => (
          <div
            key={step.key}
            className={`flex shrink-0 items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors select-none ${
              idx === 0
                ? "border-amber-500 text-amber-700"
                : "border-transparent text-slate-400 cursor-not-allowed"
            }`}
          >
            <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
              idx === 0 ? "bg-amber-500 text-white" : "bg-slate-200 text-slate-500"
            }`}>
              {step.step}
            </span>
            {step.label}
            {idx !== 0 && (
              <svg className="h-3 w-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
              </svg>
            )}
          </div>
        ))}
      </div>

      {/* Cert cards grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {options.map((cert) => {
          const isTop = cert.cert_id === topId;
          const levelStyle = CERT_LEVEL_STYLES[cert.level?.toLowerCase() ?? ""] ?? "bg-slate-100 text-slate-600";

          return (
            <div
              key={cert.cert_id}
              className={`relative rounded-xl border overflow-hidden flex flex-col transition-all ${
                cert.already_obtained
                  ? "border-slate-200 bg-slate-50"
                  : isTop
                    ? "border-amber-300 bg-white ring-2 ring-amber-300 shadow-md"
                    : "border-slate-200 bg-white hover:border-blue-200 hover:shadow-sm"
              }`}
            >
              {/* TOP MATCH badge */}
              {isTop && (
                <div className="absolute top-0 right-0 flex items-center gap-1 rounded-bl-xl bg-amber-400 px-2.5 py-1">
                  <svg className="h-3 w-3 text-amber-900" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  <span className="text-[10px] font-bold text-amber-900 uppercase tracking-wide">Top Match</span>
                </div>
              )}

              {/* Already earned banner */}
              {cert.already_obtained && (
                <div className="flex items-center gap-1.5 bg-emerald-600 px-3 py-1.5">
                  <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-[10px] font-bold text-white uppercase tracking-wider">Already Earned</span>
                </div>
              )}

              <div className={`flex flex-col flex-1 px-4 pb-4 ${isTop && !cert.already_obtained ? "pt-8" : "pt-4"}`}>
                {/* Cert ID + level */}
                <div className="flex items-center gap-2 mb-2">
                  <span className={`rounded-md px-2 py-0.5 text-xs font-bold tracking-wide ${
                    isTop ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"
                  }`}>
                    {cert.cert_id}
                  </span>
                  {cert.level && (
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${levelStyle}`}>
                      {cert.level}
                    </span>
                  )}
                </div>

                <p className={`text-sm font-semibold leading-tight mb-2 ${cert.already_obtained ? "text-slate-500" : "text-slate-800"}`}>
                  {cert.name}
                </p>

                {cert.description && (
                  <p className="text-xs text-slate-500 leading-relaxed line-clamp-2 mb-3 flex-1">
                    {cert.description}
                  </p>
                )}

                {/* Match bar */}
                <div className="flex items-center gap-2 text-xs mb-4">
                  <span className="text-slate-400 shrink-0">Match</span>
                  <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full transition-all ${
                        cert.already_obtained ? "bg-slate-300" : isTop ? "bg-amber-400" : "bg-blue-400"
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, Math.round(cert.recommendation_pct)))}%` }}
                    />
                  </div>
                  <span className={`font-semibold w-8 text-right shrink-0 tabular-nums ${
                    cert.already_obtained ? "text-slate-400" : isTop ? "text-amber-600" : "text-slate-600"
                  }`}>
                    {Math.round(cert.recommendation_pct)}%
                  </span>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between gap-2">
                  {cert.ms_learn_url.startsWith("https://") ? (
                    <a
                      href={cert.ms_learn_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-500 hover:underline"
                    >
                      MS Learn ↗
                    </a>
                  ) : <span />}
                  <button
                    type="button"
                    disabled={cert.already_obtained}
                    onClick={() => onSelect(cert.cert_id)}
                    className={`shrink-0 rounded-lg px-4 py-1.5 text-xs font-semibold transition-colors ${
                      cert.already_obtained
                        ? "bg-slate-200 text-slate-400 cursor-not-allowed"
                        : isTop
                          ? "bg-amber-500 text-white hover:bg-amber-600"
                          : "bg-blue-600 text-white hover:bg-blue-700"
                    }`}
                  >
                    {cert.already_obtained ? "Earned ✓" : "Select"}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ChatSidebar({
  messages,
  isRunning,
  activeToolCalls,
  error,
  onSend,
  onHITLConfirm,
  onHITLDecline,
  showHITL,
  hitlHours = 0,
  engagementConfirmed = false,
  disabled = false,
}: ChatSidebarProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeToolCalls]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput("");
  }

  return (
    <aside className="flex w-[420px] shrink-0 flex-col border-l border-slate-200 bg-white">
      {/* Header */}
      <div className="px-5 py-4 bg-slate-800">
        <p className="font-heading text-sm font-semibold text-white">Learning Assistant</p>
        <p className="mt-0.5 flex items-center gap-1" style={{ fontSize: "11px" }}>
          <span className="text-slate-400">Powered by</span>
          <span className="font-semibold text-blue-400">AG-UI</span>
          <span className="text-slate-500">·</span>
          <span className="text-slate-300">Azure AI Foundry</span>
        </p>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && !disabled && (
          <div className="flex flex-col items-center gap-3 pt-10 text-center px-4">
            <div className="h-11 w-11 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center">
              <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-700">AI Learning Assistant</p>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                Start your session to begin your personalized learning journey.
              </p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            {msg.role === "assistant" && (
              <span className={`agent-badge mb-1.5 ${
                msg.agentName && AGENT_COLORS[msg.agentName]
                  ? AGENT_COLORS[msg.agentName]
                  : "bg-slate-100 text-slate-600 border border-slate-200"
              }`}>
                {msg.agentName && AGENT_LABELS[msg.agentName]
                  ? AGENT_LABELS[msg.agentName]
                  : "Learning Assistant"}
              </span>
            )}
            {msg.role === "assistant" && msg.kbActivity && (
              <KBActivityCard activity={msg.kbActivity} />
            )}
            {msg.role === "assistant" && msg.curatorOutput && (
              <CuratorOutputCard output={msg.curatorOutput} />
            )}
            {msg.role === "assistant" && msg.workflowStatus === "awaiting_path_confirmation" && (
              <div className="mb-2 w-full max-w-[85%] rounded-xl px-3 py-2.5 text-xs font-medium bg-blue-50 border border-blue-200 text-blue-700">
                Your learning path is ready. Type any message to confirm and generate your study plan.
              </div>
            )}
            <div className={msg.role === "user" ? "bubble-user" : "bubble-assistant"}>
              {msg.content
                ? (msg.role === "assistant" ? renderMarkdown(msg.content) : msg.content)
                : (msg.isStreaming ? (
                <span className="inline-flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "300ms" }} />
                </span>
              ) : "")}
              {msg.isStreaming && msg.content && (
                <span className="ml-0.5 inline-block h-3 w-0.5 bg-blue-500 animate-pulse" />
              )}
            </div>
          </div>
        ))}

        {/* Active tool call indicators */}
        {activeToolCalls.map((tc) => (
          <div key={tc.toolCallId} className="flex justify-start">
            <div className="rounded-2xl rounded-tl-sm px-3.5 py-2 text-xs flex items-center gap-2 font-medium bg-blue-50 border border-blue-100 text-blue-600">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
              {tc.name.replace(/_/g, " ")}…
            </div>
          </div>
        ))}

        {/* HITL confirmation */}
        {showHITL && (
          <HITLConfirmation
            indicators={{ hoursStudied: hitlHours, resourcesCompleted: 0, totalResources: 0 }}
            onConfirm={onHITLConfirm ?? (() => {})}
            onDecline={onHITLDecline ?? (() => {})}
          />
        )}

        {/* Error */}
        {error && (
          <div className="rounded-xl px-4 py-3 text-xs font-medium bg-rose-50 border border-rose-200 text-rose-700">
            {error}
          </div>
        )}

        {engagementConfirmed && (
          <div className="rounded-xl px-4 py-3 space-y-1 bg-emerald-50 border border-emerald-200">
            <p className="text-xs font-semibold text-emerald-700">Plan & reminders confirmed</p>
            <p className="text-xs leading-relaxed text-emerald-600">
              Your study plan and engagement reminders are all set. Come back whenever you feel ready to take your assessment.
            </p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 flex gap-2 border-t border-slate-100">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={disabled ? "Start a session to chat" : "Ask anything…"}
          disabled={isRunning || disabled}
          className="input flex-1"
        />
        <button
          type="submit"
          disabled={!input.trim() || isRunning || disabled}
          className="shrink-0 min-w-[44px] min-h-[44px] rounded-xl px-4 py-2.5 bg-blue-600 text-white hover:bg-blue-700 transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          aria-label="Send message"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
        </button>
      </form>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Shared header component
// ---------------------------------------------------------------------------

interface AppHeaderProps {
  showPhase?: boolean;
  phase?: WorkflowStatus;
  backLabel?: string;
  onBack?: () => void;
  onLogout?: () => void;
  learnerId?: string;
  learnerRoles?: string[];
}

function AppHeader({ showPhase, phase, backLabel, onBack, onLogout, learnerId, learnerRoles }: AppHeaderProps) {
  return (
    <header className="shrink-0 z-20 border-b border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between px-6 py-3">
        {/* Left: always show brand + optional back breadcrumb */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-600">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="white" className="h-5 w-5" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-heading text-sm font-bold leading-none text-slate-900 tracking-tight">
                Enterprise Learning System
              </h1>
              {onBack && (
                <>
                  <span className="text-slate-300 text-sm">/</span>
                  <button
                    onClick={onBack}
                    className="text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline transition-colors"
                  >
                    ← {backLabel ?? "Back"}
                  </button>
                </>
              )}
            </div>
            <p className="text-blue-600 font-medium mt-0.5" style={{ fontSize: "10px", letterSpacing: "0.04em" }}>
              AZURE AI FOUNDRY
            </p>
          </div>
        </div>

        {/* Center: phase badge */}
        {showPhase && phase && PHASE_LABELS[phase] && (
          <span className={`phase-badge ${PHASE_COLORS[phase]}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" aria-hidden="true" />
            {PHASE_LABELS[phase]}
          </span>
        )}

        {/* Right: learner identity + action */}
        <div className="flex items-center gap-3">
          {learnerId && (
            <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100">
                <svg className="h-3.5 w-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
              </div>
              <div className="leading-none">
                <p className="font-heading text-xs font-bold text-slate-800">{learnerId}</p>
                {learnerRoles && learnerRoles.length > 0 && (
                  <p className="text-[10px] text-slate-500 mt-0.5">{learnerRoles[0]}</p>
                )}
              </div>
            </div>
          )}
          {onLogout ? (
            <button
              onClick={onLogout}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-rose-50 hover:border-rose-200 hover:text-rose-600 transition-all duration-150"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
              </svg>
              Sign out
            </button>
          ) : (
            <a href="/manager" className="btn-ghost text-xs font-medium tracking-wide">
              Manager View
            </a>
          )}
        </div>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Main learner dashboard
// ---------------------------------------------------------------------------

export default function LearnerPage() {
  // --- Screen state ---
  const [screen, setScreen] = useState<AppScreen>("login");
  const [learnerProfile, setLearnerProfile] = useState<LearnerProfile | null>(null);
  const [selectedCert, setSelectedCert] = useState<CertificationCatalogItem | null>(null);
  const [loginError, setLoginError] = useState<string>("");

  // --- Session state ---
  const [learnerId, setLearnerId] = useState("");
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [showHITL, setShowHITL] = useState(false);

  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const frozenExamQuestionsRef = useRef<AssessmentQuestion[]>([]);
  const [engagementConfirmed, setEngagementConfirmed] = useState(false);
  const [showConfirmToast, setShowConfirmToast] = useState(false);
  const [showAdjustMessage, setShowAdjustMessage] = useState(false);

  // useAgentChat MUST stay at top level — never inside conditionals
  const { messages, agentState: workflowState, isRunning, activeToolCalls, error, resetSession, sendMessage } =
    useAgentChat<WorkflowState>(process.env.NEXT_PUBLIC_AGENT_URL || `${BACKEND_URL}/api/learn`);

  // Derived: session is active when on active-session screen
  const sessionStarted = screen === "active-session";

  // Detect HITL tool call
  const hitlToolCall = activeToolCalls.find((tc) => tc.name === "confirm_assessment_readiness");
  useEffect(() => {
    if (hitlToolCall) setShowHITL(true);
  }, [hitlToolCall]);

  const effectiveLearnerId = learnerProfile?.learner_id ?? learnerId.trim();
  const canStart = effectiveLearnerId.length > 0 && selectedTopics.length > 0;

  // --- Login ---
  function handleLogin() {
    const profile = getLearnerProfile(learnerId.trim().toUpperCase());
    if (!profile) {
      setLoginError("Learner code not found. Try EMP-001 through EMP-005.");
      return;
    }
    setLoginError("");
    setLearnerProfile(profile);
    setScreen("dashboard");
  }

  function handleLogout() {
    setScreen("login");
    setLearnerProfile(null);
    setSelectedCert(null);
    setLearnerId("");
    setLoginError("");
    setSelectedTopics([]);
  }

  // --- Session ---
  function handleStartSession() {
    if (!canStart) return;
    const topicLabels = selectedTopics
      .map((id) => AZURE_TOPICS.find((t) => t.id === id)?.label ?? id)
      .join(", ");

    const initialState: WorkflowState = {
      learner: {
        learner_id: effectiveLearnerId,
        employee_id: effectiveLearnerId,
        topics: selectedTopics,
        role: learnerProfile?.roles?.[0] ?? learnerProfile?.roles?.[0] ?? "developer",
        roles: learnerProfile?.roles ?? [],
        seniority: learnerProfile?.seniority ?? "",
        experience_level: learnerProfile?.seniority ?? undefined,
      },
      learning_path: [],
      study_plan: [],
      engagement: null,
      engagement_proposal: null,
      assessment_results: [],
      retry_count: 0,
      max_retries: 3,
      hitl_confirmed: false,
      workflow_status: "planning",
      recommended_cert_id: null,
      recommended_cert_name: null,
      assessment_questions: [],
      assessment_answers: null,
      cert_options: [],
      selected_cert_id: null,
    };
    resetSession(initialState);
    setScreen("active-session");
    setShowHITL(false);
    // Auto-kick the workflow with selected topic labels
    setTimeout(() => sendMessage(`Start my learning path for the selected topics: ${topicLabels}`), 50);
  }

  function handleHITLConfirm() {
    setShowHITL(false);
    sendMessage("confirmed");
  }

  function handleHITLDecline() {
    setShowHITL(false);
    sendMessage("declined");
  }

  function handleEngagementConfirm() {
    setEngagementConfirmed(true);
    setShowConfirmToast(true);
    setTimeout(() => setShowConfirmToast(false), 3000);
  }

  function handleEngagementAdjust() {
    setShowAdjustMessage(true);
  }

  function handleRetryAssessment() {
    sendMessage("retry");
  }

  function handleSubmitAssessment(answers: AssessmentAnswers) {
    frozenExamQuestionsRef.current = examQuestions;
    const updatedState: WorkflowState = {
      ...(workflowState as WorkflowState),
      assessment_answers: answers,
      workflow_status: "exam_in_progress",
    };
    resetSession(updatedState);
    setTimeout(() => sendMessage("Assessment submitted"), 50);
  }

  // --- Derived workflow values (used in active-session) ---
  const phase = (workflowState.workflow_status as WorkflowStatus | undefined) ?? "planning";
  const learningPath = (workflowState.learning_path as LearningPathItem[] | undefined) ?? [];
  const timelineSessions = ((workflowState.study_plan as StudyPlanSession[] | undefined) ?? []).map((s) => ({
    session_id: s.session_id,
    date: s.date,
    hours: s.hours,
    topics: s.topics,
    resource_ids: s.resource_ids,
    topic_hours: s.topic_hours,
  }));
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const studyMilestones = ((workflowState as any).study_milestones as StudyMilestone[] | undefined) ?? [];
  const engagementProposal = (workflowState.engagement_proposal as EngagementProposal | null | undefined) ?? null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const scheduleContext = (workflowState as any).schedule_context as {
    preferred_study_days: string[];
    session_duration_hours: number;
    preferred_slot: string;
    capacity_hours_per_week: number;
    is_fallback?: boolean;
  } | null | undefined;
  const latestAssessment = ((workflowState.assessment_results as AssessmentResult[] | undefined) ?? []).slice(-1)[0] ?? null;
  const assessmentResult = latestAssessment
    ? {
        score: latestAssessment.score,
        passed: latestAssessment.passed,
        weakAreas: latestAssessment.weak_areas,
        nextCertRecommendation: undefined,
      }
    : null;

  const examQuestions = (workflowState.assessment_questions as AssessmentQuestion[] | undefined) ?? [];
  const latestAssessmentFull = latestAssessment ?? null;

  const recommendedCertId = workflowState.recommended_cert_id as string | null | undefined;
  const recommendedCertName = workflowState.recommended_cert_name as string | null | undefined;
  const certDisplay = recommendedCertName ?? recommendedCertId ?? null;
  const priorityDomains = (workflowState.priority_domains as Array<{
    domain_name: string;
    exam_weight: number;
    level?: string;
    products?: string[];
    icon_url?: string;
  }> | undefined) ?? [];

  const activeLearnerTopics = (workflowState.learner as LearnerContext | undefined)?.topics ?? [];
  const activeTopicLabels = activeLearnerTopics
    .map((id) => AZURE_TOPICS.find((t) => t.id === id)?.label ?? id);

  const certOptions = (workflowState.cert_options as CertOption[] | undefined) ?? [];
  const curatorReasoning = (workflowState.curator_response as { reasoning?: string } | null)?.reasoning ?? "";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const curatorKbActivity = (workflowState as any).kb_activity as {
    query?: string;
    response_text?: string;
    references?: Array<{ title: string; url: string; type: string; score?: number | null }>;
  } | null | undefined;

  // --- Dashboard derived values ---
  const completedCerts = learnerProfile?.certifications.filter((c) => c.status === "completed") ?? [];
  const inProgressCerts = learnerProfile?.certifications.filter((c) => c.status === "in_progress") ?? [];
  const readiness = learnerProfile?.readiness_score ?? 0;

  // ---------------------------------------------------------------------------
  // Screen 1: LOGIN
  // ---------------------------------------------------------------------------

  if (screen === "login") {
    return (
      <div className="flex h-screen">
        {/* Left panel */}
        <div className="hidden md:flex md:w-[45%] flex-col justify-between bg-gradient-to-br from-blue-700 to-blue-900 p-10 text-white">
          <div>
            <div className="flex items-center gap-3 mb-8">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="white" className="h-5 w-5" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
                </svg>
              </div>
              <span className="font-heading text-lg font-bold">Enterprise Learning System</span>
            </div>
            <h2 className="font-heading text-3xl font-bold mb-3 leading-tight">
              AI-powered certification training on Azure AI Foundry
            </h2>
            <p className="text-blue-200 text-sm leading-relaxed mb-8">
              Personalized learning paths built by intelligent agents for Microsoft certification success.
            </p>
            <ul className="space-y-4">
              <li className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15">
                  <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <span className="text-sm font-medium">Personalized learning paths</span>
              </li>
              <li className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15">
                  <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                  </svg>
                </div>
                <span className="text-sm font-medium">AI-guided study plans</span>
              </li>
              <li className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15">
                  <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                  </svg>
                </div>
                <span className="text-sm font-medium">Real-time progress tracking</span>
              </li>
            </ul>
          </div>
          <p className="text-xs text-blue-300">Powered by Azure AI Foundry · Multi-agent system</p>
        </div>

        {/* Right panel */}
        <div className="flex flex-1 flex-col items-center justify-center px-8 py-12 bg-white">
          <div className="w-full max-w-sm">
            <div className="flex justify-center mb-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="white" className="h-6 w-6" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
                </svg>
              </div>
            </div>
            <h1 className="font-heading text-2xl font-bold text-slate-900 text-center mb-1">Welcome back</h1>
            <p className="text-sm text-slate-500 text-center mb-8">Enter your learner code to continue</p>

            <div className="space-y-4">
              <div>
                <label htmlFor="learner-code" className="section-label block mb-2">Learner Code</label>
                <input
                  id="learner-code"
                  type="text"
                  value={learnerId}
                  onChange={(e) => { setLearnerId(e.target.value); setLoginError(""); }}
                  onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                  placeholder="EMP-001"
                  className="input"
                />
                {loginError && (
                  <p className="mt-1.5 text-xs text-rose-600">{loginError}</p>
                )}
              </div>
              <button onClick={handleLogin} className="btn-primary w-full">
                Sign in
              </button>
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-xs text-blue-700">
                ℹ Demo codes: EMP-001 · EMP-002 · EMP-003 · EMP-004 · EMP-005
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Screen 2: DASHBOARD
  // ---------------------------------------------------------------------------

  if (screen === "dashboard" && learnerProfile) {
    return (
      <div className="flex h-screen flex-col overflow-hidden bg-slate-50">
        <AppHeader
          onLogout={handleLogout}
          learnerId={learnerProfile.learner_id}
          learnerRoles={learnerProfile.roles}
        />

        <div className="flex flex-1 overflow-hidden">
          <main className="flex-1 overflow-y-auto px-6 py-8">
            <div className="mx-auto max-w-2xl space-y-6 animate-fade-in">

              {/* Learner profile card */}
              <div className="card border-l-4 border-l-blue-600 overflow-hidden">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-100">
                        <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-heading font-bold text-slate-900">{learnerProfile.learner_id}</p>
                        <p className="text-xs text-slate-500">{learnerProfile.roles.join(" · ")} · {learnerProfile.seniority}-level</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-3 mt-3 text-xs text-slate-600">
                      <span>Team: {learnerProfile.team_id}</span>
                      <span>{learnerProfile.study_hours_per_week}h/week</span>
                      <span className="flex items-center gap-1">
                        <svg className="h-3.5 w-3.5 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" />
                        </svg>
                        {learnerProfile.streak_days} day streak
                      </span>
                    </div>
                  </div>

                  {/* Readiness score */}
                  <div className="text-right shrink-0">
                    <p className="section-label mb-1">Readiness</p>
                    <p className={`text-lg font-bold ${readiness >= 70 ? "text-emerald-600" : readiness >= 40 ? "text-amber-500" : "text-rose-500"}`}>
                      {readiness}%
                    </p>
                    <div className="w-24 h-1.5 rounded-full bg-slate-100 mt-1">
                      <div
                        className={`h-full rounded-full ${readiness >= 70 ? "bg-emerald-500" : readiness >= 40 ? "bg-amber-400" : "bg-rose-400"}`}
                        style={{ width: `${readiness}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Certifications section */}
              <div>
                <p className="section-label mb-3">Certifications</p>

                {/* Completed */}
                {completedCerts.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-slate-400 mb-2">Completed</p>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {completedCerts.map((cert) => (
                        <div key={cert.cert_id} className="bg-slate-50 border border-slate-200 rounded-xl p-4 opacity-75">
                          <div className="flex items-center gap-2 mb-1">
                            <svg className="h-4 w-4 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span className="font-heading text-xs font-bold text-slate-700">{cert.cert_id}</span>
                          </div>
                          <p className="text-xs text-slate-500">{cert.cert_name}</p>
                          {cert.completedAt && <p className="text-xs text-slate-400 mt-0.5">{cert.completedAt}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* In progress */}
                {inProgressCerts.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-slate-400 mb-2">In progress</p>
                    <div className="space-y-2">
                      {inProgressCerts.map((cert) => (
                        <button
                          key={cert.cert_id}
                          type="button"
                          onClick={() => { setSelectedCert(cert); setScreen("cert-detail"); }}
                          className="card w-full cursor-pointer hover:border-blue-300 hover:shadow-md transition-all text-left"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-heading text-sm font-bold text-slate-900">{cert.cert_id}</span>
                                <span className="text-xs text-slate-500 truncate">{cert.cert_name}</span>
                              </div>
                              {cert.overallProgress !== undefined && (
                                <>
                                  <div className="w-full h-1.5 rounded-full bg-slate-100 mb-1">
                                    <div className="h-full rounded-full bg-blue-500" style={{ width: `${cert.overallProgress}%` }} />
                                  </div>
                                  <p className="text-xs text-slate-500">
                                    {cert.overallProgress}% complete
                                    {cert.learningPath && ` · ${cert.learningPath.length} resources`}
                                    {cert.assessments && cert.assessments.length > 0 && ` · ${cert.assessments.length} assessment${cert.assessments.length > 1 ? "s" : ""}`}
                                  </p>
                                </>
                              )}
                            </div>
                            <svg className="h-4 w-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                            </svg>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* New cert CTA */}
                <div className="card border border-blue-200 bg-blue-50">
                  <p className="font-heading text-sm font-semibold text-blue-900 mb-1">✦ Ready to earn a new certification?</p>
                  <p className="text-xs text-blue-700 mb-4">Let AI guide your learning path.</p>
                  <button
                    onClick={() => setScreen("topic-selection")}
                    className="btn-primary text-sm"
                  >
                    + Start new certification
                  </button>
                </div>
              </div>
            </div>
          </main>

          <ChatSidebar
            messages={[{
              id: "welcome",
              role: "assistant",
              content: "Hi! I'm your AI learning assistant. Select a certification below to start a new learning journey, or tap an in-progress cert to review your progress.",
              isStreaming: false,
            }]}
            isRunning={false}
            activeToolCalls={[]}
            error={null}
            onSend={() => {}}
            disabled={true}
          />
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Screen 3: CERT DETAIL
  // ---------------------------------------------------------------------------

  if (screen === "cert-detail" && selectedCert !== null) {
    return (
      <div className="flex h-screen flex-col overflow-hidden bg-slate-50">
        <AppHeader
          onBack={() => setScreen("dashboard")}
          backLabel="Dashboard"
          onLogout={handleLogout}
          learnerId={learnerProfile?.learner_id}
          learnerRoles={learnerProfile?.roles}
        />

        <div className="flex flex-1 overflow-hidden">
          <main className="flex-1 overflow-y-auto px-6 py-8">
            <div className="mx-auto max-w-2xl space-y-6 animate-fade-in">

              {/* Cert header card */}
              <div className="card border-l-4 border-l-blue-600">
                <h2 className="font-heading text-lg font-bold text-slate-900">{selectedCert.cert_id}</h2>
                <p className="text-sm text-slate-600">{selectedCert.cert_name}</p>
                {selectedCert.overallProgress !== undefined && (
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-slate-500 mb-1">
                      <span>Overall progress</span>
                      <span>{selectedCert.overallProgress}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-blue-500" style={{ width: `${selectedCert.overallProgress}%` }} />
                    </div>
                  </div>
                )}
              </div>

              {/* Learning Path */}
              {selectedCert.learningPath && selectedCert.learningPath.length > 0 && (
                <section>
                  <h3 className="section-label mb-3">Learning Path</h3>
                  <div className="space-y-2">
                    {selectedCert.learningPath.map((item, i) => (
                      <div key={i} className="card flex items-start gap-3">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-600 mt-0.5">
                          {i + 1}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-800">{item.title}</p>
                          <p className="text-xs text-slate-500">
                            {item.estimated_hours}h
                            {item.domain_name && ` · ${item.domain_name}`}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Study Plan */}
              {selectedCert.studyPlan && selectedCert.studyPlan.length > 0 && (
                <section>
                  <h3 className="section-label mb-3">Study Plan</h3>
                  <div className="space-y-2">
                    {selectedCert.studyPlan.map((session, i) => (
                      <div key={i} className="card flex items-center gap-4">
                        <div className="text-xs font-semibold text-slate-600 shrink-0 w-24">{session.date}</div>
                        <div className="flex-1">
                          <div className="flex flex-wrap gap-1">
                            {session.topics.map((t) => (
                              <span key={t} className="rounded-full px-2 py-0.5 text-xs bg-slate-100 text-slate-600">{t}</span>
                            ))}
                          </div>
                        </div>
                        <span className="text-xs font-medium text-blue-600 shrink-0">{session.hours}h</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Engagement */}
              {selectedCert.engagementSummary && (
                <section>
                  <h3 className="section-label mb-3">Engagement</h3>
                  <div className="card">
                    <div className="flex flex-wrap gap-6 text-sm">
                      <div>
                        <p className="section-label mb-1">Preferred slot</p>
                        <p className="font-medium capitalize text-slate-800">{selectedCert.engagementSummary.preferred_slot}</p>
                      </div>
                      <div>
                        <p className="section-label mb-1">Reminders sent</p>
                        <p className="font-medium text-slate-800">{selectedCert.engagementSummary.reminders_sent}</p>
                      </div>
                      {selectedCert.engagementSummary.next_reminder && (
                        <div>
                          <p className="section-label mb-1">Next reminder</p>
                          <p className="font-medium text-slate-800">
                            {new Date(selectedCert.engagementSummary.next_reminder).toLocaleString()}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </section>
              )}

              {/* Assessments */}
              {selectedCert.assessments && selectedCert.assessments.length > 0 && (
                <section>
                  <h3 className="section-label mb-3">Assessments</h3>
                  <div className="space-y-2">
                    {selectedCert.assessments.map((assessment) => (
                      <div key={assessment.attempt} className="card">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-semibold text-slate-800">Attempt {assessment.attempt}</span>
                          <span className={`phase-badge ${assessment.passed ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-rose-50 text-rose-700 border border-rose-200"}`}>
                            {assessment.passed ? "Passed" : "Failed"} · {assessment.score}%
                          </span>
                        </div>
                        {assessment.weak_areas.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {assessment.weak_areas.map((area) => (
                              <span key={area} className="rounded-full px-2 py-0.5 text-xs bg-amber-50 text-amber-700 border border-amber-200">{area}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Continue CTA */}
              <div className="pb-8">
                <button
                  onClick={() => {
                    if (learnerProfile) {
                      setSelectedTopics(learnerProfile.current_skills.slice(0, 5));
                    }
                    setScreen("topic-selection");
                  }}
                  className="btn-primary w-full"
                >
                  Continue this certification
                </button>
              </div>
            </div>
          </main>

          <ChatSidebar
            messages={[{
              id: "cert-welcome",
              role: "assistant",
              content: `Here's your progress for ${selectedCert.cert_name}. Start a new session to continue learning.`,
              isStreaming: false,
            }]}
            isRunning={false}
            activeToolCalls={[]}
            error={null}
            onSend={() => {}}
            disabled={true}
          />
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Screen 4: TOPIC SELECTION
  // ---------------------------------------------------------------------------

  if (screen === "topic-selection") {
    return (
      <div className="flex h-screen flex-col overflow-hidden bg-slate-50">
        <AppHeader
          onBack={() => setScreen("dashboard")}
          backLabel="Dashboard"
          onLogout={handleLogout}
          learnerId={learnerProfile?.learner_id}
          learnerRoles={learnerProfile?.roles}
        />

        <div className="flex flex-1 overflow-hidden">
          <main className="flex-1 flex flex-col overflow-hidden">
            {/* Scrollable topic area */}
            <div className="flex-1 overflow-y-auto px-6 pt-6 pb-2">
              <div className="mx-auto max-w-3xl animate-fade-in space-y-4">
                {/* Context banner */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100">
                      <svg className="h-3.5 w-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                      </svg>
                    </div>
                    <div>
                      <span className="text-xs font-bold text-slate-800">{effectiveLearnerId}</span>
                      {learnerProfile && <span className="ml-2 text-xs text-slate-500">{learnerProfile.roles.join(" · ")}</span>}
                    </div>
                  </div>
                  <p className="section-label">Select up to 10 topics</p>
                </div>

                <TopicPicker selectedTopics={selectedTopics} onChange={setSelectedTopics} />
              </div>
            </div>

            {/* Sticky CTA footer */}
            <div className="shrink-0 border-t border-slate-200 bg-white px-6 py-4">
              <div className="mx-auto max-w-3xl">
                {selectedTopics.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-1.5">
                    {selectedTopics.map((id) => {
                      const label = AZURE_TOPICS.find((t) => t.id === id)?.label ?? id;
                      return (
                        <span key={id} className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2.5 py-1 text-xs font-medium text-blue-700">
                          {label}
                          <button
                            type="button"
                            aria-label={`Remove ${label}`}
                            onClick={() => setSelectedTopics(selectedTopics.filter((t) => t !== id))}
                            className="ml-0.5 text-blue-400 hover:text-blue-700 transition-colors leading-none"
                          >×</button>
                        </span>
                      );
                    })}
                  </div>
                )}
                <button
                  onClick={handleStartSession}
                  disabled={!canStart}
                  className="btn-primary w-full py-3.5 text-base font-semibold"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                  {selectedTopics.length > 0
                    ? `Start learning session · ${selectedTopics.length} topic${selectedTopics.length > 1 ? "s" : ""} selected`
                    : "Select topics to continue"}
                </button>
              </div>
            </div>
          </main>

          <ChatSidebar
            messages={[{
              id: "topic-welcome",
              role: "assistant",
              content: "Configure your session by selecting the topics you want to focus on, then start your personalized learning journey.",
              isStreaming: false,
            }]}
            isRunning={false}
            activeToolCalls={[]}
            error={null}
            onSend={() => {}}
            disabled={true}
          />
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Screen 5: ACTIVE SESSION (existing agent flow)
  // ---------------------------------------------------------------------------

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-slate-50">
      <AppHeader
        showPhase={sessionStarted}
        phase={phase}
        learnerId={learnerId || learnerProfile?.learner_id}
      />

      {/* Body: main content + chat sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Exam mode: ExamInterface takes the full viewport — chat hidden */}
        {sessionStarted && phase === "exam_in_progress" && examQuestions.length > 0 ? (
          <div className="flex-1 overflow-hidden">
            <ExamInterface
              questions={examQuestions}
              onSubmit={handleSubmitAssessment}
            />
          </div>
        ) : (
          <>
            <main className="flex-1 overflow-y-auto px-6 py-8">
              <div className="space-y-8 animate-fade-in">
                {/* Learner info + cert banner */}
                <section className="card overflow-hidden p-0">
                  <div className="flex">
                    <div className="w-1 bg-blue-600 rounded-l-xl shrink-0" />
                    <div className="flex-1">
                      <div className="px-5 py-4 flex items-center justify-between gap-4 border-b border-slate-100">
                        <div>
                          <p className="section-label mb-0.5">Learner</p>
                          <p className="text-base font-bold text-slate-900">
                            {(workflowState.learner as LearnerContext | undefined)?.learner_id ?? learnerId}
                          </p>
                          {(() => {
                            const lc = workflowState.learner as LearnerContext | undefined;
                            const role = lc?.roles?.[0] ?? lc?.role;
                            const seniority = lc?.seniority;
                            if (!role && !seniority) return null;
                            return (
                              <p className="text-xs text-slate-500 mt-0.5">
                                {[role, seniority ? `${seniority}-level` : null].filter(Boolean).join(" · ")}
                              </p>
                            );
                          })()}
                        </div>
                        {certDisplay ? (
                          <div className="text-right">
                            <p className="section-label mb-0.5">Target certification</p>
                            <p className="text-sm font-bold text-blue-600">{certDisplay}</p>
                          </div>
                        ) : (
                          <div className="text-right">
                            <p className="section-label mb-0.5">Certification</p>
                            <p className="text-sm italic text-slate-400">Determining…</p>
                          </div>
                        )}
                      </div>
                      {activeTopicLabels.length > 0 && (
                        <div className="px-5 py-3">
                          <p className="section-label mb-2">Topics</p>
                          <div className="flex flex-wrap gap-1.5">
                            {activeTopicLabels.map((label) => (
                              <span
                                key={label}
                                className="rounded-full px-2.5 py-1 text-xs font-medium bg-slate-100 border border-slate-200 text-slate-600"
                              >
                                {label}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </section>

                {certOptions.length > 0 && phase === "awaiting_cert_selection" && (
                  <>
                    <CertOptionsPanel
                      options={certOptions}
                      onSelect={(certId) => sendMessage(certId)}
                    />
                    <CuratorReasoningPanel
                      reasoning={curatorReasoning}
                      kbActivity={curatorKbActivity}
                    />
                  </>
                )}

                {learningPath.length > 0 && (
                  <section aria-labelledby="path-heading">
                    <h2 id="path-heading" className="section-label mb-4">Learning Path</h2>
                    <CourseSection
                      certId={recommendedCertId ?? learningPath[0]?.cert_id ?? ""}
                      certName={recommendedCertName ?? certDisplay ?? "Azure Certification"}
                      items={learningPath}
                      priorityDomains={priorityDomains}
                    />
                  </section>
                )}

                {scheduleContext && (
                  <section aria-labelledby="prefs-heading">
                    <h2 id="prefs-heading" className="section-label mb-3">Schedule Preferences</h2>
                    <div className="card flex flex-wrap gap-5 text-sm">
                      <div>
                        <p className="section-label mb-1">Study days</p>
                        <p className="font-medium text-slate-800">{scheduleContext.preferred_study_days.join(", ")}</p>
                      </div>
                      <div>
                        <p className="section-label mb-1">Session length</p>
                        <p className="font-semibold text-slate-800 tabular-nums">{scheduleContext.session_duration_hours}h</p>
                      </div>
                      <div>
                        <p className="section-label mb-1">Preferred slot</p>
                        <p className="font-medium capitalize text-slate-800">{scheduleContext.preferred_slot}</p>
                      </div>
                      <div>
                        <p className="section-label mb-1">Weekly capacity</p>
                        <p className="font-semibold text-slate-800 tabular-nums">{scheduleContext.capacity_hours_per_week}h/week</p>
                      </div>
                      {scheduleContext.is_fallback && (
                        <p className="w-full text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                          No calendar data found — using default preferences.
                        </p>
                      )}
                    </div>
                  </section>
                )}

                {timelineSessions.length > 0 && (
                  <section aria-labelledby="plan-heading">
                    <h2 id="plan-heading" className="section-label mb-4">Study Plan</h2>
                    <StudyPlanTimeline sessions={timelineSessions} milestones={studyMilestones} />
                  </section>
                )}

                {engagementProposal && (
                  <section aria-labelledby="engagement-heading">
                    <h2 id="engagement-heading" className="section-label mb-4">Engagement Plan</h2>
                    <EngagementProposalView
                      proposal={engagementProposal}
                      studySessions={timelineSessions as StudySessionRef[]}
                      studyMilestones={studyMilestones as StudyMilestoneRef[]}
                      onConfirm={engagementConfirmed ? undefined : handleEngagementConfirm}
                      onAdjust={handleEngagementAdjust}
                    />
                    {showAdjustMessage && !engagementConfirmed && (
                      <p className="mt-3 text-xs text-slate-400 text-center">
                        Alert customization coming soon.
                      </p>
                    )}
                  </section>
                )}

                {phase === "assessing" && assessmentResult && (
                  <section aria-labelledby="assessment-heading">
                    <h2 id="assessment-heading" className="section-label mb-4">Assessment</h2>
                    <AssessmentPanel
                      questions={[]}
                      currentQuestionIndex={0}
                      selectedAnswer={selectedAnswer}
                      result={assessmentResult}
                      onSelectAnswer={setSelectedAnswer}
                      onSubmitAnswer={() => {}}
                      onBackToStudying={() => {
                        setScreen("dashboard");
                        setLearnerId("");
                        setSelectedTopics([]);
                      }}
                    />
                  </section>
                )}

                {(phase === "passed" || phase === "failed" || phase === "exam_failed") && latestAssessmentFull && (
                  <section aria-labelledby="results-heading">
                    <h2 id="results-heading" className="section-label mb-4">Assessment Results</h2>
                    <AssessmentResults
                      score={latestAssessmentFull.score}
                      passed={latestAssessmentFull.passed}
                      weakAreas={latestAssessmentFull.weak_areas}
                      perQuestionResults={latestAssessmentFull.per_question_results ?? []}
                      questions={frozenExamQuestionsRef.current.length > 0 ? frozenExamQuestionsRef.current : examQuestions}
                      reasoningDistribution={(latestAssessmentFull as { reasoning_distribution?: string | null }).reasoning_distribution ?? null}
                      recommendedCertName={recommendedCertName ?? null}
                      recommendedCertId={recommendedCertId ?? null}
                      onRetry={phase === "exam_failed" ? handleRetryAssessment : undefined}
                    />
                  </section>
                )}

                {(phase === "planning" || phase === "studying") && learningPath.length === 0 && (
                  <div className="flex flex-col items-center gap-4 py-20">
                    <div className="relative h-10 w-10">
                      <div className="absolute inset-0 rounded-full border-2 border-blue-100" />
                      <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-blue-600" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-semibold text-slate-700">
                        {phase === "planning" ? "Planning your learning path…" : "Building study schedule…"}
                      </p>
                      <p className="text-xs mt-1 text-slate-500">Azure AI agents are working on your personalized plan</p>
                    </div>
                  </div>
                )}
              </div>
            </main>

            {/* AG-UI chat sidebar (normal mode — not exam) */}
            <ChatSidebar
              messages={messages}
              isRunning={isRunning}
              activeToolCalls={activeToolCalls}
              error={error}
              onSend={sendMessage}
              showHITL={showHITL && !hitlToolCall}
              hitlHours={0}
              onHITLConfirm={handleHITLConfirm}
              onHITLDecline={handleHITLDecline}
              engagementConfirmed={engagementConfirmed}
            />
          </>
        )}
      </div>

      {showConfirmToast && (
        <div
          className="fixed bottom-6 right-6 z-50 rounded-2xl px-5 py-3.5 shadow-lg text-sm font-semibold animate-fade-in flex items-center gap-2.5 bg-emerald-600 text-white"
          role="status"
          aria-live="polite"
        >
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Alerts activated — study reminders scheduled.
        </div>
      )}
    </div>
  );
}
