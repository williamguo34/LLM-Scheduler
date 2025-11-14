import type { CSSProperties, ChangeEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { fetchSolverRun, runSolver, type RunSolverPayload } from "../api/solver";
import { usePolling } from "../hooks/usePolling";
import { useAppStore } from "../store/useAppStore";
import { useSettingsStore } from "../store/useSettingsStore";
import type { SolverRunRecord } from "../types";
import { buildAssetFileUrl, isImageLike } from "../utils/assetActions";
import { pickDefaultSolver } from "../utils/solverHelpers";

interface RunArtifactView {
  run_number?: number;
  makespan?: number;
  pool_csv?: string;
  gantt_file?: string;
  [key: string]: unknown;
}

const layoutStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "24px"
};

const cardStyle: CSSProperties = {
  backgroundColor: "#ffffff",
  borderRadius: "12px",
  padding: "24px",
  boxShadow: "0 8px 24px rgba(15, 23, 42, 0.08)",
  display: "flex",
  flexDirection: "column",
  gap: "16px"
};

const historyTableStyle: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse"
};

const SolverHubPage = () => {
  const { schedule, solverRuns, upsertSolverRun, activeRunId, setActiveRun } = useAppStore();
  const { modelWeightsDir, ppoRuns, updateSettings } = useSettingsStore();
  const [algorithm, setAlgorithm] = useState<RunSolverPayload["algorithm"]>(() =>
    pickDefaultSolver(schedule)
  );
  const [iaoaConfig, setIaoaConfig] = useState({
    population_size: 30,
    max_iterations: 50,
    num_runs: 1,
    timeout_seconds: 600
  });
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeRecord: SolverRunRecord | undefined = useMemo(() => {
    if (activeRunId) {
      return solverRuns.find((run) => run.run_id === activeRunId) ?? undefined;
    }
    return solverRuns[0];
  }, [activeRunId, solverRuns]);

  useEffect(() => {
    setAlgorithm(pickDefaultSolver(schedule));
  }, [schedule]);

  const isPollingEnabled =
    Boolean(activeRecord) && !["completed", "failed"].includes(activeRecord?.status ?? "");

  usePolling(
    async () => {
      if (!activeRecord || ["completed", "failed"].includes(activeRecord.status)) return;
      try {
        const refreshed = await fetchSolverRun(activeRecord.run_id);
        upsertSolverRun(refreshed);
      } catch (err) {
        console.warn(err);
      }
    },
    5000,
    isPollingEnabled
  );

  const artifactRuns = (activeRecord?.results?.runs ?? []) as RunArtifactView[];
  const snapshotArtifacts = activeRecord?.results?.snapshot as Record<string, unknown> | undefined;

  const handleRun = async () => {
    if (!schedule) {
      setError("Generate or import a schedule JSON first.");
      return;
    }
    setIsRunning(true);
    setError(null);
    try {
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
        payload.iaoa_gns = iaoaConfig;
      }
      const record = await runSolver(payload);
      upsertSolverRun(record);
      setActiveRun(record.run_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start the solver.";
      setError(message);
    } finally {
      setIsRunning(false);
    }
  };

  const handleIaoaChange = (evt: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = evt.target;
    setIaoaConfig((prev) => ({
      ...prev,
      [name]: Number(value)
    }));
  };

const statusBadge = (status: string) => {
  const colors: Record<string, string> = {
    queued: "#f59e0b",
    running: "#2563eb",
    completed: "#16a34a",
    failed: "#dc2626"
  };
    return (
      <span
        style={{
          display: "inline-block",
          padding: "4px 10px",
          borderRadius: "999px",
          backgroundColor: colors[status] ?? "#9ca3af",
          color: "#fff",
          fontSize: "0.8rem"
        }}
      >
        {status}
      </span>
    );
  };

  const handleArtifactAction = async (path?: string | null) => {
    if (!path) return;
    if (path.startsWith("http://") || path.startsWith("https://")) {
      window.open(path, "_blank");
      return;
    }
    if (navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(path);
        alert("Path copied. Open it from your terminal or file browser.");
        return;
      } catch {
        /* ignore copy errors */
      }
    }
    window.prompt("Copy path:", path);
  };

  return (
    <div style={layoutStyle}>
      <div>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>Solver Hub</h1>
        <p style={{ color: "#4b5563", margin: "6px 0 0" }}>
          Choose an algorithm, configure parameters, and monitor solver runs. Supports PPO RL and IAOA + GNS.
        </p>
      </div>

      {!schedule && (
        <div style={{ ...cardStyle, color: "#dc2626" }}>
          Generate in Problem Builder or import a schedule JSON on Home before launching a solver run.
        </div>
      )}

      <section style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Configuration</h2>
          {statusBadge(activeRecord?.status ?? "idle")}
        </div>
        <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <input
              type="radio"
              name="algorithm"
              checked={algorithm === "ppo"}
              onChange={() => setAlgorithm("ppo")}
            />
            PPO
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <input
              type="radio"
              name="algorithm"
              checked={algorithm === "iaoa_gns"}
              onChange={() => setAlgorithm("iaoa_gns")}
            />
            IAOA + GNS
          </label>
        </div>

        {algorithm === "ppo" ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontWeight: 600 }}>MODEL_WEIGHTS_DIR</span>
              <input
                type="text"
                value={modelWeightsDir}
                onChange={(evt) => updateSettings({ modelWeightsDir: evt.target.value })}
                style={{ borderRadius: "8px", border: "1px solid #d1d5db", padding: "10px" }}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontWeight: 600 }}>Runs</span>
              <input
                type="number"
                min={1}
                max={10}
                value={ppoRuns}
                onChange={(evt) => updateSettings({ ppoRuns: Number(evt.target.value) })}
                style={{ borderRadius: "8px", border: "1px solid #d1d5db", padding: "10px" }}
              />
            </label>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span>Population Size</span>
              <input
                type="number"
                min={5}
                max={200}
                name="population_size"
                value={iaoaConfig.population_size}
                onChange={handleIaoaChange}
                style={{ borderRadius: "8px", border: "1px solid #d1d5db", padding: "10px" }}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span>Max Iterations</span>
              <input
                type="number"
                min={10}
                max={500}
                name="max_iterations"
                value={iaoaConfig.max_iterations}
                onChange={handleIaoaChange}
                style={{ borderRadius: "8px", border: "1px solid #d1d5db", padding: "10px" }}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span>Runs</span>
              <input
                type="number"
                min={1}
                max={10}
                name="num_runs"
                value={iaoaConfig.num_runs}
                onChange={handleIaoaChange}
                style={{ borderRadius: "8px", border: "1px solid #d1d5db", padding: "10px" }}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span>Timeout (s)</span>
              <input
                type="number"
                min={60}
                max={3600}
                name="timeout_seconds"
                value={iaoaConfig.timeout_seconds}
                onChange={handleIaoaChange}
                style={{ borderRadius: "8px", border: "1px solid #d1d5db", padding: "10px" }}
              />
            </label>
          </div>
        )}

        <button
          type="button"
          onClick={handleRun}
          disabled={isRunning || !schedule}
          style={{
            alignSelf: "flex-start",
            border: "none",
            borderRadius: "8px",
            padding: "12px 24px",
            backgroundColor: schedule ? "#2563eb" : "#9ca3af",
            color: "#fff",
            fontWeight: 600,
            cursor: schedule ? "pointer" : "not-allowed"
          }}
        >
          {isRunning ? "Running..." : "Start solving"}
        </button>

        {error && <div style={{ color: "#dc2626" }}>{error}</div>}
      </section>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Run Status</h2>
        {activeRecord ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div>Run ID: {activeRecord.run_id}</div>
            <div>
              Algorithm: <strong>{activeRecord.algorithm.toUpperCase()}</strong>
            </div>
            <div>
              Status: {statusBadge(activeRecord.status)}
            </div>
            {activeRecord.results && (
              <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                <div>Best: {activeRecord.results.summary.best}</div>
                <div>Average: {activeRecord.results.summary.average}</div>
                <div>Worst: {activeRecord.results.summary.worst}</div>
              </div>
            )}
            {artifactRuns.length ? (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontWeight: 600 }}>Run artifacts</div>
                {artifactRuns.map((run, idx) => {
                  const runNumber = (run.run_number ?? run["run_number"] ?? idx + 1) as number;
                  const makespan = (run.makespan ?? run["makespan"]) as number | undefined;
                  const poolPath = (run.pool_csv ?? run["pool_csv"]) as string | undefined;
                  const rawGantt = (run.gantt_generated ?? run["gantt_generated"] ?? run.gantt_file ?? run["gantt_file"]) as string | undefined;
                  const ganttPath = rawGantt || undefined;
                  return (
                    <div
                      key={`artifact-${runNumber}-${idx}`}
                      style={{
                        border: "1px solid #e5e7eb",
                      borderRadius: "8px",
                      padding: "10px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                      background: "#f9fafb"
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>
                      Run {runNumber}
                      {typeof makespan === "number" ? ` — Makespan ${makespan}` : ""}
                    </div>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      {poolPath && (
                        <button
                          type="button"
                          onClick={() => handleArtifactAction(poolPath)}
                          style={{
                            border: "1px solid #d1d5db",
                            borderRadius: "6px",
                            padding: "6px 10px",
                            backgroundColor: "transparent",
                            cursor: "pointer"
                          }}
                        >
                          Open solution CSV
                        </button>
                      )}
                      {ganttPath && (
                        <button
                          type="button"
                          onClick={() => handleArtifactAction(ganttPath)}
                          style={{
                            border: "1px solid #d1d5db",
                            borderRadius: "6px",
                            padding: "6px 10px",
                            backgroundColor: "transparent",
                            cursor: "pointer"
                          }}
                        >
                          Preview Gantt
                        </button>
                      )}
                    </div>
                    {ganttPath && isImageLike(ganttPath) && (
                      <img
                        src={buildAssetFileUrl(ganttPath)}
                        alt={`Gantt Run ${runNumber}`}
                        style={{
                          width: "100%",
                          borderRadius: "8px",
                          border: "1px solid #e5e7eb",
                          marginTop: "8px"
                        }}
                      />
                    )}
                  </div>
                );
              })}
              </div>
            ) : null}
            {snapshotArtifacts && (
              <div style={{ marginTop: "12px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {(["pool_csv", "instance_json", "instance_npy"] as const).map((key) => {
                  const path = snapshotArtifacts?.[key] as string | undefined;
                  if (!path) return null;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => handleArtifactAction(path as string)}
                      style={{
                        border: "1px solid #d1d5db",
                        borderRadius: "6px",
                        padding: "6px 10px",
                        backgroundColor: "transparent",
                        cursor: "pointer"
                      }}
                    >
                      Download {key.replace("_", " ")}
                    </button>
                  );
                })}
              </div>
            )}
            {activeRecord.error && (
              <div style={{ color: "#dc2626" }}>Error: {activeRecord.error}</div>
            )}
          </div>
        ) : (
          <div style={{ color: "#6b7280" }}>No runs recorded yet.</div>
        )}
      </section>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>History</h2>
        {solverRuns.length === 0 ? (
          <div style={{ color: "#6b7280" }}>No solver history.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={historyTableStyle}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #e5e7eb" }}>Run ID</th>
                  <th style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #e5e7eb" }}>Algorithm</th>
                  <th style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #e5e7eb" }}>Status</th>
                  <th style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #e5e7eb" }}>Best</th>
                  <th style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #e5e7eb" }}>Created</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {solverRuns.map((run) => (
                  <tr key={run.run_id}>
                    <td style={{ padding: "8px", borderBottom: "1px solid #f3f4f6" }}>{run.run_id}</td>
                    <td style={{ padding: "8px", borderBottom: "1px solid #f3f4f6" }}>{run.algorithm.toUpperCase()}</td>
                    <td style={{ padding: "8px", borderBottom: "1px solid #f3f4f6" }}>{statusBadge(run.status)}</td>
                    <td style={{ padding: "8px", borderBottom: "1px solid #f3f4f6" }}>
                      {run.results?.summary.best ?? "—"}
                    </td>
                    <td style={{ padding: "8px", borderBottom: "1px solid #f3f4f6" }}>
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: "8px", borderBottom: "1px solid #f3f4f6" }}>
                      <button
                        type="button"
                        onClick={() => setActiveRun(run.run_id)}
                        style={{
                          border: "1px solid #d1d5db",
                          borderRadius: "6px",
                          padding: "6px 12px",
                          backgroundColor: activeRunId === run.run_id ? "#1d4ed8" : "transparent",
                          color: activeRunId === run.run_id ? "#fff" : "#1f2937",
                          cursor: "pointer"
                        }}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default SolverHubPage;
