import { runSolver, type RunSolverPayload } from "../api/solver";
import { useAppStore } from "../store/useAppStore";
import { useSettingsStore } from "../store/useSettingsStore";
import type { ScheduleJSON } from "../types";

const DEFAULT_IAOA_GNS_CONFIG = {
  population_size: 30,
  max_iterations: 50,
  num_runs: 1,
  timeout_seconds: 600
};

export function pickDefaultSolver(schedule: ScheduleJSON | null): RunSolverPayload["algorithm"] {
  if (!schedule) return "iaoa_gns";
  const jobs = schedule.instances ?? [];
  const jobCount = schedule.J ?? jobs.length;
  const hasTenJobs = jobCount === 10 && jobs.length === 10;
  const hasTenOperationsPerJob =
    hasTenJobs && jobs.every((job) => (job.operations?.length ?? 0) === 10);
  return hasTenOperationsPerJob ? "ppo" : "iaoa_gns";
}

export async function triggerAutoSolve(): Promise<{ ok: boolean; runId?: string; error?: string }> {
  const { schedule, upsertSolverRun, setActiveRun } = useAppStore.getState();
  const { modelWeightsDir, ppoRuns } = useSettingsStore.getState();

  if (!schedule) {
    return { ok: false, error: "No schedule to solve." };
  }

  try {
    const algorithm = pickDefaultSolver(schedule);
    const payload: RunSolverPayload = {
      schedule_json: schedule,
      algorithm
    };
    if (algorithm === "ppo") {
      payload.ppo = {
        model_weights_dir: modelWeightsDir,
        runs: ppoRuns
      };
    } else {
      payload.iaoa_gns = DEFAULT_IAOA_GNS_CONFIG;
    }
    const record = await runSolver(payload);
    upsertSolverRun(record);
    setActiveRun(record.run_id);
    return { ok: true, runId: record.run_id };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to start solver";
    return { ok: false, error: message };
  }
}
