import { create } from "zustand";

import type { ChatMessage, ScheduleJSON, SolverRunRecord } from "../types";

interface AppState {
  schedule: ScheduleJSON | null;
  pendingSchedule: ScheduleJSON | null;
  messages: ChatMessage[];
  solverRuns: SolverRunRecord[];
  activeRunId?: string;
  setSchedule: (schedule: ScheduleJSON | null) => void;
  setPendingSchedule: (schedule: ScheduleJSON | null) => void;
  appendMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  upsertSolverRun: (record: SolverRunRecord) => void;
  setActiveRun: (runId?: string) => void;
  resetConversation: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  schedule: null,
  pendingSchedule: null,
  messages: [],
  solverRuns: [],
  activeRunId: undefined,
  setSchedule: (schedule) => set(() => ({ schedule })),
  setPendingSchedule: (pendingSchedule) => set(() => ({ pendingSchedule })),
  appendMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (messages) => set(() => ({ messages })),
  upsertSolverRun: (record) =>
    set((state) => {
      const existingIndex = state.solverRuns.findIndex((run) => run.run_id === record.run_id);
      if (existingIndex >= 0) {
        const solverRuns = state.solverRuns.slice();
        solverRuns[existingIndex] = record;
        return { solverRuns };
      }
      return { solverRuns: [record, ...state.solverRuns] };
    }),
  setActiveRun: (runId) => set(() => ({ activeRunId: runId })),
  resetConversation: () => set(() => ({ messages: [], pendingSchedule: null }))
}));
