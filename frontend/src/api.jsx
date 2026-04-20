export const API_URL = import.meta.env.VITE_API_URL || "/api";

export function getRetryAfterSeconds(response, fallbackSeconds = 60) {
  const rawRetryAfter = response?.headers?.get("Retry-After") || "";
  const parsed = Number.parseInt(rawRetryAfter, 10);
  if (Number.isFinite(parsed) && parsed > 0) {
    return parsed;
  }
  return fallbackSeconds;
}

export function getRateLimitMessage(response) {
  const retryAfterSeconds = getRetryAfterSeconds(response, 60);
  return `Limit erreicht: Bitte warte noch ${retryAfterSeconds} Sekunden, dann kannst du neue Anfragen senden.`;
}
