/**
 * Utility functions for chart primitives.
 */

/**
 * Normalize timestamp to UTC midnight for consistent comparison across timezones.
 * This ensures BTC-USD (UTC) and other assets (EST/other) use the same reference point.
 *
 * @param timestamp - Any timestamp string (ISO 8601, date only, etc.)
 * @returns Unix timestamp in seconds (UTC midnight of the date)
 */
export function normalizeTimestamp(timestamp: string): number {
  // Extract just the date part (YYYY-MM-DD) and treat as UTC midnight
  const dateOnly = timestamp.substring(0, 10);
  return Math.floor(new Date(dateOnly + 'T00:00:00Z').getTime() / 1000);
}
