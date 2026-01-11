/**
 * Centralized API helpers with base URL from env.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function getApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

/**
 * Fetch wrapper with abort signal support and JSON parsing.
 */
export async function apiFetch<T>(
  path: string,
  options?: RequestInit & { signal?: AbortSignal }
): Promise<T> {
  const url = getApiUrl(path);
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `API error: ${res.status} ${res.statusText}`
    );
  }

  return res.json();
}

/**
 * POST helper for /invoke endpoint.
 */
export type TimestampedTranscriptLine = { text: string; time: string };

export async function invokeTranscript(
  transcript: {
  text: string;
  time: string;
  location: string;
  duration: string;
  },
  timestamped_transcript?: TimestampedTranscriptLine[]
): Promise<unknown> {
  return apiFetch("/invoke", {
    method: "POST",
    body: JSON.stringify({ transcript, timestamped_transcript }),
  });
}

/**
 * DELETE helper for /remove/{id} endpoint.
 * Returns true if successful.
 */
export async function removeFromQueue(id: string): Promise<boolean> {
  await apiFetch(`/remove/${id}`, { method: "DELETE" });
  return true;
}

/**
 * GET helper for /queue endpoint.
 */
export interface QueueItem {
  id: string;
  incidentType: string;
  location: string;
  time: string;
  severity_level: string;
  suggested_actions: string;
}

export async function fetchQueue(signal?: AbortSignal): Promise<QueueItem[]> {
  return apiFetch<QueueItem[]>("/queue", { signal });
}

/**
 * GET helper for /agent/{id} endpoint.
 */
export interface FullIncidentDetails {
  id: string;
  incidentType: string;
  location: string;
  date: string;
  time: string;
  duration: string;
  message: string;
  desc: string;
  suggested_actions: string;
  status: string;
  severity_level: string;
  transcript?: { text: string; time: string }[];
}

export async function fetchIncidentDetails(
  id: string
): Promise<FullIncidentDetails> {
  const result = await apiFetch<{ result: FullIncidentDetails }>(
    `/agent/${id}`
  );
  return result.result;
}
