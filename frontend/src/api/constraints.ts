import client from "./client";

import type { ScheduleJSON } from "../types";

export async function checkDeadlines(runId: string, deadlines: number[]) {
  const { data } = await client.post("/constraints/deadlines", {
    run_id: runId,
    deadlines
  });
  return data as { deadlines_path: string; pool_path: string; valid_solutions: number };
}

export async function checkPrecedence(schedule: ScheduleJSON) {
  const { data } = await client.post("/constraints/precedence", {
    schedule_json: schedule
  });
  return data as { precedence_matrix: number[][] | null; precedence_path: string | null };
}
