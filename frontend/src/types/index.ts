export interface Operation {
  op_id: string | number;
  op_n?: string;
  re: string;
  pre?: Array<string | number>;
  [key: string]: unknown;
}

export interface JobInstance {
  job_id: number;
  job_n?: string;
  operations: Operation[];
}

export interface ScheduleJSON {
  J: number;
  M: number;
  instances: JobInstance[];
  [key: string]: unknown;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SolverRunResult {
  algorithm: "ppo" | "iaoa_gns";
  summary: {
    best: number;
    average: number;
    worst: number;
  };
  makespans: number[];
  runs: Array<Record<string, unknown>>;
  snapshot: Record<string, unknown>;
}

export interface SolverRunRecord {
  run_id: string;
  algorithm: "ppo" | "iaoa_gns";
  status: string;
  created_at: string;
  config: Record<string, unknown>;
  results?: SolverRunResult;
  error?: string;
}
