"use client";

import { useCallback, useRef, useState } from "react";
import { HttpAgent } from "@ag-ui/client";

export type AgentName =
  | "curator"
  | "study_plan"
  | "engagement"
  | "assessment"
  | "certification_advisor";

export interface KBReference {
  title: string;
  url: string;
  type: string;
  score?: number | null;
}

export interface KBActivity {
  query: string;
  response_text?: string;
  references: KBReference[];
}

export interface DomainWeight {
  domain_name: string;
  exam_weight: number;
}

export interface CuratorOutput {
  exam: string;
  user_level: string;
  priority_domains: DomainWeight[];
  recommended_learning_paths: unknown[];
  coverage_summary: string;
  references: KBReference[];
}

export interface CertOption {
  cert_id: string;
  name: string;
  description: string;
  ms_learn_url: string;
  recommendation_pct: number;
  already_obtained: boolean;
  level: string;
}

export interface AgUiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming: boolean;
  agentName?: AgentName;
  kbActivity?: KBActivity;
  curatorOutput?: CuratorOutput;
  certOptions?: CertOption[];
  workflowStatus?: string;
}

export interface ActiveToolCall {
  toolCallId: string;
  name: string;
}

export function useAgentChat<TState extends Record<string, unknown>>(url: string) {
  const [messages, setMessages] = useState<AgUiMessage[]>([]);
  const [agentState, setAgentState] = useState<TState>({} as TState);
  const [isRunning, setIsRunning] = useState(false);
  const [activeToolCalls, setActiveToolCalls] = useState<ActiveToolCall[]>([]);
  const [error, setError] = useState<string | null>(null);
  const agentRef = useRef<HttpAgent | null>(null);
  const currentAgentRef = useRef<AgentName | undefined>(undefined);
  const pendingKbRef = useRef<KBActivity | undefined>(undefined);
  const pendingCuratorOutputRef = useRef<CuratorOutput | undefined>(undefined);
  const pendingCertOptionsRef = useRef<CertOption[] | undefined>(undefined);
  const pendingWorkflowStatusRef = useRef<string | undefined>(undefined);

  const resetSession = useCallback(
    (initialState: TState) => {
      agentRef.current = new HttpAgent({ url, initialState });
      setMessages([]);
      setAgentState(initialState);
      setIsRunning(false);
      setActiveToolCalls([]);
      setError(null);
      pendingKbRef.current = undefined;
      pendingCuratorOutputRef.current = undefined;
      pendingCertOptionsRef.current = undefined;
      pendingWorkflowStatusRef.current = undefined;
    },
    [url],
  );

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isRunning || !agentRef.current) return;

    const agent = agentRef.current;
    const userId = `user-${Date.now()}`;

    agent.addMessage({ id: userId, role: "user", content: text });
    setMessages((prev) => [
      ...prev,
      { id: userId, role: "user", content: text, isStreaming: false },
    ]);
    setIsRunning(true);
    setError(null);

    try {
      await agent.runAgent(
        {},
        {
          onTextMessageStartEvent({ event }) {
            const agentName = currentAgentRef.current;
            const kbActivity = agentName === "curator" ? pendingKbRef.current : undefined;
            const curatorOutput = agentName === "curator" ? pendingCuratorOutputRef.current : undefined;
            const certOptions = pendingCertOptionsRef.current;
            const workflowStatus = pendingWorkflowStatusRef.current;
            pendingKbRef.current = undefined;
            pendingCuratorOutputRef.current = undefined;
            pendingCertOptionsRef.current = undefined;
            pendingWorkflowStatusRef.current = undefined;
            setMessages((prev) => [
              ...prev,
              { id: event.messageId, role: "assistant", content: "", isStreaming: true, agentName, kbActivity, curatorOutput, certOptions, workflowStatus },
            ]);
          },
          onTextMessageContentEvent({ event, textMessageBuffer }) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === event.messageId ? { ...m, content: textMessageBuffer } : m,
              ),
            );
          },
          onTextMessageEndEvent({ event, textMessageBuffer }) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === event.messageId
                  ? { ...m, content: textMessageBuffer, isStreaming: false }
                  : m,
              ),
            );
          },
          onToolCallStartEvent({ event }) {
            setActiveToolCalls((prev) => [
              ...prev,
              { toolCallId: event.toolCallId, name: event.toolCallName },
            ]);
          },
          onToolCallEndEvent({ event }) {
            setActiveToolCalls((prev) =>
              prev.filter((tc) => tc.toolCallId !== event.toolCallId),
            );
          },
          onStateSnapshotEvent({ event }) {
            const snap = event.snapshot as TState & {
              current_agent?: string;
              kb_activity?: KBActivity | null;
              curator_response?: CuratorOutput | null;
              cert_options?: CertOption[] | null;
              workflow_status?: string;
            };
            currentAgentRef.current = (snap.current_agent || undefined) as AgentName | undefined;
            pendingKbRef.current = snap.kb_activity ?? undefined;
            pendingCuratorOutputRef.current = snap.curator_response ?? undefined;
            pendingCertOptionsRef.current = (snap.cert_options && snap.cert_options.length > 0) ? snap.cert_options : undefined;
            pendingWorkflowStatusRef.current = snap.workflow_status ?? undefined;
            setAgentState(snap);
          },
          onRunFinishedEvent() {
            setIsRunning(false);
          },
          onRunErrorEvent({ event }) {
            setError(event.message ?? "Agent run failed");
            setIsRunning(false);
          },
        },
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setIsRunning(false);
    }
  }, [isRunning]);

  return { messages, agentState, isRunning, activeToolCalls, error, resetSession, sendMessage };
}
