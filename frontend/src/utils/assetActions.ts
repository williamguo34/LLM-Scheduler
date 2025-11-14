import client from "../api/client";

export interface AssetPreviewPayload {
  path: string;
  content: string;
  truncated: boolean;
  mime_type?: string;
}

const TEXT_EXTENSIONS = new Set([".json", ".csv", ".txt", ".log", ".md"]);
const IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".gif"]); // png handles gantt previews

const getExtension = (path: string): string => {
  const match = /\.([^.\\/]+)$/.exec(path.toLowerCase());
  return match ? `.${match[1]}` : "";
};

export const isTextPreviewable = (path: string): boolean => TEXT_EXTENSIONS.has(getExtension(path));

export const isImageLike = (path: string): boolean => IMAGE_EXTENSIONS.has(getExtension(path));

const buildBaseUrl = (): string => {
  const base = client.defaults.baseURL || "/api";
  return base.endsWith("/") ? base.slice(0, -1) : base;
};

export const buildAssetFileUrl = (path: string): string =>
  `${buildBaseUrl()}/assets/file?path=${encodeURIComponent(path)}`;

export async function fetchAssetPreview(path: string): Promise<AssetPreviewPayload> {
  const { data } = await client.get("/assets/preview", { params: { path } });
  return data as AssetPreviewPayload;
}

export async function downloadAssetFile(path: string, filename?: string): Promise<void> {
  const response = await client.get<Blob>("/assets/file", {
    params: { path },
    responseType: "blob"
  });
  const blobUrl = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename ?? path.split(/[/\\]/).pop() ?? "asset";
  link.click();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 500);
}
