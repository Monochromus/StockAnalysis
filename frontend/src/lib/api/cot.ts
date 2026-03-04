/**
 * COT (Commitments of Traders) API client.
 */

import { apiClient } from './client';
import type {
  COTAnalysis,
  COTDashboardResponse,
  COTStatusResponse,
  COTMappingsResponse,
  COTRefreshResponse,
  COTHistoryResponse,
} from '$lib/types';

/**
 * Get COT API status and supported symbols.
 */
export async function getCOTStatus(): Promise<COTStatusResponse> {
  return apiClient.get<COTStatusResponse>('/cot/status');
}

/**
 * Get all available symbol mappings.
 */
export async function getCOTMappings(): Promise<COTMappingsResponse> {
  return apiClient.get<COTMappingsResponse>('/cot/mappings');
}

/**
 * Get COT analysis for a single symbol.
 */
export async function getCOTAnalysis(
  symbol: string,
  options?: {
    weeks?: number;
    lookbackWeeks?: number;
    forceRefresh?: boolean;
  }
): Promise<COTAnalysis> {
  const params = new URLSearchParams();

  if (options?.weeks) {
    params.append('weeks', options.weeks.toString());
  }
  if (options?.lookbackWeeks) {
    params.append('lookback_weeks', options.lookbackWeeks.toString());
  }
  if (options?.forceRefresh) {
    params.append('force_refresh', 'true');
  }

  const queryString = params.toString();
  const url = `/cot/${encodeURIComponent(symbol)}${queryString ? `?${queryString}` : ''}`;

  return apiClient.get<COTAnalysis>(url);
}

/**
 * Get COT historical data for charting.
 */
export async function getCOTHistory(
  symbol: string,
  weeks: number = 52
): Promise<COTHistoryResponse> {
  return apiClient.get<COTHistoryResponse>(
    `/cot/${encodeURIComponent(symbol)}/history?weeks=${weeks}`
  );
}

/**
 * Force refresh COT data for a symbol.
 */
export async function refreshCOTData(symbol: string): Promise<COTRefreshResponse> {
  return apiClient.post<COTRefreshResponse>(
    `/cot/${encodeURIComponent(symbol)}/refresh`
  );
}

/**
 * Get COT dashboard data for multiple symbols.
 */
export async function getCOTDashboard(
  symbols?: string[],
  forceRefresh: boolean = false
): Promise<COTDashboardResponse> {
  const params = new URLSearchParams();

  if (symbols && symbols.length > 0) {
    symbols.forEach(s => params.append('symbols', s));
  }
  if (forceRefresh) {
    params.append('force_refresh', 'true');
  }

  return apiClient.get<COTDashboardResponse>(`/cot/dashboard?${params.toString()}`);
}
