import type { CSSProperties, FormEvent as ReactFormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { generateSchedule, updateSchedule } from "../api/schedules";
import { fetchJsonDiff, fetchTableDiff, type TableDiffChange } from "../api/diff";
import { useAppStore } from "../store/useAppStore";
import { useSettingsStore } from "../store/useSettingsStore";
import { buildAssetFileUrl, isImageLike } from "../utils/assetActions";
import { triggerAutoSolve } from "../utils/solverHelpers";
import type { ChatMessage, ScheduleJSON } from "../types";

interface RunArtifactView {
  run_number?: number;
  makespan?: number;
  pool_csv?: string;
  gantt_generated?: string;
  gantt_file?: string;
  [key: string]: unknown;
}

const pageStyle: CSSProperties = {
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
  gap: "16px",
  minHeight: "320px"
};

const chatContainerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
  minHeight: "700px"
};

const messagesStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "12px",
  overflowY: "auto",
  maxHeight: "600px",
  paddingRight: "4px"
};

const chatInputStyle: CSSProperties = {
  display: "flex",
  gap: "12px"
};

const toggleRowStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "12px"
};

type RowDiffStatus = "removed" | "added" | "modified" | "unchanged";

interface RowDiffEntry {
  key: string;
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
  status: RowDiffStatus;
  changedColumns: Set<string>;
}

const ROW_KEY_CANDIDATES = ["op_id", "operation_id", "operation", "op_n", "id", "name"];
const COLUMN_ORDER_HINT = ["op_id", "operation_id", "op_n", "operation", "machine", "start", "end", "duration", "processing_time"];

const ROW_COLORS: Record<RowDiffStatus, { background: string; border: string }> = {
  removed: { background: "#fee2e2", border: "#fecaca" },
  added: { background: "#dcfce7", border: "#bbf7d0" },
  modified: { background: "#ffffff", border: "#e5e7eb" },
  unchanged: { background: "#ffffff", border: "#e5e7eb" }
};

const CHANGED_CELL_COLOR = "#fef9c3";

const getRowKey = (row: Record<string, unknown>, fallbackIndex: number): string => {
  for (const field of ROW_KEY_CANDIDATES) {
    const value = row[field];
    if (value !== undefined && value !== null && value !== "") {
      return `${field}:${String(value)}`;
    }
  }
  return `row-${fallbackIndex}`;
};

const isValueEqual = (a: unknown, b: unknown): boolean => {
  if (a === b) return true;
  if (typeof a === "object" && typeof b === "object") {
    try {
      return JSON.stringify(a) === JSON.stringify(b);
    } catch {
      return false;
    }
  }
  return String(a ?? "") === String(b ?? "");
};

const formatCellValue = (value: unknown): string => {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
};

const sortColumns = (columns: string[]): string[] => {
  const weight = (col: string) => {
    const idx = COLUMN_ORDER_HINT.indexOf(col);
    return idx === -1 ? COLUMN_ORDER_HINT.length + col.charCodeAt(0) : idx;
  };
  return [...columns].sort((a, b) => {
    const diff = weight(a) - weight(b);
    return diff !== 0 ? diff : a.localeCompare(b);
  });
};

