import client from "./client";

import type { ScheduleJSON, SolverRunRecord } from "../types";

export interface RunSolverPayload {
  schedule_json: ScheduleJSON;
  algorithm: "ppo" | "iaoa_gns";
  ppo?: {
    model_weights_dir: string;
    runs: number;
  };
  iaoa_gns?: {
    population_size: number;
    max_iterations: number;
    num_runs: number;
    timeout_seconds: number;
    pool_size?: number;
    use_final_population?: boolean;
  };
}

export async function runSolver(payload: RunSolverPayload): Promise<SolverRunRecord> {
  const { data } = await client.post("/solvers/run", payload);
  return data as SolverRunRecord;
}

export async function fetchSolverRun(runId: string): Promise<SolverRunRecord> {
  const { data } = await client.get(`/solvers/run/${runId}`);
  return data as SolverRunRecord;
}
