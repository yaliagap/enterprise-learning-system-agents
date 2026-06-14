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
  curator: "Curator Agent",
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
          <p className="section-label mb-2">{family}</p>
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
                  className={`topic-pill ${
                    selected
                      ? "topic-pill-active"
                      : atMax
                      ? "topic-pill-disabled"
                      : "topic-pill-inactive"
                  }`}
                >
                  {topic.label}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      <p className="text-xs font-medium text-slate-500">
        {selectedTopics.length}/10 topics selected
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
    <aside className="flex w-[420px] shrink-0 flex-col border-l border-slate-200 bg-white">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100">
        <p className="font-heading text-sm font-semibold text-slate-900">Learning Assistant</p>
        <p className="text-slate-400 mt-0.5" style={{ fontSize: "11px" }}>
          Powered by AG-UI · Azure AI Foundry
        </p>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
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
            {msg.role === "assistant" && msg.certOptions && msg.certOptions.length > 0 && (
              <CertSelectionCard
                options={msg.certOptions}
                onSelect={(certId) => onSend(certId)}
              />
            )}
            {msg.role === "assistant" && msg.workflowStatus === "awaiting_path_confirmation" && (
              <div className="mb-2 w-full max-w-[85%] rounded-xl px-3 py-2.5 text-xs font-medium bg-blue-50 border border-blue-200 text-blue-700">
                Your learning path is ready. Type any message to confirm and generate your study plan.
              </div>
            )}
            <div className={msg.role === "user" ? "bubble-user" : "bubble-assistant"}>
              {msg.content || (msg.isStreaming ? (
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
          placeholder="Ask anything…"
          disabled={isRunning}
          className="input flex-1"
        />
        <button
          type="submit"
          disabled={!input.trim() || isRunning}
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
    useAgentChat<WorkflowState>(process.env.NEXT_PUBLIC_AGENT_URL || `${BACKEND_URL}/api/learn`);

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
    <div className="flex h-screen flex-col overflow-hidden bg-slate-50">
      {/* Header */}
      <header className="shrink-0 z-20 border-b border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between px-6 py-3">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="white" className="h-5 w-5" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
              </svg>
            </div>
            <div>
              <h1 className="font-heading text-sm font-bold leading-none text-slate-900 tracking-tight">
                Enterprise Learning System
              </h1>
              <p className="text-blue-600 font-medium mt-0.5" style={{ fontSize: "10px" }}>
                Azure AI Foundry
              </p>
            </div>
          </div>

          {/* Status badge */}
          {sessionStarted && PHASE_LABELS[phase] && (
            <span className={`phase-badge ${PHASE_COLORS[phase]}`}>
              <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" aria-hidden="true" />
              {PHASE_LABELS[phase]}
            </span>
          )}

          <a href="/manager" className="btn-ghost text-xs font-medium tracking-wide">
            Manager View
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
          <main className="flex-1 overflow-y-auto px-6 py-8">
          {!sessionStarted ? (
            <div className="mx-auto max-w-2xl animate-fade-in">
              {/* Hero welcome card */}
              <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-600 to-blue-700 p-8 mb-6 text-white shadow-md">
                <div className="flex items-center gap-2 mb-5">
                  <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold bg-white/20 text-white border border-white/30">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 animate-pulse" />
                    Azure AI Foundry
                  </span>
                </div>
                <h2 className="font-heading text-2xl font-bold mb-2 tracking-tight">
                  Enterprise Learning System
                </h2>
                <p className="text-sm leading-relaxed text-blue-100">
                  Start an AI-guided certification learning session powered by Azure AI Foundry Hosted Agents.
                </p>
              </div>

              <div className="card space-y-6">
                {/* Learner ID */}
                <div>
                  <label htmlFor="learner-id" className="section-label block mb-2">
                    Learner ID
                  </label>
                  <input
                    id="learner-id"
                    type="text"
                    value={learnerId}
                    onChange={(e) => setLearnerId(e.target.value)}
                    placeholder="e.g. EMP-001"
                    className="input"
                  />
                </div>

                {/* Topic picker */}
                <div>
                  <label className="section-label block mb-3">
                    Select topics you want to learn
                  </label>
                  <TopicPicker selectedTopics={selectedTopics} onChange={setSelectedTopics} />
                </div>

                {/* Selected topic chips summary */}
                {selectedTopics.length > 0 && (
                  <div>
                    <p className="section-label mb-2">Selected</p>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedTopics.map((id) => {
                        const label = AZURE_TOPICS.find((t) => t.id === id)?.label ?? id;
                        return (
                          <span
                            key={id}
                            className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium bg-blue-50 border border-blue-200 text-blue-700"
                          >
                            {label}
                            <button
                              type="button"
                              aria-label={`Remove ${label}`}
                              onClick={() => setSelectedTopics(selectedTopics.filter((t) => t !== id))}
                              className="ml-0.5 text-blue-400 hover:text-blue-600 transition-colors"
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
                  className="btn-primary w-full py-3"
                >
                  Start learning session
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-8 animate-fade-in">
              {/* Learner info + cert banner */}
              <section className="card overflow-hidden p-0">
                {/* Left accent bar for premium feel */}
                <div className="flex">
                  <div className="w-1 bg-blue-600 rounded-l-xl shrink-0" />
                  <div className="flex-1">
                    <div className="px-5 py-4 flex items-center justify-between gap-4 border-b border-slate-100">
                      <div>
                        <p className="section-label mb-0.5">Learner</p>
                        <p className="text-base font-bold text-slate-900">
                          {(workflowState.learner as LearnerContext | undefined)?.learner_id ?? learnerId}
                        </p>
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

              {(phase === "assessing") && assessmentResult && (
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
                      setSessionStarted(false);
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
