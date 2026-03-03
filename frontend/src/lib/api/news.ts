/**
 * News API client for Gemini-powered market research.
 */

import { apiClient } from './client';
import type {
  NewsAnalysisResponse,
  NewsDashboardResponse,
  NewsStatusResponse,
} from '$lib/types';

/**
 * Get news analysis dashboard for multiple commodities.
 */
export async function getNewsDashboard(
  symbols: string[],
  forceRefresh: boolean = false
): Promise<NewsDashboardResponse> {
  const params = new URLSearchParams();
  symbols.forEach(s => params.append('symbols', s));
  if (forceRefresh) {
    params.append('force_refresh', 'true');
  }

  return apiClient.get<NewsDashboardResponse>(`/news/dashboard?${params.toString()}`);
}

/**
 * Get news analysis for a single commodity.
 */
export async function getCommodityNews(
  symbol: string,
  forceRefresh: boolean = false
): Promise<NewsAnalysisResponse> {
  return apiClient.get<NewsAnalysisResponse>(`/news/${encodeURIComponent(symbol)}`, {
    params: { force_refresh: forceRefresh },
  });
}

/**
 * Force refresh news analysis for a commodity.
 */
export async function refreshCommodityNews(
  symbol: string
): Promise<NewsAnalysisResponse> {
  return apiClient.post<NewsAnalysisResponse>(`/news/${encodeURIComponent(symbol)}/refresh`);
}

/**
 * Get Gemini API status.
 */
export async function getNewsStatus(): Promise<NewsStatusResponse> {
  return apiClient.get<NewsStatusResponse>('/news/status');
}
