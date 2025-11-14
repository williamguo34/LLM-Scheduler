import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { checkDeadlines, checkPrecedence } from "../api/constraints";
import { useAppStore } from "../store/useAppStore";
import { downloadAssetFile, fetchAssetPreview, isTextPreviewable } from "../utils/assetActions";

const containerStyle: CSSProperties = {
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

const tableStyle: CSSProperties = {
  borderCollapse: "collapse",
  width: "100%"
};

const ConstraintsPage = () => {
  const { solverRuns, schedule } = useAppStore();
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [deadlineInput, setDeadlineInput] = useState("100, 120, 150");
  const [deadlineResult, setDeadlineResult] = useState<{
    deadlines_path: string;
    pool_path: string;
    valid_solutions: number;
  } | null>(null);
  const [parsedDeadlines, setParsedDeadlines] = useState<number[]>([]);
  const [deadlineLoading, setDeadlineLoading] = useState(false);
  const [deadlineError, setDeadlineError] = useState<string | null>(null);

  const [precedenceMatrix, setPrecedenceMatrix] = useState<number[][] | null>(null);
  const [precedencePath, setPrecedencePath] = useState<string | null>(null);
  const [precedenceLoading, setPrecedenceLoading] = useState(false);
  const [precedenceError, setPrecedenceError] = useState<string | null>(null);
  const [previewPayload, setPreviewPayload] = useState<{ title: string; content: string; truncated: boolean } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedRunId && solverRuns.length > 0) {
      setSelectedRunId(solverRuns[0].run_id);
    }
  }, [solverRuns, selectedRunId]);

  const selectedRun = useMemo(
    () => solverRuns.find((run) => run.run_id === selectedRunId),
    [solverRuns, selectedRunId]
  );

  const handleDeadlineSubmit = async (evt: FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    if (!selectedRunId) {
      setDeadlineError("Please select a solver run.");
      return;
    }
    setDeadlineError(null);
    setDeadlineLoading(true);
    setDeadlineResult(null);
    try {
      const numbers = deadlineInput
        .split(",")
        .map((token) => token.trim())
        .filter(Boolean)
        .map((token) => Number(token));
      if (numbers.some((n) => Number.isNaN(n))) {
        throw new Error("Enter valid numbers separated by commas.");
      }
      setParsedDeadlines(numbers);
      const result = await checkDeadlines(selectedRunId, numbers);
      setDeadlineResult(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Deadline verification failed.";
      setDeadlineError(message);
    } finally {
      setDeadlineLoading(false);
    }
  };

  const handlePrecedence = async () => {
    if (!schedule) {
      setPrecedenceError("No schedule JSON is available.");
      return;
    }
    setPrecedenceLoading(true);
    setPrecedenceError(null);
    try {
      const result = await checkPrecedence(schedule);
      setPrecedenceMatrix(result.precedence_matrix ?? null);
      setPrecedencePath(result.precedence_path ?? null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to extract the precedence matrix.";
      setPrecedenceError(message);
    } finally {
      setPrecedenceLoading(false);
    }
  };

  const handleDownloadAsset = async (path?: string | null, fallbackName?: string) => {
    if (!path) return;
    try {
      await downloadAssetFile(path, fallbackName);
      setPreviewError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to download this file.";
      setPreviewError(message);
    }
  };

  const handlePreviewAsset = async (path?: string | null, title?: string) => {
    if (!path) return;
    if (!isTextPreviewable(path)) {
      setPreviewError("This file type cannot be previewed online. Please download it instead.");
      return;
    }
    setPreviewPayload({ title: title ?? path, content: "", truncated: false });
    setPreviewLoading(true);
    try {
      const data = await fetchAssetPreview(path);
      setPreviewPayload({ title: title ?? data.path, content: data.content, truncated: data.truncated });
      setPreviewError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load the preview.";
      setPreviewError(message);
      setPreviewPayload(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div style={containerStyle}>
      <div>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>Constraints & Health</h1>
        <p style={{ color: "#4b5563", margin: "6px 0 0" }}>
          Use the API to validate solver results against deadlines and extract cross-job precedence matrices.
        </p>
      </div>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Deadline Check</h2>
        {solverRuns.length === 0 ? (
          <div style={{ color: "#6b7280" }}>Run the solver at least once before checking deadlines.</div>
        ) : (
          <>
            <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span>Select a Solver Run</span>
              <select
                value={selectedRunId}
                onChange={(evt) => setSelectedRunId(evt.target.value)}
                style={{
                  borderRadius: "8px",
                  border: "1px solid #d1d5db",
                  padding: "10px"
                }}
              >
                <option value="">Pick a run</option>
                {solverRuns.map((run) => (
                  <option key={run.run_id} value={run.run_id}>
                    {run.run_id} | {run.algorithm} | {run.status}
                  </option>
                ))}
              </select>
            </label>
            <form onSubmit={handleDeadlineSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <span>Deadlines (comma separated)</span>
                <input
                  type="text"
                  value={deadlineInput}
                  onChange={(evt) => setDeadlineInput(evt.target.value)}
                  style={{
                    borderRadius: "8px",
                    border: "1px solid #d1d5db",
                    padding: "10px"
                  }}
                />
              </label>
              <button
                type="submit"
                disabled={deadlineLoading}
                style={{
                  alignSelf: "flex-start",
                  border: "none",
                  borderRadius: "8px",
                  padding: "10px 20px",
                  backgroundColor: "#2563eb",
                  color: "#fff",
                  fontWeight: 600,
                  cursor: "pointer"
                }}
              >
                {deadlineLoading ? "Checking..." : "Check"}
              </button>
            </form>
            {deadlineError && <div style={{ color: "#dc2626" }}>{deadlineError}</div>}
            {deadlineResult && (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <div>
                  Valid Solutions:{" "}
                  <strong>
                    {deadlineResult.valid_solutions}
                    {selectedRun?.results?.runs ? ` / ${selectedRun.results.runs.length}` : ""}
                  </strong>
                </div>
                {parsedDeadlines.length > 0 && (
                  <div style={{ color: "#4b5563", fontSize: "0.9rem" }}>
                    Deadlines: {parsedDeadlines.join(", ")}
                  </div>
                )}
                <div>Deadlines Saved: {deadlineResult.deadlines_path}</div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={() => handleDownloadAsset(deadlineResult.deadlines_path, "deadlines.npy")}
                    style={{
                      border: "1px solid #d1d5db",
                      borderRadius: "6px",
                      padding: "6px 12px",
                      backgroundColor: "transparent",
                      cursor: deadlineResult.deadlines_path ? "pointer" : "not-allowed",
                      color: deadlineResult.deadlines_path ? "inherit" : "#9ca3af"
                    }}
                  >
                    Download Deadlines
                  </button>
                  {isTextPreviewable(deadlineResult.deadlines_path ?? "") && (
                    <button
                      type="button"
                      onClick={() => handlePreviewAsset(deadlineResult.deadlines_path, "Deadlines file")}
                      style={{
                        border: "1px solid #d1d5db",
                        borderRadius: "6px",
                        padding: "6px 12px",
                        backgroundColor: "transparent",
                        cursor: "pointer"
                      }}
                    >
                      Preview Deadlines
                    </button>
                  )}
                </div>
                <div>Report CSV: {deadlineResult.pool_path}</div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={() => handleDownloadAsset(deadlineResult.pool_path, "deadline_report.csv")}
                    style={{
                      border: "1px solid #d1d5db",
                      borderRadius: "6px",
                      padding: "6px 12px",
                      backgroundColor: "transparent",
                      cursor: deadlineResult.pool_path ? "pointer" : "not-allowed",
                      color: deadlineResult.pool_path ? "inherit" : "#9ca3af"
                    }}
                  >
                    Download CSV
                  </button>
                  {isTextPreviewable(deadlineResult.pool_path ?? "") && (
                    <button
                      type="button"
                      onClick={() => handlePreviewAsset(deadlineResult.pool_path, "Deadline report CSV")}
                      style={{
                        border: "1px solid #d1d5db",
                        borderRadius: "6px",
                        padding: "6px 12px",
                        backgroundColor: "transparent",
                        cursor: "pointer"
                      }}
                    >
                      Preview CSV
                    </button>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </section>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Precedence Extraction</h2>
        <p style={{ color: "#6b7280" }}>
          Use the current schedule JSON to compute job-to-job precedence matrices and export them as `.npy`.
        </p>
        <button
          type="button"
          onClick={handlePrecedence}
          disabled={precedenceLoading || !schedule}
          style={{
            alignSelf: "flex-start",
            border: "none",
            borderRadius: "8px",
            padding: "10px 20px",
            backgroundColor: schedule ? "#16a34a" : "#9ca3af",
            color: "#fff",
            fontWeight: 600,
            cursor: schedule ? "pointer" : "not-allowed"
          }}
        >
          {precedenceLoading ? "Extracting..." : "Extract matrix"}
        </button>
        {precedenceError && <div style={{ color: "#dc2626" }}>{precedenceError}</div>}
        {precedencePath && (
          <div style={{ color: "#4b5563", display: "flex", flexDirection: "column", gap: "6px" }}>
            <span>File output: {precedencePath}</span>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => handleDownloadAsset(precedencePath, "precedence_output")}
                style={{
                  border: "1px solid #d1d5db",
                  borderRadius: "6px",
                  padding: "6px 12px",
                  backgroundColor: "transparent",
                  cursor: "pointer"
                }}
              >
                Download Precedence
              </button>
              {isTextPreviewable(precedencePath) && (
                <button
                  type="button"
                  onClick={() => handlePreviewAsset(precedencePath, "Precedence file")}
                  style={{
                    border: "1px solid #d1d5db",
                    borderRadius: "6px",
                    padding: "6px 12px",
                    backgroundColor: "transparent",
                    cursor: "pointer"
                  }}
                >
                  Preview file
                </button>
              )}
            </div>
          </div>
        )}
        {precedenceMatrix ? (
          <>
            <div style={{ color: "#4b5563" }}>
              There are{" "}
              <strong>
                {precedenceMatrix.reduce(
                  (sum, row) => sum + row.reduce((acc, val) => acc + (val ? 1 : 0), 0),
                  0
                )}
              </strong>{" "}
              cross-job precedence constraints.
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={{ padding: "6px", borderBottom: "1px solid #e5e7eb" }} />
                    {precedenceMatrix.map((_, idx) => (
                      <th key={`col-${idx}`} style={{ padding: "6px", borderBottom: "1px solid #e5e7eb" }}>
                        Job {idx + 1}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {precedenceMatrix.map((row, rowIdx) => (
                    <tr key={`row-${rowIdx}`}>
                      <td style={{ padding: "6px", borderBottom: "1px solid #f3f4f6", fontWeight: 600 }}>
                        Job {rowIdx + 1}
                      </td>
                      {row.map((value, colIdx) => (
                        <td
                          key={`cell-${rowIdx}-${colIdx}`}
                          style={{
                            padding: "6px",
                            borderBottom: "1px solid #f3f4f6",
                            textAlign: "center",
                            backgroundColor: value ? "#dcfce7" : "transparent"
                          }}
                        >
                          {value}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div style={{ color: "#6b7280" }}>No matrix generated yet.</div>
        )}
      </section>

      {previewError && <div style={{ color: "#dc2626" }}>{previewError}</div>}

      {previewPayload && (
        <section style={cardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ margin: 0, fontSize: "1.1rem" }}>File Preview: {previewPayload.title}</h2>
            <button
              type="button"
              onClick={() => {
                setPreviewPayload(null);
                setPreviewError(null);
              }}
              style={{
                border: "1px solid #d1d5db",
                borderRadius: "6px",
                padding: "6px 12px",
                backgroundColor: "transparent",
                cursor: "pointer"
              }}
            >
              Close
            </button>
          </div>
          {previewLoading ? (
            <div style={{ color: "#6b7280" }}>Loading preview…</div>
          ) : (
            <pre
              style={{
                backgroundColor: "#0f172a",
                color: "#e5e7eb",
                borderRadius: "8px",
                padding: "12px",
                maxHeight: "260px",
                overflowY: "auto"
              }}
            >
              {previewPayload.content}
            </pre>
          )}
          {previewPayload.truncated && (
            <span style={{ color: "#6b7280", fontSize: "0.85rem" }}>
              Showing only the first 20KB. Download to see the full file.
            </span>
          )}
        </section>
      )}
    </div>
  );
};

export default ConstraintsPage;
