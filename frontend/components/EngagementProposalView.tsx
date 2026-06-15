"use client";

import { useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WorkIQSignals {
  focusPeakStart: string;
  focusPeakEnd: string;
  meetingWindowStart: string;
  meetingWindowEnd: string;
  preferredChannel: string;
  avgStreakDays: number;
  responseRateByChannel: Record<string, number>;
  teamType: string;
}

export interface EngagementAlert {
  type: "reminder" | "milestone" | "motivation" | "risk";
  channel: "slack" | "email";
  timing: string;
  triggerCondition: string;
  previewText: string;
  repeatCount: string;
  reasoning: string;
}

export interface EngagementProposal {
  workIQSignals: WorkIQSignals;
  alerts: EngagementAlert[];
  totalAlerts: number;
  totalMilestones: number;
  totalWeeks: number;
  activeChannels: number;
}

export interface StudySessionRef {
  session_id?: string;
  date: string;
  topics: string[];
  hours?: number;
}

export interface StudyMilestoneRef {
  milestone_id: string;
  domain_name: string;
  target_week: number;
  target_date: string;
}

interface Props {
  proposal: EngagementProposal;
  studySessions: StudySessionRef[];
  studyMilestones: StudyMilestoneRef[];
  onConfirm?: () => void;
  onAdjust: () => void;
}

// ---------------------------------------------------------------------------
// Per-type style config (light palette)
// ---------------------------------------------------------------------------

const ALERT_STYLES = {
  reminder: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    badgeBg: "bg-blue-100",
    badgeText: "text-blue-700",
    accent: "text-blue-600",
    reasoningBorder: "border-blue-300",
    icon: "🔔",
    label: "REMINDER",
  },
  milestone: {
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    badgeBg: "bg-emerald-100",
    badgeText: "text-emerald-700",
    accent: "text-emerald-600",
    reasoningBorder: "border-emerald-300",
    icon: "🏆",
    label: "MILESTONE",
  },
  motivation: {
    bg: "bg-violet-50",
    border: "border-violet-200",
    badgeBg: "bg-violet-100",
    badgeText: "text-violet-700",
    accent: "text-violet-600",
    reasoningBorder: "border-violet-300",
    icon: "⚡",
    label: "MOTIVATION",
  },
  risk: {
    bg: "bg-orange-50",
    border: "border-orange-200",
    badgeBg: "bg-orange-100",
    badgeText: "text-orange-700",
    accent: "text-orange-600",
    reasoningBorder: "border-orange-300",
    icon: "🛡",
    label: "RISK",
  },
} as const;

