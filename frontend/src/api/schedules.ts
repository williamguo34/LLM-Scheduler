import client from "./client";

import type { ChatMessage, ScheduleJSON } from "../types";

export type JobTableRow = Record<string, unknown>;

export interface JobTable {
  job_id: number;
  job_name?: string;
  rows: JobTableRow[];
}

export interface GenerateSchedulePayload {
  user_message: string;
  model?: string;
  api_key?: string;
  base_url?: string;
}

export interface UpdateSchedulePayload {
  current_json: ScheduleJSON;
  instruction: string;
  previous_messages?: ChatMessage[];
  model?: string;
  api_key?: string;
  base_url?: string;
}

export interface CSVAdjustmentPayload {
  csv_path: string;
  instruction: string;
  model?: string;
  api_key?: string;
  base_url?: string;
}

export interface DecisionPayload {
  instruction: string;
  model?: string;
  api_key?: string;
  base_url?: string;
}

export async function generateSchedule(payload: GenerateSchedulePayload): Promise<ScheduleJSON> {
  const { data } = await client.post("/schedules/generate", payload);
  return data.schedule_json as ScheduleJSON;
}

export async function updateSchedule(payload: UpdateSchedulePayload): Promise<ScheduleJSON> {
  const { data } = await client.post("/schedules/update", payload);
  return data.schedule_json as ScheduleJSON;
}

export async function updateSchedulePatch(payload: UpdateSchedulePayload): Promise<ScheduleJSON> {
  const { data } = await client.post("/schedules/update_patch", payload);
  return data.schedule_json as ScheduleJSON;
}

export async function decideRoute(payload: DecisionPayload): Promise<string> {
  const { data } = await client.post("/llm/route", payload);
  return data.decision as string;
}

export async function adjustSolutionCSV(
  payload: CSVAdjustmentPayload
): Promise<{ csv_path: string; preview: unknown[] }> {
  const { data } = await client.post("/schedules/csv-adjustment", payload);
  return data;
}

export async function fetchSchema(): Promise<unknown> {
  const { data } = await client.get("/schedules/schema");
  return data.schema;
}

export async function transformScheduleToTables(schedule: ScheduleJSON): Promise<JobTable[]> {
  const { data } = await client.post("/schedules/transform", {
    direction: "to_tables",
    payload: schedule
  });
  return data.tables as JobTable[];
}

export async function transformTablesToSchedule(
  tables: JobTable[],
  original: ScheduleJSON
) {
  const { data } = await client.post("/schedules/transform", {
    direction: "from_tables",
    payload: { tables },
    original_json: original
  });
  return data.schedule_json as ScheduleJSON;
}