const ProblemBuilderPage = () => {
  const {
    schedule,
    pendingSchedule,
    messages,
    solverRuns,
    activeRunId,
    setSchedule,
    setPendingSchedule,
    appendMessage,
    resetConversation
  } = useAppStore();
  const {
    modelName,
    apiKey,
    baseUrl,
    autoApply,
    autoSolve,
    updateSettings
  } = useSettingsStore();

  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diffText, setDiffText] = useState("");
  const [diffLoading, setDiffLoading] = useState(false);
  const [activeDiffTab, setActiveDiffTab] = useState<"json" | "table">("table");
  const [tableDiff, setTableDiff] = useState<TableDiffChange[] | null>(null);
  const [tableDiffLoading, setTableDiffLoading] = useState(false);
  const [tableDiffError, setTableDiffError] = useState<string | null>(null);
  const [manualSolveLoading, setManualSolveLoading] = useState(false);
  const [manualSolveError, setManualSolveError] = useState<string | null>(null);
  const [manualSolveDone, setManualSolveDone] = useState(false);
  const [showGuidance, setShowGuidance] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function runDiff() {
      if (!schedule || !pendingSchedule) {
        setDiffText("");
        setDiffLoading(false);
        return;
      }
      setDiffLoading(true);
      try {
        const text = await fetchJsonDiff(schedule, pendingSchedule);
        if (!cancelled) {
          setDiffText(text);
        }
      } catch (err) {
        if (!cancelled) {
          setDiffText("Unable to generate a diff. Please try again shortly.");
        }
      } finally {
        if (!cancelled) {
          setDiffLoading(false);
        }
      }
    }
    runDiff();
    return () => {
      cancelled = true;
    };
  }, [schedule, pendingSchedule]);

  useEffect(() => {
    let cancelled = false;
    async function loadTableDiff() {
      if (activeDiffTab !== "table" || !schedule || !pendingSchedule) {
        if (!schedule || !pendingSchedule) {
          setTableDiff(null);
          setTableDiffError(null);
        }
        return;
      }
      setTableDiffLoading(true);
      setTableDiffError(null);
      try {
        const data = await fetchTableDiff(schedule, pendingSchedule);
        if (!cancelled) {
          setTableDiff(data);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Unable to generate the table diff.";
          setTableDiffError(message);
          setTableDiff(null);
        }
      } finally {
        if (!cancelled) {
          setTableDiffLoading(false);
        }
      }
    }
    loadTableDiff();
    return () => {
      cancelled = true;
    };
  }, [activeDiffTab, schedule, pendingSchedule]);

  const stats = useMemo(() => {
    if (!schedule) return null;
    return {
      jobs: schedule.J ?? schedule.instances?.length ?? 0,
      machines: schedule.M ?? 0,
      operations: schedule.instances?.reduce(
        (total, job) => total + (job.operations?.length ?? 0),
        0
      ) ?? 0
    };
  }, [schedule]);

  useEffect(() => {
    setManualSolveError(null);
    setManualSolveLoading(false);
    setManualSolveDone(false);
  }, [schedule]);

  useEffect(() => {
    setManualSolveError(null);
    setManualSolveLoading(false);
  }, [autoSolve]);

  const llmConfig = useMemo(
    () => ({
      model: modelName || undefined,
      api_key: apiKey || undefined,
      base_url: baseUrl || undefined
    }),
    [apiKey, baseUrl, modelName]
  );

  const autoSolveRecord = useMemo(() => {
    if (!solverRuns.length) return undefined;
    if (activeRunId) {
      return solverRuns.find((run) => run.run_id === activeRunId) ?? solverRuns[0];
    }
    return solverRuns[0];
  }, [activeRunId, solverRuns]);

  const artifactRuns = (autoSolveRecord?.results?.runs ?? []) as RunArtifactView[];
  const showAutoSolveCard = autoSolve || solverRuns.length > 0;
  const showManualSolvePrompt = Boolean(schedule) && !autoSolve && !manualSolveDone;

  const statusBadge = (status?: string) => {
    if (!status) return null;
    const colors: Record<string, string> = {
      queued: "#f59e0b",
      running: "#2563eb",
      completed: "#16a34a",
      failed: "#dc2626"
    };
    const color = colors[status] ?? "#6b7280";
    return (
      <span
        style={{
          padding: "2px 10px",
          borderRadius: "999px",
          fontSize: "0.85rem",
          backgroundColor: `${color}20`,
          color
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

  const handleSend = async (evt: ReactFormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const history = [...messages, userMessage];
    setInput("");
    appendMessage(userMessage);
    setIsSending(true);
    setError(null);

    try {
      let result: ScheduleJSON;
      if (!schedule) {
        result = await generateSchedule({
          user_message: trimmed,
          ...llmConfig
        });
      } else {
        result = await updateSchedule({
          current_json: schedule,
          instruction: trimmed,
          previous_messages: history,
          ...llmConfig
        });
      }

      if (autoApply) {
        applySchedule(result, true);
      } else {
        setPendingSchedule(result);
        appendMessage({
          role: "assistant",
          content: "✅ Generated a new schedule. Review the diff on the right."
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "LLM request failed.";
      setError(message);
      appendMessage({
        role: "assistant",
        content: `⚠️ Unable to process that request: ${message}`
      });
    } finally {
      setIsSending(false);
    }
  };

  const applySchedule = (next: ScheduleJSON, autoApplied = false) => {
    setSchedule(next);
    setPendingSchedule(null);
    setDiffText("");
    appendMessage({
      role: "assistant",
      content: autoApplied ? "✅ Automatically applied the generated schedule." : "✅ Changes applied."
    });
    if (autoSolve) {
      appendMessage({
        role: "assistant",
        content: "🧠 Auto Solve is on—triggering Solver Hub now."
      });
      triggerAutoSolve().then((result) => {
        appendMessage({
          role: "assistant",
          content: result.ok
            ? `🚀 Auto solve started (Run: ${result.runId}).`
            : `⚠️ Auto Solve failed: ${result.error}`
        });
      });
    }
  };

  const handleAccept = () => {
    if (!pendingSchedule) return;
    applySchedule(pendingSchedule);
  };

  const handleReject = () => {
    setPendingSchedule(null);
    setDiffText("");
    appendMessage({
      role: "assistant",
      content: "❌ Discarded the proposed changes."
    });
  };

  const handleManualSolve = async () => {
    if (!schedule || manualSolveLoading) return;
    setManualSolveLoading(true);
    setManualSolveError(null);
    const result = await triggerAutoSolve();
    if (result.ok) {
      appendMessage({
        role: "assistant",
        content: `🚀 Manual solve started (Run: ${result.runId}). Monitor progress in Solver Hub.`
      });
      setManualSolveDone(true);
    } else {
      setManualSolveError(result.error ?? "Failed to start the solver.");
    }
    setManualSolveLoading(false);
  };

  const currentSummary = schedule
    ? `Jobs: ${stats?.jobs ?? "-"} | Machines: ${stats?.machines ?? "-"} | Ops: ${stats?.operations ?? "-"}`
    : "No schedule JSON yet—generate one via chat.";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>Problem Builder</h1>
        <p style={{ color: "#4b5563", margin: "6px 0 0" }}>
          Describe the problem → let the LLM create/update the schedule JSON → review the diff → accept or reject.
        </p>
      </div>

      <div>
        <button
          type="button"
          onClick={() => setShowGuidance((val) => !val)}
          style={{
            border: "1px solid #2563eb",
            borderRadius: "999px",
            padding: "6px 16px",
            background: "transparent",
            color: "#2563eb",
            cursor: "pointer",
            fontWeight: 600
          }}
        >
          {showGuidance ? "Hide tips" : "Show tips"}
        </button>
      </div>
      {showGuidance && (
        <div style={{ ...cardStyle, minHeight: "auto", padding: "16px", gap: "12px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
            <div style={{ background: "#f3f4f6", borderRadius: "10px", padding: "12px" }}>
              <div style={{ fontWeight: 600, marginBottom: "6px" }}>How to describe the initial problem</div>
              <ul style={{ margin: 0, paddingInlineStart: "18px", color: "#4b5563", fontSize: "0.9rem" }}>
                <li>State the number of jobs and machines plus what they represent.</li>
                <li>List each job's operations and available machines in order.</li>
                <li>Provide processing times (minutes/seconds are fine); more detail is better.</li>
              </ul>
            </div>
            <div style={{ background: "#f3f4f6", borderRadius: "10px", padding: "12px" }}>
              <div style={{ fontWeight: 600, marginBottom: "6px" }}>How to request changes</div>
              <ul style={{ margin: 0, paddingInlineStart: "18px", color: "#4b5563", fontSize: "0.9rem" }}>
                <li>Adjust processing time: “Change Job 1's second operation to 20 minutes.”</li>
                <li>Add or remove jobs/operations and describe the dependencies.</li>
                <li>Limit machines: e.g., “Operation A can only run on M1 or M2.”</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", gap: "16px" }}>
        <div style={{ color: "#1f2937", fontWeight: 600 }}>{currentSummary}</div>
        <button
          type="button"
          onClick={resetConversation}
          style={{
            background: "transparent",
            border: "1px solid #d1d5db",
            borderRadius: "8px",
            padding: "8px 16px",
            cursor: "pointer"
          }}
        >
          Reset conversation
        </button>
      </div>

      <div style={pageStyle}>
        <section style={{ ...cardStyle, minHeight: "640px" }}>
          <div style={chatContainerStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Conversation</h2>
              {isSending && <span style={{ color: "#6b7280", fontSize: "0.9rem" }}>Calling the LLM…</span>}
            </div>
            <div style={toggleRowStyle}>
              <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <input
                  type="checkbox"
                  checked={autoApply}
                  onChange={(evt) => updateSettings({ autoApply: evt.target.checked })}
                />
                Auto apply changes
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <input
                  type="checkbox"
                  checked={autoSolve}
                  onChange={(evt) => updateSettings({ autoSolve: evt.target.checked })}
                />
                Auto solve (requires Solver Hub setup)
              </label>
            </div>
            <div style={messagesStyle}>
              {messages.length === 0 && (
                <div style={{ color: "#6b7280" }}>No messages yet—describe your FJSP problem to get started.</div>
              )}
              {messages.map((message, idx) => (
                <div
                  key={`${message.role}-${idx}`}
                  style={{
                    alignSelf: message.role === "user" ? "flex-end" : "flex-start",
                    backgroundColor: message.role === "assistant" ? "#eef2ff" : "#dcfce7",
                    borderRadius: "10px",
                    padding: "12px",
                    maxWidth: "75%"
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: "6px" }}>
                    {message.role === "assistant" ? "Assistant" : "You"}
                  </div>
                  <div style={{ whiteSpace: "pre-wrap", color: "#111827" }}>{message.content}</div>
                </div>
              ))}
              {pendingSchedule && (
                <div
                  style={{
                    alignSelf: "stretch",
                    backgroundColor: "#eef2ff",
                    borderRadius: "12px",
                    padding: "16px",
                    maxWidth: "100%",
                    width: "100%",
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                    border: "1px solid #c7d2fe"
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: "1rem", color: "#1e3a8a" }}>Change Review</div>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      onClick={() => setActiveDiffTab("table")}
                      style={{
                        border: "1px solid #d1d5db",
                        borderRadius: "6px",
                        padding: "6px 12px",
                        backgroundColor: activeDiffTab === "table" ? "#e0e7ff" : "transparent",
                        cursor: "pointer"
                      }}
                    >
                      Table Diff
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveDiffTab("json")}
                      style={{
                        border: "1px solid #d1d5db",
                        borderRadius: "6px",
                        padding: "6px 12px",
                        backgroundColor: activeDiffTab === "json" ? "#e0e7ff" : "transparent",
                        cursor: "pointer"
                      }}
                    >
                      JSON Diff
                    </button>
                  </div>
                  <div style={{ fontWeight: 600 }}>
                    Proposed Jobs: {pendingSchedule.J ?? pendingSchedule.instances?.length ?? "-"}
                  </div>
                  <div style={{ fontWeight: 600 }}>Machines: {pendingSchedule.M ?? "-"}</div>
                  {activeDiffTab === "json" ? (
                    <div
                      style={{
                        backgroundColor: "#0f172a",
                        color: "#e5e7eb",
                        borderRadius: "8px",
                        padding: "12px",
                        maxHeight: "240px",
                        overflowY: "auto",
                        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono"
                      }}
                    >
                      {diffLoading ? "Generating diff..." : diffText || "No diff summary available."}
                    </div>
                  ) : (
                    <div style={{ maxHeight: "240px", overflowY: "auto" }}>
                      {tableDiffLoading && <div style={{ color: "#6b7280" }}>Generating table diff…</div>}
                      {tableDiffError && <div style={{ color: "#dc2626" }}>{tableDiffError}</div>}
                      {!tableDiffLoading && !tableDiffError && (tableDiff?.length ?? 0) === 0 && (
                        <div style={{ color: "#6b7280" }}>No differences in the table.</div>
                      )}
                  {tableDiff?.map((change, changeIdx) => {
                    const currentRows = change.current_rows ?? [];
                    const proposedRows = change.proposed_rows ?? [];
                    const beforeMap = new Map<string, Record<string, unknown>>();
                    const afterMap = new Map<string, Record<string, unknown>>();

                    currentRows.forEach((row, idx) => {
                      beforeMap.set(getRowKey(row, idx), row);
                    });
                    proposedRows.forEach((row, idx) => {
                      afterMap.set(getRowKey(row, idx), row);
                    });

                    const rowKeys = new Set<string>([
                      ...beforeMap.keys(),
                      ...afterMap.keys()
                    ]);

                    const draftRowDiffs: RowDiffEntry[] = Array.from(rowKeys).map((rowKey) => {
                      const before = beforeMap.get(rowKey);
                      const after = afterMap.get(rowKey);
                      const changedColumns = new Set<string>();
                      const candidateColumns = new Set<string>();
                      if (before) {
                        Object.keys(before).forEach((col) => candidateColumns.add(col));
                      }
                      if (after) {
                        Object.keys(after).forEach((col) => candidateColumns.add(col));
                      }
                      candidateColumns.forEach((col) => {
                        if (!before || !after) return;
                        if (!isValueEqual(before[col], after[col])) {
                          changedColumns.add(col);
                        }
                      });
                      let status: RowDiffStatus;
                      if (before && !after) {
                        status = "removed";
                      } else if (!before && after) {
                        status = "added";
                      } else if (changedColumns.size > 0) {
                        status = "modified";
                      } else {
                        status = "unchanged";
                      }
                      return {
                        key: rowKey,
                        before,
                        after,
                        changedColumns,
                        status
                      };
                    });

                    const rowDiffs = draftRowDiffs.filter((entry) => entry.status !== "unchanged");
                    if (rowDiffs.length === 0) {
                      return (
                        <div key={`${change.job_id}-${changeIdx}`} style={{ color: "#6b7280" }}>
                          No row-level changes detected for Job {change.job_id}.
                        </div>
                      );
                    }

                    const columnSet = new Set<string>();
                    rowDiffs.forEach((entry) => {
                      entry.before &&
                        Object.keys(entry.before).forEach((col) => columnSet.add(col));
                      entry.after &&
                        Object.keys(entry.after).forEach((col) => columnSet.add(col));
                    });
                    const columns = sortColumns(Array.from(columnSet));

                    const beforeEntries = rowDiffs.filter((entry) => entry.before);
                    const afterEntries = rowDiffs.filter((entry) => entry.after);

                    const renderTable = (
                      entries: RowDiffEntry[],
                      label: string,
                      variant: "before" | "after"
                    ) => (
                      <div
                        style={{
                          border: "1px solid #e5e7eb",
                          borderRadius: "8px",
                          padding: "8px",
                          background: "#f9fafb"
                        }}
                      >
                        <div style={{ fontWeight: 600, marginBottom: "6px" }}>{label}</div>
                        {entries.length === 0 ? (
                          <div style={{ color: "#6b7280" }}>No rows.</div>
                        ) : (
                          <div style={{ overflowX: "auto" }}>
                            <table style={{ width: "100%", borderCollapse: "collapse" }}>
                              <thead>
                                <tr>
                                  {columns.map((col) => (
                                    <th
                                      key={`${label}-${col}`}
                                      style={{
                                        textAlign: "left",
                                        borderBottom: "1px solid #e5e7eb",
                                        padding: "4px",
                                        fontSize: "0.8rem",
                                        color: "#4b5563"
                                      }}
                                    >
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {entries.map((entry) => {
                                  const rowData = variant === "before" ? entry.before : entry.after;
                                  if (!rowData) return null;
                                  const rowStatus =
                                    variant === "before" && entry.status === "added"
                                      ? "unchanged"
                                      : variant === "after" && entry.status === "removed"
                                        ? "unchanged"
                                        : entry.status;
                                  const colors = ROW_COLORS[rowStatus];
                                  return (
                                    <tr
                                      key={`${entry.key}-${label}`}
                                      style={{
                                        backgroundColor: colors.background,
                                        borderLeft: `4px solid ${colors.border}`
                                      }}
                                    >
                                      {columns.map((col) => {
                                        const cellChanged =
                                          entry.status === "modified" && entry.changedColumns.has(col);
                                        return (
                                          <td
                                            key={`${entry.key}-${label}-${col}`}
                                            style={{
                                              borderBottom: "1px solid #f3f4f6",
                                              padding: "4px",
                                              fontSize: "0.8rem",
                                              backgroundColor: cellChanged ? CHANGED_CELL_COLOR : "transparent"
                                            }}
                                          >
                                            {formatCellValue(rowData[col])}
                                          </td>
                                        );
                                      })}
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    );

                    return (
                      <div
                        key={`${change.job_id}-${changeIdx}`}
                        style={{
                          border: "1px solid #e5e7eb",
                          borderRadius: "8px",
                          padding: "10px",
                          marginBottom: "10px",
                          background: "#fff",
                          display: "flex",
                          flexDirection: "column",
                          gap: "10px"
                        }}
                      >
                        <div style={{ fontWeight: 600, color: "#111827" }}>
                          Job {change.job_id}
                          {change.job_name ? ` — ${change.job_name}` : ""}
                        </div>
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                            gap: "12px"
                          }}
                        >
                          {renderTable(beforeEntries, "Before", "before")}
                          {renderTable(afterEntries, "After", "after")}
                        </div>
                      </div>
                    );
                  })}
                    </div>
                  )}
                  <div style={{ display: "flex", gap: "12px" }}>
                    <button
                      type="button"
                      onClick={handleAccept}
                      style={{
                        flex: 1,
                        border: "none",
                        borderRadius: "8px",
                        padding: "12px",
                        backgroundColor: "#16a34a",
                        color: "#fff",
                        fontWeight: 600,
                        cursor: "pointer"
                      }}
                    >
                      Accept changes
                    </button>
                    <button
                      type="button"
                      onClick={handleReject}
                      style={{
                        flex: 1,
                        border: "1px solid #d1d5db",
                        borderRadius: "8px",
                        padding: "12px",
                        backgroundColor: "transparent",
                        cursor: "pointer"
                      }}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}
              {showManualSolvePrompt && (
                <div
                  style={{
                    alignSelf: "flex-start",
                    backgroundColor: "#ecfccb",
                    borderRadius: "12px",
                    padding: "16px",
                    maxWidth: "85%",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                    border: "1px solid #bbf7d0"
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: "1rem", color: "#166534" }}>Ready to solve?</div>
                  <div style={{ color: "#1f2937" }}>
                    Auto Solve is off. Kick off a Solver Hub run for the current schedule with one click.
                  </div>
                  <button
                    type="button"
                    onClick={handleManualSolve}
                    disabled={manualSolveLoading}
                    style={{
                      border: "none",
                      borderRadius: "8px",
                      padding: "10px 18px",
                      backgroundColor: manualSolveLoading ? "#9ca3af" : "#16a34a",
                      color: "#fff",
                      fontWeight: 600,
                      cursor: manualSolveLoading ? "not-allowed" : "pointer",
                      alignSelf: "flex-start"
                    }}
                  >
                    {manualSolveLoading ? "Starting…" : "Solve this schedule"}
                  </button>
                  {manualSolveError && <div style={{ color: "#dc2626" }}>{manualSolveError}</div>}
                </div>
              )}
            </div>
            <form onSubmit={handleSend} style={chatInputStyle}>
              <textarea
                placeholder="Describe new constraints, resources, or edits…"
                value={input}
                onChange={(evt) => setInput(evt.target.value)}
                style={{
                  flex: 1,
                  borderRadius: "8px",
                  border: "1px solid #d1d5db",
                  padding: "12px",
                  minHeight: "72px",
                  resize: "vertical"
                }}
              />
              <button
                type="submit"
                disabled={isSending}
                style={{
                  width: "120px",
                  borderRadius: "8px",
                  border: "none",
                  backgroundColor: isSending ? "#9ca3af" : "#2563eb",
                  color: "#fff",
                  fontWeight: 600,
                  cursor: isSending ? "not-allowed" : "pointer"
                }}
              >
                Send
              </button>
            </form>
            {error && <div style={{ color: "#dc2626" }}>{error}</div>}
          </div>
        </section>
      </div>

      {showAutoSolveCard && (
        <section style={{ ...cardStyle, minHeight: "320px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Auto Solve Results</h2>
            {statusBadge(autoSolveRecord?.status)}
          </div>
          {autoSolveRecord ? (
            <>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <div style={{ color: "#1f2937", fontWeight: 600 }}>Run ID: {autoSolveRecord.run_id}</div>
                <div>Algorithm: {autoSolveRecord.algorithm.toUpperCase()}</div>
                <div>Status: {statusBadge(autoSolveRecord.status)}</div>
                <div>Created: {new Date(autoSolveRecord.created_at).toLocaleString()}</div>
              </div>
              {autoSolveRecord.results ? (
                <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                  <div>Best: {autoSolveRecord.results.summary.best}</div>
                  <div>Average: {autoSolveRecord.results.summary.average}</div>
                  <div>Worst: {autoSolveRecord.results.summary.worst}</div>
                </div>
              ) : (
                <div style={{ color: "#6b7280" }}>Waiting for solver output…</div>
              )}
              {artifactRuns.length ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {artifactRuns.map((run, idx) => {
                    const runNumber = (run.run_number ?? run["run_number"] ?? idx + 1) as number;
                    const makespan = (run.makespan ?? run["makespan"]) as number | undefined;
                    const poolPath = (run.pool_csv ?? run["pool_csv"]) as string | undefined;
                    const rawGantt = (run.gantt_generated ??
                      run["gantt_generated"] ??
                      run.gantt_file ??
                      run["gantt_file"]) as string | undefined;
                    const ganttPath = rawGantt || undefined;
                    return (
                      <div
                        key={`auto-artifact-${runNumber}-${idx}`}
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
                            alt={`Auto solve run ${runNumber} gantt chart`}
                            style={{
                              width: "100%",
                              borderRadius: "8px",
                              border: "1px solid #e5e7eb",
                              marginTop: "6px"
                            }}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ color: "#6b7280" }}>
                  Solver artifacts (CSV and Gantt preview) will appear here when the run finishes.
                </div>
              )}
            </>
          ) : (
            <div style={{ color: "#6b7280" }}>
              {autoSolve
                ? "Accept a proposed change to trigger Auto Solve. Results will show here."
                : "Turn on Auto Solve to run PPO and preview the generated Gantt chart here."}
            </div>
          )}
        </section>
      )}
    </div>
  );
};

export default ProblemBuilderPage;