const SECTION_GROUPS: { label: string; types: EngagementAlert["type"][] }[] = [
  { label: "SESSION REMINDERS", types: ["reminder"] },
  { label: "MILESTONES", types: ["milestone"] },
  { label: "MOTIVATION & RISK", types: ["motivation", "risk"] },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function ChannelBadge({ channel }: { channel: "slack" | "email" }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-white border border-slate-200 px-2 py-0.5 text-xs text-slate-600">
      {channel === "slack" ? "💬 Slack" : "✉ Email"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Expandable session list (for reminder)
// ---------------------------------------------------------------------------

function SessionAccordion({ sessions }: { sessions: StudySessionRef[] }) {
  const [open, setOpen] = useState(false);
  if (sessions.length === 0) return null;
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
      >
        <span>{open ? "▾" : "▸"}</span>
        {open ? "Hide sessions" : `View all ${sessions.length} sessions`}
      </button>
      {open && (
        <div className="mt-2 rounded-lg border border-blue-100 bg-white divide-y divide-slate-100 max-h-52 overflow-y-auto">
          {sessions.map((s, i) => (
            <div key={s.session_id ?? i} className="flex items-start gap-3 px-3 py-2">
              <span className="shrink-0 w-5 text-center text-xs text-slate-400 pt-0.5">
                {i + 1}
              </span>
              <div className="min-w-0">
                <p className="text-xs font-medium text-slate-700">{formatDate(s.date)}</p>
                <p className="text-xs text-slate-500 truncate">{s.topics.join(" · ")}</p>
              </div>
              {s.hours !== undefined && (
                <span className="ml-auto shrink-0 text-xs text-slate-400">{s.hours}h</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expandable milestone list (for milestone alert)
// ---------------------------------------------------------------------------

function MilestoneAccordion({ milestones }: { milestones: StudyMilestoneRef[] }) {
  const [open, setOpen] = useState(false);
  if (milestones.length === 0) return null;
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 hover:text-emerald-800 transition-colors"
      >
        <span>{open ? "▾" : "▸"}</span>
        {open ? "Hide milestones" : `View all ${milestones.length} milestones`}
      </button>
      {open && (
        <div className="mt-2 rounded-lg border border-emerald-100 bg-white divide-y divide-slate-100 max-h-52 overflow-y-auto">
          {milestones.map((m, i) => (
            <div key={m.milestone_id} className="flex items-start gap-3 px-3 py-2">
              <span className="shrink-0 w-5 text-center text-xs text-slate-400 pt-0.5">
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-slate-700">{m.domain_name}</p>
                <p className="text-xs text-slate-500">
                  Target: {formatDate(m.target_date)} · Week {m.target_week}
                </p>
                <p className="text-xs text-emerald-600 mt-0.5 italic">
                  "Completing {m.domain_name} unlocks your next certification milestone."
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Alert card
// ---------------------------------------------------------------------------

function AlertCard({
  alert,
  studySessions,
  studyMilestones,
}: {
  alert: EngagementAlert;
  studySessions: StudySessionRef[];
  studyMilestones: StudyMilestoneRef[];
}) {
  const [reasoningOpen, setReasoningOpen] = useState(false);
  const style = ALERT_STYLES[alert.type];

  return (
    <div className={`rounded-xl p-4 space-y-3 border ${style.bg} ${style.border}`}>
      {/* Header row */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-base" aria-hidden="true">{style.icon}</span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-bold tracking-wider ${style.badgeBg} ${style.badgeText}`}>
            {style.label}
          </span>
          <ChannelBadge channel={alert.channel} />
        </div>
        <span className={`text-xs font-medium ${style.badgeText}`}>
          {alert.repeatCount}
        </span>
      </div>

      {/* Timing + trigger */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>
          <span className={`font-medium ${style.accent}`}>Timing:</span> {alert.timing}
        </span>
        <span>
          <span className={`font-medium ${style.accent}`}>Trigger:</span> {alert.triggerCondition}
        </span>
      </div>

      {/* Preview text */}
      <p className="text-sm font-semibold text-slate-800">{alert.previewText}</p>

      {/* Accordion: sessions for reminder */}
      {alert.type === "reminder" && (
        <SessionAccordion sessions={studySessions} />
      )}

      {/* Accordion: milestones for milestone */}
      {alert.type === "milestone" && (
        <MilestoneAccordion milestones={studyMilestones} />
      )}

      {/* Reasoning toggle */}
      <button
        type="button"
        onClick={() => setReasoningOpen((v) => !v)}
        className={`flex items-center gap-1.5 text-xs font-medium ${style.accent} hover:opacity-80 transition-opacity`}
      >
        <span>ⓘ</span>
        {reasoningOpen ? "Hide reasoning" : "Why this alert?"}
      </button>

      {reasoningOpen && (
        <div className={`rounded-lg bg-white border-l-2 ${style.reasoningBorder} pl-3 pr-2 py-2`}>
          <p className="text-xs text-slate-600 leading-relaxed">{alert.reasoning}</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function EngagementProposalView({
  proposal,
  studySessions,
  studyMilestones,
  onConfirm,
  onAdjust,
}: Props) {
  const { workIQSignals: signals, alerts, totalAlerts, totalMilestones, totalWeeks, activeChannels } = proposal;

  return (
    <div className="space-y-5">
      <div className="space-y-6">
        {/* Work IQ banner */}
        <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold tracking-wider text-blue-600">WORK IQ SIGNALS</p>
            <span className="rounded-full bg-white border border-blue-200 px-2 py-0.5 text-xs font-medium text-blue-600">
              Read automatically
            </span>
          </div>
          <p className="text-xs text-blue-700 leading-relaxed">
            Personalized alerts grounded in your Work IQ profile — timing, channel, and frequency set automatically.
          </p>
          <div className="flex flex-wrap gap-2">
            {[
              `⏰ Focus peak: ${signals.focusPeakStart}–${signals.focusPeakEnd}`,
              `📅 Meetings: ${signals.meetingWindowStart}–${signals.meetingWindowEnd}`,
              `📣 Preferred: ${signals.preferredChannel}`,
              `🔥 Streak: ${signals.avgStreakDays}d avg`,
              `👥 Team: ${signals.teamType}`,
            ].map((chip) => (
              <span
                key={chip}
                className="rounded-full bg-white border border-slate-200 px-3 py-1 text-xs text-slate-600"
              >
                {chip}
              </span>
            ))}
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Total alerts", value: totalAlerts },
            { label: "Milestones", value: totalMilestones },
            { label: "Weeks", value: totalWeeks },
            { label: "Channels", value: activeChannels },
          ].map(({ label, value }) => (
            <div
              key={label}
              className="rounded-xl border border-slate-200 bg-white p-3 text-center shadow-sm"
            >
              <p className="text-2xl font-bold text-slate-900">{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>

        {/* Alert sections */}
        {SECTION_GROUPS.map(({ label, types }) => {
          const sectionAlerts = alerts.filter((a) => types.includes(a.type));
          if (sectionAlerts.length === 0) return null;
          return (
            <section key={label}>
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">
                {label}
              </p>
              <div className="space-y-3">
                {sectionAlerts.map((alert, i) => (
                  <AlertCard
                    key={`${alert.type}-${i}`}
                    alert={alert}
                    studySessions={studySessions}
                    studyMilestones={studyMilestones}
                  />
                ))}
              </div>
            </section>
          );
        })}

        {/* Footer */}
        {onConfirm ? (
          <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-slate-100">
            <button
              onClick={onAdjust}
              className="flex-1 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-700 transition-colors text-center"
            >
              Adjust alerts
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2.5 text-sm font-semibold text-white transition-colors text-center"
            >
              Confirm and activate plan →
            </button>
          </div>
        ) : (
          <div className="pt-2 border-t border-slate-100 flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1.5 text-sm font-medium text-emerald-700">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              Alerts activated — reminders scheduled
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
