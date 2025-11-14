import type { CSSProperties } from "react";
import { useEffect, useState } from "react";

import { listGanttCharts, listModelWeights, listSolutionPools } from "../api/assets";
import {
  buildAssetFileUrl,
  downloadAssetFile,
  fetchAssetPreview,
  isImageLike,
  isTextPreviewable
} from "../utils/assetActions";

interface AssetItem {
  name: string;
  path: string;
}

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
  gap: "12px"
};

const listStyle: CSSProperties = {
  listStyle: "none",
  padding: 0,
  margin: 0,
  display: "flex",
  flexDirection: "column",
  gap: "8px"
};

const AssetsPage = () => {
  const [pools, setPools] = useState<AssetItem[]>([]);
  const [charts, setCharts] = useState<AssetItem[]>([]);
  const [models, setModels] = useState<AssetItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{
    name: string;
    content?: string;
    truncated?: boolean;
    imageUrl?: string;
  } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadAssets() {
      setLoading(true);
      setError(null);
      try {
        const [poolData, chartData, modelData] = await Promise.all([
          listSolutionPools(),
          listGanttCharts(),
          listModelWeights()
        ]);
        if (!cancelled) {
          setPools(poolData);
          setCharts(chartData);
          setModels(modelData);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Unable to fetch assets.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    loadAssets();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleCopyPath = async (path: string) => {
    if (navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(path);
        alert("Path copied. You can paste it directly into a terminal or Finder.");
        return;
      } catch {
        /* ignore */
      }
    }
    window.prompt("Copy path:", path);
  };

  const handleDownload = async (item: AssetItem) => {
    try {
      await downloadAssetFile(item.path, item.name);
      setPreviewError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to download this file.";
      setPreviewError(message);
    }
  };

  const handlePreview = async (item: AssetItem) => {
    setPreviewError(null);
    if (isImageLike(item.path)) {
      setPreview({ name: item.name, imageUrl: buildAssetFileUrl(item.path) });
      return;
    }
    if (!isTextPreviewable(item.path)) {
      setPreviewError("This file type cannot be previewed online. Please download it directly.");
      return;
    }
    setPreview({ name: item.name });
    setPreviewLoading(true);
    try {
      const data = await fetchAssetPreview(item.path);
      setPreview({ name: item.name, content: data.content, truncated: data.truncated });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to preview this file.";
      setPreviewError(message);
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const renderList = (items: AssetItem[], options?: { kind?: "gantt" }) => {
    if (items.length === 0) {
      return <div style={{ color: "#6b7280" }}>No data yet.</div>;
    }
    return (
      <ul style={listStyle}>
        {items.map((item) => {
          const previewable = isTextPreviewable(item.path) || isImageLike(item.path);
          return (
            <li
              key={item.path}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                padding: "10px 12px"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontWeight: 600 }}>{item.name}</span>
                  <span style={{ color: "#6b7280", fontSize: "0.85rem" }}>{item.path}</span>
                </div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={() => handlePreview(item)}
                    disabled={!previewable}
                    style={{
                      border: "1px solid #d1d5db",
                      borderRadius: "6px",
                      padding: "6px 10px",
                      backgroundColor: previewable ? "transparent" : "#f3f4f6",
                      color: previewable ? "inherit" : "#9ca3af",
                      cursor: previewable ? "pointer" : "not-allowed"
                    }}
                  >
                    Preview
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload(item)}
                    style={{
                      border: "1px solid #d1d5db",
                      borderRadius: "6px",
                      padding: "6px 10px",
                      backgroundColor: "transparent",
                      cursor: "pointer"
                    }}
                  >
                    Download
                  </button>
                  <button
                    type="button"
                    onClick={() => handleCopyPath(item.path)}
                    style={{
                      border: "1px solid #d1d5db",
                      borderRadius: "6px",
                      padding: "6px 10px",
                      backgroundColor: "transparent",
                      cursor: "pointer"
                    }}
                  >
                    Copy Path
                  </button>
                </div>
              </div>
              {options?.kind === "gantt" && (
                <img
                  src={buildAssetFileUrl(item.path)}
                  alt={item.name}
                  style={{ width: "100%", borderRadius: "6px", border: "1px solid #e5e7eb" }}
                />
              )}
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <div style={containerStyle}>
      <div>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>Assets</h1>
        <p style={{ color: "#4b5563", margin: "6px 0 0" }}>
          Browse solver output CSVs, historical Gantt charts, and PPO model weight directories.
        </p>
      </div>

      {error && <div style={{ color: "#dc2626" }}>{error}</div>}
      {previewError && <div style={{ color: "#dc2626" }}>{previewError}</div>}
      {loading && <div style={{ color: "#6b7280" }}>Loading…</div>}

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Solution Pools ({pools.length})</h2>
        {renderList(pools)}
      </section>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Gantt Charts ({charts.length})</h2>
        {renderList(charts, { kind: "gantt" })}
      </section>

      <section style={cardStyle}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>PPO Model Repositories ({models.length})</h2>
        {renderList(models)}
      </section>

      {preview && (
        <section style={cardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Preview: {preview.name}</h2>
            <button
              type="button"
              onClick={() => {
                setPreview(null);
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
          ) : preview.imageUrl ? (
            <img
              src={preview.imageUrl}
              alt={preview.name}
              style={{ width: "100%", borderRadius: "8px", border: "1px solid #e5e7eb" }}
            />
          ) : (
            <pre
              style={{
                backgroundColor: "#0f172a",
                color: "#e5e7eb",
                borderRadius: "8px",
                padding: "12px",
                maxHeight: "320px",
                overflowY: "auto"
              }}
            >
              {preview.content}
            </pre>
          )}
          {preview?.truncated && (
            <span style={{ color: "#6b7280", fontSize: "0.85rem" }}>
              Showing only the first 20KB. Download to view the full file.
            </span>
          )}
        </section>
      )}
    </div>
  );
};

export default AssetsPage;
