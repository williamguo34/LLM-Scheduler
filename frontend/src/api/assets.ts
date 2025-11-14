import client from "./client";

export async function listSolutionPools() {
  const { data } = await client.get("/assets/solution-pools");
  return data.items as Array<{ name: string; path: string }>;
}

export async function listGanttCharts() {
  const { data } = await client.get("/assets/gantt-charts");
  return data.items as Array<{ name: string; path: string }>;
}

export async function listModelWeights() {
  const { data } = await client.get("/assets/models");
  return data.items as Array<{ name: string; path: string }>;
}
