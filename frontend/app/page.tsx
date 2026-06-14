"use client";

import { useEffect, useRef, useState } from "react";
import { useAgentChat, type AgentName, type KBActivity, type CertOption } from "@/app/hooks/useAgentChat";
import { AZURE_TOPICS, getTopicsByFamily } from "@/app/lib/topics";

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
  planning: "bg-amber-100 text-amber-700",
  studying: "bg-blue-100 text-blue-700",
  awaiting_assessment: "bg-violet-100 text-violet-700",
  assessing: "bg-pink-100 text-pink-700",
  exam_in_progress: "bg-violet-100 text-violet-700",
  passed: "bg-emerald-100 text-emerald-700",
  failed: "bg-rose-100 text-rose-700",
  exam_failed: "bg-rose-100 text-rose-700",
  max_retries_reached: "bg-rose-100 text-rose-700",
  awaiting_cert_selection: "bg-amber-100 text-amber-700",
  awaiting_path_confirmation: "bg-blue-100 text-blue-700",
};

const AGENT_LABELS: Record<AgentName, string> = {
  curator: "Curator Agent",
  study_plan: "Study Plan Agent",
  engagement: "Engagement Agent",
  assessment: "Assessment Agent",
  certification_advisor: "Assessment Agent",
};

const AGENT_COLORS: Record<AgentName, string> = {
  curator: "bg-amber-100 text-amber-700",
  study_plan: "bg-blue-100 text-blue-700",
  engagement: "bg-violet-100 text-violet-700",
  assessment: "bg-pink-100 text-pink-700",
  certification_advisor: "bg-pink-100 text-pink-700",
};

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

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

  return (
    <div className="space-y-4">
      {Array.from(grouped.entries()).map(([family, topics]) => (
        <div key={family}>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">
            {family}
          </p>
          <div className="flex flex-wrap gap-2">
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
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors
                    ${selected
                      ? "border-blue-600 bg-blue-600 text-white"
                      : "border-slate-300 bg-white text-slate-700 hover:border-blue-400 hover:text-blue-600"
                    }
                    ${atMax ? "cursor-not-allowed opacity-40" : "cursor-pointer"}
                  `}
                >
                  {topic.label}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      <p className="text-xs text-slate-400">
        {selectedTopics.length}/10 topics selected — pick 1–10
      </p>
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
}: ChatSidebarProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeToolCalls]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  }

  return (
    <aside className="flex w-[420px] shrink-0 flex-col border-l border-slate-200 bg-slate-50">
      {/* Header */}
      <div className="border-b border-slate-200 px-4 py-3">
        <p className="text-xs font-semibold text-slate-700">Learning Assistant</p>
        <p className="text-xs text-slate-400">Powered by AG-UI</p>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-xs text-slate-400 text-center pt-4">
            Hi! I&apos;m your AI learning assistant. Start your session to begin.
          </p>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            {msg.role === "assistant" && (
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full mb-1 inline-block ${
                msg.agentName && AGENT_COLORS[msg.agentName]
                  ? AGENT_COLORS[msg.agentName]
                  : "bg-slate-100 text-slate-500"
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
            {msg.role === "assistant" && msg.certOptions && msg.certOptions.length > 0 && (
              <CertSelectionCard
                options={msg.certOptions}
                onSelect={(certId) => onSend(certId)}
              />
            )}
            {msg.role === "assistant" && msg.workflowStatus === "awaiting_path_confirmation" && (
              <div className="mb-2 w-full max-w-[85%] rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
                Your learning path is ready. Type any message to confirm and generate your study plan.
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-slate-800 shadow-sm border border-slate-100"
              }`}
            >
              {msg.content || (msg.isStreaming ? (
                <span className="inline-flex items-center gap-1">
                  <span className="h-1 w-1 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="h-1 w-1 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="h-1 w-1 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "300ms" }} />
                </span>
              ) : "")}
              {msg.isStreaming && msg.content && (
                <span className="ml-0.5 inline-block h-3 w-0.5 bg-slate-500 animate-pulse" />
              )}
            </div>
          </div>
        ))}

        {/* Active tool call indicators */}
        {activeToolCalls.map((tc) => (
          <div key={tc.toolCallId} className="flex justify-start">
            <div className="max-w-[85%] rounded-xl px-3 py-2 text-xs bg-amber-50 text-amber-700 border border-amber-100 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
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
          <div className="rounded-lg bg-rose-50 border border-rose-100 px-3 py-2 text-xs text-rose-700">
            {error}
          </div>
        )}

        {engagementConfirmed && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3 space-y-1">
            <p className="text-xs font-semibold text-emerald-700">✓ Plan & reminders confirmed</p>
            <p className="text-xs text-emerald-600 leading-relaxed">
              Your study plan and engagement reminders are all set. Come back whenever you feel ready to take your assessment.
            </p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-slate-200 p-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything…"
          disabled={isRunning}
          className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs
                     text-slate-900 placeholder:text-slate-400
                     focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500
                     disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || isRunning}
          className="shrink-0 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white
                     hover:bg-blue-700 disabled:opacity-40 transition-colors"
        >
          Send
        </button>
      </form>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Main learner dashboard
// ---------------------------------------------------------------------------

export default function LearnerPage() {
  const [learnerId, setLearnerId] = useState("");
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [sessionStarted, setSessionStarted] = useState(false);
  const [showHITL, setShowHITL] = useState(false);

  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const frozenExamQuestionsRef = useRef<AssessmentQuestion[]>([]);
  const [engagementConfirmed, setEngagementConfirmed] = useState(false);
  const [showConfirmToast, setShowConfirmToast] = useState(false);
  const [showAdjustMessage, setShowAdjustMessage] = useState(false);

  const { messages, agentState: workflowState, isRunning, activeToolCalls, error, resetSession, sendMessage } =
    useAgentChat<WorkflowState>(`${BACKEND_URL}/api/learn`);

  // Detect HITL tool call
  const hitlToolCall = activeToolCalls.find((tc) => tc.name === "confirm_assessment_readiness");
  useEffect(() => {
    if (hitlToolCall) setShowHITL(true);
  }, [hitlToolCall]);

  const canStart = learnerId.trim().length > 0 && selectedTopics.length > 0;

  function handleStartSession() {
    if (!canStart) return;
    const topicLabels = selectedTopics
      .map((id) => AZURE_TOPICS.find((t) => t.id === id)?.label ?? id)
      .join(", ");

    const initialState: WorkflowState = {
      learner: {
        learner_id: learnerId.trim(),
        employee_id: learnerId.trim(),
        topics: selectedTopics,
        role: "developer",
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
    setSessionStarted(true);
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
    // Freeze questions before resetSession wipes the workflow state.
    frozenExamQuestionsRef.current = examQuestions;
    // Build updated state with answers populated — the next POST to /api/learn
    // will include this state, which triggers SeedExecutor's exam_in_progress branch.
    const updatedState: WorkflowState = {
      ...(workflowState as WorkflowState),
      assessment_answers: answers,
      workflow_status: "exam_in_progress",
    };
    resetSession(updatedState);
    // Small delay so the agent ref is initialised before send
    setTimeout(() => sendMessage("Assessment submitted"), 50);
  }

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

  // Assessment exam data
  const examQuestions = (workflowState.assessment_questions as AssessmentQuestion[] | undefined) ?? [];
  const latestAssessmentFull = latestAssessment ?? null;

  // Cert info — available once curator runs
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

  // Topics in the active session (from workflowState after session starts)
  const activeLearnerTopics = (workflowState.learner as LearnerContext | undefined)?.topics ?? [];
  const activeTopicLabels = activeLearnerTopics
    .map((id) => AZURE_TOPICS.find((t) => t.id === id)?.label ?? id);

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Header */}
      <header className="shrink-0 border-b border-slate-200 bg-white/80 backdrop-blur-sm z-10">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="white" className="h-4 w-4" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
              </svg>
            </div>
            <h1 className="text-sm font-bold text-slate-900">Enterprise Learning System</h1>
          </div>

          {sessionStarted && PHASE_LABELS[phase] && (
            <span className={`phase-badge ${PHASE_COLORS[phase]}`}>
              <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
              {PHASE_LABELS[phase]}
            </span>
          )}

          <a href="/manager" className="text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors">
            Manager view
          </a>
        </div>
      </header>

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
          <main className="flex-1 overflow-y-auto px-4 py-8">
          {!sessionStarted ? (
            <div className="mx-auto max-w-2xl animate-fade-in">
              <div className="card text-center mb-6">
                <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome back</h2>
                <p className="text-sm text-slate-500">Start an AI-guided certification learning session.</p>
              </div>

              <div className="card space-y-6">
                {/* Learner ID */}
                <div>
                  <label htmlFor="learner-id" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Learner ID
                  </label>
                  <input
                    id="learner-id"
                    type="text"
                    value={learnerId}
                    onChange={(e) => setLearnerId(e.target.value)}
                    placeholder="e.g. EMP-001"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                {/* Topic picker */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-3">
                    Select topics you want to learn
                  </label>
                  <TopicPicker selectedTopics={selectedTopics} onChange={setSelectedTopics} />
                </div>

                {/* Selected topic chips summary */}
                {selectedTopics.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-700 mb-2">Selected topics</p>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedTopics.map((id) => {
                        const label = AZURE_TOPICS.find((t) => t.id === id)?.label ?? id;
                        return (
                          <span
                            key={id}
                            className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2.5 py-0.5 text-xs text-blue-700"
                          >
                            {label}
                            <button
                              type="button"
                              aria-label={`Remove ${label}`}
                              onClick={() => setSelectedTopics(selectedTopics.filter((t) => t !== id))}
                              className="ml-0.5 text-blue-400 hover:text-blue-700"
                            >
                              ×
                            </button>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                <button
                  onClick={handleStartSession}
                  disabled={!canStart}
                  className="btn-primary w-full"
                >
                  Start learning session
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-8 animate-fade-in">
              {/* Learner info + inferred cert banner */}
              <section className="card space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold text-slate-500">Learner</p>
                    <p className="text-sm font-bold text-slate-900">
                      {(workflowState.learner as LearnerContext | undefined)?.learner_id ?? learnerId}
                    </p>
                  </div>
                  {certDisplay ? (
                    <div className="text-right">
                      <p className="text-xs font-semibold text-slate-500">Recommended certification</p>
                      <p className="text-sm font-bold text-blue-700">{certDisplay}</p>
                    </div>
                  ) : (
                    <div className="text-right">
                      <p className="text-xs font-semibold text-slate-500">Certification</p>
                      <p className="text-sm text-slate-400 italic">Determining…</p>
                    </div>
                  )}
                </div>

                {/* Active topic chips */}
                {activeTopicLabels.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 mb-1.5">Topics</p>
                    <div className="flex flex-wrap gap-1.5">
                      {activeTopicLabels.map((label) => (
                        <span
                          key={label}
                          className="rounded-full bg-slate-100 border border-slate-200 px-2.5 py-0.5 text-xs text-slate-600"
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </section>

              {learningPath.length > 0 && (
                <section aria-labelledby="path-heading">
                  <h2 id="path-heading" className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">
                    Learning Path
                  </h2>
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
                  <h2 id="prefs-heading" className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">
                    Schedule Preferences Considered
                  </h2>
                  <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 flex flex-wrap gap-4 text-sm">
                    <div>
                      <p className="text-xs text-slate-400 mb-0.5">Study days</p>
                      <p className="font-medium text-slate-700">{scheduleContext.preferred_study_days.join(", ")}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 mb-0.5">Session length</p>
                      <p className="font-medium text-slate-700">{scheduleContext.session_duration_hours}h</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 mb-0.5">Preferred slot</p>
                      <p className="font-medium text-slate-700 capitalize">{scheduleContext.preferred_slot}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 mb-0.5">Weekly capacity</p>
                      <p className="font-medium text-slate-700">{scheduleContext.capacity_hours_per_week}h/week</p>
                    </div>
                    {scheduleContext.is_fallback && (
                      <p className="w-full text-xs text-amber-600">⚠ No calendar data found — using default preferences.</p>
                    )}
                  </div>
                </section>
              )}

              {timelineSessions.length > 0 && (
                <section aria-labelledby="plan-heading">
                  <h2 id="plan-heading" className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">
                    Study Plan
                  </h2>
                  <StudyPlanTimeline sessions={timelineSessions} milestones={studyMilestones} />
                </section>
              )}

              {engagementProposal && (
                <section aria-labelledby="engagement-heading">
                  <h2 id="engagement-heading" className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">
                    Engagement Plan
                  </h2>
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

              {(phase === "assessing") && assessmentResult && (
                <section aria-labelledby="assessment-heading">
                  <h2 id="assessment-heading" className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">
                    Assessment
                  </h2>
                  <AssessmentPanel
                    questions={[]}
                    currentQuestionIndex={0}
                    selectedAnswer={selectedAnswer}
                    result={assessmentResult}
                    onSelectAnswer={setSelectedAnswer}
                    onSubmitAnswer={() => {}}
                    onBackToStudying={() => {
                      setSessionStarted(false);
                      setLearnerId("");
                      setSelectedTopics([]);
                    }}
                  />
                </section>
              )}

              {(phase === "passed" || phase === "failed" || phase === "exam_failed") && latestAssessmentFull && (
                <section aria-labelledby="results-heading">
                  <h2 id="results-heading" className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">
                    Assessment Results
                  </h2>
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
                <div className="flex flex-col items-center gap-3 py-16 text-slate-400">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
                  <p className="text-sm">
                    {phase === "planning" ? "Planning your learning path…" : "Building study schedule…"}
                  </p>
                </div>
              )}
            </div>
          )}
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
          className="fixed bottom-6 right-6 z-50 rounded-xl px-5 py-3 shadow-xl text-sm font-medium animate-fade-in"
          style={{ background: "#0f3d2a", border: "1px solid #1a5a3d", color: "#34d399" }}
          role="status"
          aria-live="polite"
        >
          ✓ Alerts activated! Your study reminders have been scheduled.
        </div>
      )}
    </div>
  );
}
