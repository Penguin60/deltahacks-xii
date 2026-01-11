/**
 * Client-side ULID generation for current calls (frontend-only).
 * Used to give realistic unique IDs to simulated current calls.
 */

import { ulid } from "ulid";

/**
 * Generate a new ULID string.
 * Use this for current calls that stay client-side only.
 */
export function generateUlid(): string {
  return ulid();
}

/**
 * Get a display-friendly suffix of an ID (last 8 characters).
 * ULIDs have timestamp in prefix, so suffix is more unique visually.
 */
export function getIdSuffix(id: string, length: number = 8): string {
  if (!id) return "N/A";
  return id.slice(-length);
}
