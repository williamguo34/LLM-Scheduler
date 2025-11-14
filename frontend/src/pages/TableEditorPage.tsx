import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";

import {
  transformScheduleToTables,
  transformTablesToSchedule,
  type JobTable
} from "../api/schedules";
import { useAppStore } from "../store/useAppStore";
import type { JobInstance } from "../types";

const pageStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "24px"
};

const cardStyle: CSSProperties = {
  backgroundColor: "#ffffff",
  borderRadius: "12px",
  padding: "24px",
  boxShadow: "0 8px 24px rgba(15, 23, 42, 0.08)"
};

const jobGridStyle: CSSProperties = {
  display: "grid",
  gap: "16px",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))"
};

const TableEditorPage = () => {
  const { schedule, setSchedule } = useAppStore();
  const [tables, setTables] = useState<JobTable[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadTables() {
      if (!schedule) {
        setTables([]);
        setError(null);
        return;
      }
      setIsLoading(true);
      setError(null);
      setSuccess(null);
      try {
        const result = await transformScheduleToTables(schedule);
        if (!cancelled) {
          setTables(result);
          setHasUnsavedChanges(false);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Unable to load table data.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }
    loadTables();
    return () => {
      cancelled = true;
    };
  }, [schedule]);

  const summary = useMemo(() => {
    if (!schedule) return null;
    const instances = (schedule.instances ?? []) as JobInstance[];
    const operations = instances.reduce(
      (total, job) => total + (job.operations?.length ?? 0),
      0
    );
    return { jobs: schedule.J ?? instances.length, machines: schedule.M ?? 0, operations };
  }, [schedule]);

  const formatValue = (value: unknown) => {
    if (Array.isArray(value)) {
      return value.join(", ");
    }
    if (value === undefined || value === null) return "";
    return String(value);
  };

  const coerceValue = (prev: unknown, nextRaw: string, key: string): unknown => {
    if (Array.isArray(prev) || key === "pre") {
      return nextRaw
        .split(",")
        .map((token) => token.trim())
        .filter(Boolean)
        .map((token) => {
          const num = Number(token);
          return Number.isNaN(num) ? token : num;
        });
    }
    if (typeof prev === "number") {
      const parsed = Number(nextRaw);
      return Number.isNaN(parsed) ? prev : parsed;
    }
    if (typeof prev === "boolean") {
      return nextRaw === "true";
    }
    return nextRaw;
  };

  const updateJobTable = (jobId: number, updater: (table: JobTable) => JobTable) => {
    setTables((prev) =>
      prev.map((table) => (table.job_id === jobId ? updater(table) : table))
    );
    setHasUnsavedChanges(true);
    setSuccess(null);
  };

  const handleCellChange = (jobId: number, rowIndex: number, key: string, rawValue: string) => {
    updateJobTable(jobId, (table) => {
      const rows = table.rows.map((row, idx) => {
        if (idx !== rowIndex) return row;
        const previous = row[key];
        return {
          ...row,
          [key]: coerceValue(previous, rawValue, key)
        };
      });
      return { ...table, rows };
    });
  };

  const handleJobNameChange = (jobId: number, value: string) => {
    updateJobTable(jobId, (table) => ({ ...table, job_name: value }));
  };

  const handleAddRow = (jobId: number) => {
    updateJobTable(jobId, (table) => ({
      ...table,
      rows: [
        ...table.rows,
        {
          op_id: `op_${table.rows.length + 1}`,
          op_n: "",
          re: "",
          pre: []
        }
      ]
    }));
  };

  const handleRemoveRow = (jobId: number, rowIndex: number) => {
    updateJobTable(jobId, (table) => ({
      ...table,
      rows: table.rows.filter((_, idx) => idx !== rowIndex)
    }));
  };

  const handleSave = async () => {
    if (!schedule) return;
    const validationError = validateTables();
    if (validationError) {
      setError(validationError);
      return;
    }
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await transformTablesToSchedule(tables, schedule);
      setSchedule(updated);
      setHasUnsavedChanges(false);
      setSuccess("✅ Manual edits saved.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Save failed.";
      setError(message);
    } finally {
      setIsSaving(false);
    }
  };

  const validateTables = () => {
    for (const job of tables) {
      if (job.rows.length === 0) {
        return `Job ${job.job_id} requires at least one operation.`;
      }
      const seen = new Set<string>();
      for (const row of job.rows) {
        const opId = row.op_id;
        if (!opId || String(opId).trim() === "") {
          return `Job ${job.job_id} has an empty op_id.`;
        }
        const key = String(opId).trim();
        if (seen.has(key)) {
          return `Job ${job.job_id} has a duplicate op_id=${key}.`;
        }
        seen.add(key);
      }
    }
    return null;
  };

  if (!schedule) {
    return (
      <div style={pageStyle}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>Table Editor</h1>
          <p style={{ color: "#4b5563", margin: "6px 0 0" }}>
            Generate or upload a schedule JSON in the Problem Builder first.
          </p>
        </div>
        <div style={cardStyle}>
          <p style={{ color: "#6b7280" }}>No schedule data for this session.</p>
        </div>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>Table Editor</h1>
          <p style={{ color: "#4b5563", margin: "6px 0 0" }}>
            Review each job and adjust the operation table manually.
          </p>
        </div>
        <div style={{ textAlign: "right", color: "#4b5563" }}>
          <div>Jobs: {summary?.jobs ?? "-"}</div>
          <div>Machines: {summary?.machines ?? "-"}</div>
          <div>Operations: {summary?.operations ?? "-"}</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: "12px" }}>
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving || !hasUnsavedChanges}
          style={{
            border: "none",
            borderRadius: "8px",
            padding: "12px 20px",
            backgroundColor: hasUnsavedChanges ? "#16a34a" : "#9ca3af",
            color: "#fff",
            fontWeight: 600,
            cursor: hasUnsavedChanges ? "pointer" : "not-allowed"
          }}
        >
          {isSaving ? "Saving..." : "Save manual edits"}
        </button>
      </div>

      {error && <div style={{ color: "#dc2626" }}>{error}</div>}
      {success && <div style={{ color: "#16a34a" }}>{success}</div>}
      {isLoading && <div style={{ color: "#6b7280" }}>Loading tables…</div>}

      <div style={jobGridStyle}>
        {tables.map((job) => {
          const columnSet = new Set<string>();
          job.rows.forEach((row) => {
            Object.keys(row).forEach((key) => columnSet.add(key));
          });
          const columns = Array.from(columnSet);
          if (columns.length === 0) {
            columns.push("op_id", "op_n", "re", "pre");
          }
          return (
            <div key={job.job_id} style={cardStyle}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>Job {job.job_id}</div>
                  <input
                    type="text"
                    value={job.job_name ?? ""}
                    onChange={(evt) => handleJobNameChange(job.job_id, evt.target.value)}
                    placeholder="Job name"
                    style={{
                      marginTop: "6px",
                      width: "100%",
                      borderRadius: "6px",
                      border: "1px solid #d1d5db",
                      padding: "6px 8px"
                    }}
                  />
                </div>
                <button
                  type="button"
                  onClick={() => handleAddRow(job.job_id)}
                  style={{
                    height: "36px",
                    alignSelf: "flex-start",
                    borderRadius: "6px",
                    border: "1px solid #d1d5db",
                    backgroundColor: "transparent",
                    cursor: "pointer"
                  }}
                >
                  + Operation
                </button>
              </div>

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {columns.map((col) => (
                        <th
                          key={col}
                          style={{
                            textAlign: "left",
                            borderBottom: "1px solid #e5e7eb",
                            paddingBottom: "6px",
                            fontSize: "0.85rem",
                            color: "#6b7280"
                          }}
                        >
                          {col}
                        </th>
                      ))}
                      <th style={{ width: "60px" }} />
                    </tr>
                  </thead>
                  <tbody>
                    {job.rows.map((row, rowIndex) => (
                      <tr key={`${job.job_id}-${rowIndex}`}>
                        {columns.map((col) => (
                          <td key={`${job.job_id}-${rowIndex}-${col}`} style={{ padding: "6px 4px" }}>
                            <input
                              type="text"
                              value={formatValue(row[col])}
                              onChange={(evt) =>
                                handleCellChange(job.job_id, rowIndex, col, evt.target.value)
                              }
                              style={{
                                width: "100%",
                                borderRadius: "4px",
                                border: "1px solid #d1d5db",
                                padding: "6px"
                              }}
                            />
                          </td>
                        ))}
                        <td>
                          <button
                            type="button"
                            onClick={() => handleRemoveRow(job.job_id, rowIndex)}
                            style={{
                              border: "none",
                              background: "transparent",
                              color: "#dc2626",
                              cursor: "pointer"
                            }}
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    ))}
                    {job.rows.length === 0 && (
                      <tr>
                        <td colSpan={columns.length + 1} style={{ padding: "12px", color: "#6b7280" }}>
                          No operations yet. Use the button above to add one.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TableEditorPage;
