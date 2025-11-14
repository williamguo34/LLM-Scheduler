import type { CSSProperties } from "react";

import { useSettingsStore } from "../store/useSettingsStore";

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

const inputStyle: CSSProperties = {
  borderRadius: "8px",
  border: "1px solid #d1d5db",
  padding: "10px"
};

const SettingsPage = () => {
  const {
    apiBaseUrl,
    modelName,
    apiKey,
    baseUrl,
    modelWeightsDir,
    ppoRuns,
    autoApply,
    autoSolve,
    updateSettings
  } = useSettingsStore();

  return (
    <div style={containerStyle}>
      <div>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>Settings</h1>
        <p style={{ color: "#4b5563", margin: "6px 0 0" }}>
          Configure the API gateway, LLM credentials, and default Solver/Builder behavior.
        </p>
      </div>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>API Gateway</h2>
        <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span>Backend Base URL</span>
          <input
            type="text"
            value={apiBaseUrl}
            onChange={(evt) => updateSettings({ apiBaseUrl: evt.target.value })}
            style={inputStyle}
            placeholder="e.g., http://127.0.0.1:8000/api"
          />
        </label>
        <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
          All axios requests will use the updated address.
        </p>
      </section>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>LLM</h2>
        <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
          <button
            onClick={() =>
              updateSettings({
                modelName: "Pro/deepseek-ai/DeepSeek-V3.2-Exp",
                apiKey: "sk-zhmjtdpqtkpsddfccwwbhkbikyhvtyxlcqwbqwtoivcsnebg",
                baseUrl: "https://api.siliconflow.cn/v1"
              })
            }
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              border: "1px solid #3b82f6",
              backgroundColor: "#3b82f6",
              color: "white",
              cursor: "pointer",
              fontSize: "0.9rem"
            }}
          >
            🔵 DeepSeek-V3.2-Exp
          </button>
          <button
            onClick={() =>
              updateSettings({
                modelName: "gpt-4o",
                apiKey: "",
                baseUrl: "https://models.inference.ai.azure.com"
              })
            }
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              border: "1px solid #10b981",
              backgroundColor: "#10b981",
              color: "white",
              cursor: "pointer",
              fontSize: "0.9rem"
            }}
          >
            🟢 OpenAI (Default)
          </button>
          <button
            onClick={() =>
              updateSettings({
                modelName: "",
                apiKey: "",
                baseUrl: ""
              })
            }
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              border: "1px solid #6b7280",
              backgroundColor: "transparent",
              color: "#6b7280",
              cursor: "pointer",
              fontSize: "0.9rem"
            }}
          >
            🔄 Clear All
          </button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span>Model Name</span>
            <input
              type="text"
              value={modelName}
              onChange={(evt) => updateSettings({ modelName: evt.target.value })}
              style={inputStyle}
              placeholder="gpt-4o, llama3.1, etc."
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span>API Key</span>
            <input
              type="password"
              value={apiKey}
              onChange={(evt) => updateSettings({ apiKey: evt.target.value })}
              style={inputStyle}
              placeholder="sk-..."
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span>Base URL</span>
            <input
              type="text"
              value={baseUrl}
              onChange={(evt) => updateSettings({ baseUrl: evt.target.value })}
              style={inputStyle}
              placeholder="https://models.inference.ai.azure.com"
            />
          </label>
        </div>
        <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
          These values are automatically injected into Problem Builder LLM requests.
        </p>
      </section>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Solver Defaults</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span>MODEL_WEIGHTS_DIR</span>
            <input
              type="text"
              value={modelWeightsDir}
              onChange={(evt) => updateSettings({ modelWeightsDir: evt.target.value })}
              style={inputStyle}
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span>PPO Runs</span>
            <input
              type="number"
              min={1}
              max={10}
              value={ppoRuns}
              onChange={(evt) => updateSettings({ ppoRuns: Number(evt.target.value) })}
              style={inputStyle}
            />
          </label>
        </div>
      </section>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>UI Preferences</h2>
        <label style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <input
            type="checkbox"
            checked={autoApply}
            onChange={(evt) => updateSettings({ autoApply: evt.target.checked })}
          />
          Automatically apply Problem Builder changes
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <input
            type="checkbox"
            checked={autoSolve}
            onChange={(evt) => updateSettings({ autoSolve: evt.target.checked })}
          />
          Automatically trigger the Solver (experimental)
        </label>
      </section>
    </div>
  );
};

export default SettingsPage;
