import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface SettingsState {
  apiBaseUrl: string;
  modelName: string;
  apiKey: string;
  baseUrl: string;
  modelWeightsDir: string;
  ppoRuns: number;
  autoApply: boolean;
  autoSolve: boolean;
  updateSettings: (changes: Partial<Omit<SettingsState, "updateSettings">>) => void;
}

const DEFAULT_MODEL_WEIGHTS = "saved_network/FJSP_J10M10/best_value000";

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      apiBaseUrl: "/api",
      modelName: "",
      apiKey: "",
      baseUrl: "",
      modelWeightsDir: DEFAULT_MODEL_WEIGHTS,
      ppoRuns: 1,
      autoApply: false,
      autoSolve: false,
      updateSettings: (changes) =>
        set((state) => ({
          ...state,
          ...changes
        }))
    }),
    {
      name: "fjsp-settings"
    }
  )
);
