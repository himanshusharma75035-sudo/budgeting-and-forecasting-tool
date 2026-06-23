// Typed fetch wrapper around the backend API (all routes under /api, proxied by Vite in dev).

const BASE = "/api";

async function parseError(res: Response): Promise<string> {
  let message = `${res.status} ${res.statusText}`;
  try {
    const data: unknown = await res.clone().json();
    if (data && typeof data === "object") {
      const obj = data as Record<string, unknown>;
      const detail = obj.detail ?? obj.message ?? obj.error;
      if (typeof detail === "string") {
        message = detail;
      } else if (detail != null) {
        message = JSON.stringify(detail);
      }
    }
  } catch {
    try {
      const text = await res.text();
      if (text) message = text;
    } catch {
      // keep status-based message
    }
  }
  return message;
}

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as T;
}

/** Parse the download filename out of a Content-Disposition header, if present. */
function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header);
  return match ? decodeURIComponent(match[1]) : null;
}

/** POST JSON and save the binary response as a file download (e.g. an .xlsx export). */
export async function downloadPost(
  path: string,
  body: unknown,
  fallbackFilename = "download",
): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  const blob = await res.blob();
  const filename = filenameFromDisposition(res.headers.get("Content-Disposition")) ?? fallbackFilename;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function uploadFile<T>(
  path: string,
  file: File,
  params: Record<string, string> = {},
): Promise<T> {
  const query = new URLSearchParams(params).toString();
  const url = `${BASE}${path}${query ? `?${query}` : ""}`;
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json" },
    body: form,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as T;
}
