import client from "./client";

import type { ScheduleJSON } from "../types";

export interface TableDiffChange {
  job_id: number | string;
  job_name?: string;
  current_rows: Array<Record<string, unknown>>;
  proposed_rows: Array<Record<string, unknown>>;
}

export async function fetchJsonDiff(currentJson: ScheduleJSON, proposedJson: ScheduleJSON): Promise<string> {
  const { data } = await client.post("/diff/json", {
    current_json: currentJson,
    proposed_json: proposedJson
  });
  return data.diff as string;
}

export async function fetchTableDiff(
  currentJson: ScheduleJSON,
  proposedJson: ScheduleJSON
): Promise<TableDiffChange[]> {
  const { data } = await client.post("/diff/table", {
    current_json: currentJson,
    proposed_json: proposedJson
  });
  return data.changes as TableDiffChange[];
}
