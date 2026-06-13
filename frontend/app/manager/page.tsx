"use client";

import { useEffect, useRef, useState } from "react";
import { useAgentChat } from "@/app/hooks/useAgentChat";

import ReadinessGauge from "@/components/ReadinessGauge";
import TeamRiskTable from "@/components/TeamRiskTable";

// ---------------------------------------------------------------------------
// Types — mirror backend TeamDashboard Pydantic schema
// ---------------------------------------------------------------------------

interface TeamMemberSummary {
  anonymizedId: string;
  status: "On Track" | "At Risk" | "Completed";
  hoursStudied: number;
  readinessScore: number;
  targetCert: string;
}

interface TeamDashboard extends Record<string, unknown> {
  team_id: string;
  avg_readiness: number;
  at_risk_count: number;
  completed_count: number;
  members: TeamMemberSummary[];
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Chat sidebar (manager variant)
// ---------------------------------------------------------------------------

interface ManagerChatSidebarProps {
  messages: Array<{ id: string; role: "user" | "assistant"; content: string; isStreaming: boolean }>;
  isRunning: boolean;
  activeToolCalls: Array<{ toolCallId: string; name: string }>;
  error: string | null;
  onSend: (text: string) => void;
}

function ManagerChatSidebar({ messages, isRunning, activeToolCalls, error, onSend }: ManagerChatSidebarProps) {
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
    <aside className="flex w-80 shrink-0 flex-col border-l border-slate-200 bg-slate-50">
      <div className="border-b border-slate-200 px-4 py-3">
        <p className="text-xs font-semibold text-slate-700">Manager Assistant</p>
        <p className="text-xs text-slate-400">Powered by AG-UI</p>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-xs text-slate-400 text-center pt-4">
            Hi! I can help you understand your team&apos;s certification readiness. Enter a Team ID to get started.
          </p>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-slate-800 text-white"
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

        {activeToolCalls.map((tc) => (
          <div key={tc.toolCallId} className="flex justify-start">
            <div className="max-w-[85%] rounded-xl px-3 py-2 text-xs bg-amber-50 text-amber-700 border border-amber-100 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
              {tc.name.replace(/_/g, " ")}…
            </div>
          </div>
        ))}

        {error && (
          <div className="rounded-lg bg-rose-50 border border-rose-100 px-3 py-2 text-xs text-rose-700">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t border-slate-200 p-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything…"
          disabled={isRunning}
          className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs
                     text-slate-900 placeholder:text-slate-400
                     focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500
                     disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || isRunning}
          className="shrink-0 rounded-lg bg-slate-800 px-3 py-2 text-xs font-medium text-white
                     hover:bg-slate-900 disabled:opacity-40 transition-colors"
        >
          Send
        </button>
      </form>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Manager dashboard
// ---------------------------------------------------------------------------

export default function ManagerPage() {
  const [teamId, setTeamId] = useState("");
  const [sessionStarted, setSessionStarted] = useState(false);

  const { messages, agentState: dashboard, isRunning, activeToolCalls, error, resetSession, sendMessage } =
    useAgentChat<TeamDashboard>(`${BACKEND_URL}/api/manager`);

  function handleLoadTeam() {
    if (!teamId.trim()) return;
    const initialState: TeamDashboard = {
      team_id: teamId.trim(),
      avg_readiness: 0,
      at_risk_count: 0,
      completed_count: 0,
      members: [],
    };
    resetSession(initialState);
    setSessionStarted(true);
    setTimeout(() => sendMessage(`Load insights for team ${teamId.trim()}`), 50);
  }

  const members = (dashboard.members as TeamMemberSummary[] | undefined) ?? [];
  const hasData = members.length > 0 || ((dashboard.avg_readiness as number | undefined) ?? 0) > 0;

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Header */}
      <header className="shrink-0 border-b border-slate-200 bg-white/80 backdrop-blur-sm z-10">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="white" className="h-4 w-4" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
              </svg>
            </div>
            <h1 className="text-sm font-bold text-slate-900">Manager Insights</h1>
          </div>
          <a href="/" className="text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors">
            Learner view
          </a>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 overflow-y-auto px-4 py-8">
          {/* Team ID input */}
          <div className="card mb-8 flex flex-col gap-3 sm:flex-row sm:items-end max-w-2xl">
            <div className="flex-1">
              <label htmlFor="team-id" className="block text-xs font-semibold text-slate-700 mb-1.5">
                Team ID
              </label>
              <input
                id="team-id"
                type="text"
                value={teamId}
                onChange={(e) => setTeamId(e.target.value)}
                placeholder="e.g. TEAM-A"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <button onClick={handleLoadTeam} disabled={!teamId.trim()} className="btn-primary sm:w-auto">
              Load team
            </button>
          </div>

          {!sessionStarted ? (
            <div className="flex flex-col items-center gap-3 py-16 text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor" className="h-16 w-16 text-slate-200" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
              </svg>
              <p className="text-sm">Enter a Team ID to view insights.</p>
            </div>
          ) : !hasData && isRunning ? (
            <div className="flex flex-col items-center gap-3 py-16 text-slate-400">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-400 border-t-transparent" />
              <p className="text-sm">Loading team data…</p>
            </div>
          ) : hasData ? (
            <div className="space-y-8 animate-fade-in max-w-4xl">
              <section aria-labelledby="summary-heading">
                <h2 id="summary-heading" className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">
                  Team Summary
                </h2>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                  <div className="card flex flex-col items-center gap-2">
                    <ReadinessGauge
                      score={(dashboard.avg_readiness as number) ?? 0}
                      label="Avg Readiness"
                      size="md"
                    />
                  </div>
                  <div className="card flex flex-col items-center justify-center gap-1">
                    <p className="text-3xl font-bold text-rose-600">{(dashboard.at_risk_count as number) ?? 0}</p>
                    <p className="text-xs text-slate-500">At Risk</p>
                  </div>
                  <div className="card flex flex-col items-center justify-center gap-1">
                    <p className="text-3xl font-bold text-emerald-600">{(dashboard.completed_count as number) ?? 0}</p>
                    <p className="text-xs text-slate-500">Completed</p>
                  </div>
                </div>
              </section>

              {((dashboard.members as TeamMemberSummary[]) ?? []).length > 0 && (
                <section aria-labelledby="members-heading">
                  <h2 id="members-heading" className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">
                    Learner Overview
                  </h2>
                  <TeamRiskTable members={members} />
                </section>
              )}
            </div>
          ) : null}
        </main>

        {/* AG-UI chat sidebar */}
        <ManagerChatSidebar
          messages={messages}
          isRunning={isRunning}
          activeToolCalls={activeToolCalls}
          error={error}
          onSend={sendMessage}
        />
      </div>
    </div>
  );
}
