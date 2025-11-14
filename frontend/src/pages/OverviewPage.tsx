import React, { useRef, useState } from "react";
import type { CSSProperties, ChangeEvent } from "react";

import { useAppStore } from "../store/useAppStore";
import { useSettingsStore } from "../store/useSettingsStore";
import type { ChatMessage, ScheduleJSON } from "../types";

const cardStyle: CSSProperties = {
  backgroundColor: "#ffffff",
  borderRadius: "12px",
  padding: "24px",
  boxShadow: "0 8px 24px rgba(15, 23, 42, 0.08)",
  display: "flex",
  flexDirection: "column",
  gap: "12px"
};

const gridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: "24px"
};

const sectionTitleStyle: CSSProperties = {
  fontSize: "1.125rem",
  fontWeight: 600,
  color: "#111827"
};

const OverviewPage = () => {
  const { schedule, pendingSchedule, messages, solverRuns, setSchedule, setPendingSchedule } = useAppStore();
  const { apiBaseUrl, modelName, autoApply, autoSolve } = useSettingsStore();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const latestSolverRun = solverRuns.length > 0 ? solverRuns[0] : undefined;

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setImportError(null);
    setImportSuccess(null);
  };

  const handleImport = async () => {
    if (!selectedFile) {
      setImportError("Please select a schedule.json file.");
      return;
    }
    try {
      const text = await selectedFile.text();
      const parsed = JSON.parse(text) as ScheduleJSON;
      if (!parsed || typeof parsed !== "object" || !parsed.instances) {
        throw new Error("Missing required field (instances).");
      }
      setSchedule(parsed);
      setPendingSchedule(null);
      setImportSuccess(`Imported ${selectedFile.name}`);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to parse file.";
      setImportError(`Unable to import: ${message}`);
      setImportSuccess(null);
    }
  };

  const handleExport = () => {
    if (!schedule) return;
    const blob = new Blob([JSON.stringify(schedule, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "schedule.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  };

  const activeInstances = schedule && Array.isArray(schedule.instances) ? schedule.instances : [];
  const pendingInstances =
    pendingSchedule && Array.isArray(pendingSchedule.instances) ? pendingSchedule.instances : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>Mission Control</h1>
          <p style={{ color: "#4b5563", margin: "6px 0 0" }}>
            Monitor schedules, conversations, and solver performance in one place.
          </p>
        </div>
      </div>

      <div style={gridStyle}>
        <div style={cardStyle}>
          <div style={sectionTitleStyle}>Active Schedule</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json"
              onChange={handleFileChange}
            />
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={handleImport}
                style={{
                  border: "none",
                  borderRadius: "6px",
                  padding: "8px 16px",
                  backgroundColor: "#2563eb",
                  color: "#fff",
                  fontWeight: 600,
                  cursor: "pointer"
                }}
              >
                Import JSON
              </button>
              <button
                type="button"
                onClick={handleExport}
                disabled={!schedule}
                style={{
                  border: "1px solid #d1d5db",
                  borderRadius: "6px",
                  padding: "8px 16px",
                  backgroundColor: "transparent",
                  color: schedule ? "#111827" : "#9ca3af",
                  cursor: schedule ? "pointer" : "not-allowed"
                }}
              >
                Export Current JSON
              </button>
            </div>
            {importError && <div style={{ color: "#dc2626" }}>{importError}</div>}
            {importSuccess && <div style={{ color: "#16a34a" }}>{importSuccess}</div>}
          </div>
          {schedule ? (
            <div>
              <div style={{ fontWeight: 600 }}>Jobs: {schedule.J ?? activeInstances.length}</div>
              <div style={{ fontWeight: 600 }}>Machines: {schedule.M ?? "-"}</div>
              <pre style={{ backgroundColor: "#f3f4f6", padding: "12px", borderRadius: "8px", margin: "16px 0 0" }}>
                {JSON.stringify(activeInstances.slice(0, 3), null, 2)}
              </pre>
              {activeInstances.length > 3 && (
                <div style={{ color: "#6b7280", fontSize: "0.875rem", marginTop: "8px" }}>
                  Showing first three jobs of {activeInstances.length}
                </div>
              )}
            </div>
          ) : (
            <div style={{ color: "#6b7280" }}>No schedule generated yet.</div>
          )}
        </div>

        <div style={cardStyle}>
          <div style={sectionTitleStyle}>Pending Updates</div>
          {pendingSchedule ? (
            <div>
              <div style={{ fontWeight: 600 }}>Ready to review</div>
              <pre style={{ backgroundColor: "#f3f4f6", padding: "12px", borderRadius: "8px", margin: "16px 0 0" }}>
                {JSON.stringify(pendingInstances.slice(0, 2), null, 2)}
              </pre>
            </div>
          ) : (
            <div style={{ color: "#6b7280" }}>No draft changes pending.</div>
          )}
        </div>

        <div style={cardStyle}>
          <div style={sectionTitleStyle}>Latest Solver Run</div>
          {latestSolverRun ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <div>Algorithm: <strong>{latestSolverRun.algorithm.toUpperCase()}</strong></div>
              <div>Status: <strong>{latestSolverRun.status}</strong></div>
              {latestSolverRun.results && (
                <div style={{ display: "flex", gap: "12px" }}>
                  <div>Best: {latestSolverRun.results.summary.best}</div>
                  <div>Average: {latestSolverRun.results.summary.average}</div>
                  <div>Worst: {latestSolverRun.results.summary.worst}</div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ color: "#6b7280" }}>Solver has not been executed yet.</div>
          )}
        </div>

        <div style={cardStyle}>
          <div style={sectionTitleStyle}>Integration Status</div>
          <div>API Base: {apiBaseUrl || "/api"}</div>
          <div>LLM Model: {modelName || "Not configured"}</div>
          <div>Auto Apply: {autoApply ? "ON" : "OFF"}</div>
          <div>Auto Solve: {autoSolve ? "ON" : "OFF"}</div>
        </div>
      </div>

      <div style={cardStyle}>
        <div style={sectionTitleStyle}>Conversation Log</div>
        {messages.length === 0 ? (
          <div style={{ color: "#6b7280" }}>No messages exchanged yet.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {messages.slice(-5).map((message: ChatMessage, index: number) => (
              <div key={`${message.role}-${index}`} style={{
                backgroundColor: message.role === "assistant" ? "#eef2ff" : "#ecfdf5",
                borderRadius: "8px",
                padding: "12px"
              }}>
                <div style={{ fontWeight: 600, marginBottom: "6px" }}>
                  {message.role === "assistant" ? "Assistant" : "You"}
                </div>
                <div style={{ whiteSpace: "pre-wrap", color: "#1f2937" }}>{message.content}</div>
              </div>
            ))}
            {messages.length > 5 && (
              <div style={{ color: "#6b7280", fontSize: "0.875rem" }}>
                Showing the last five messages.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default OverviewPage;
