/**
 * Seasonality API client for calendar analysis.
 */

import apiClient from './client';
import type {
  SeasonalityAnalysisRequest,
  SeasonalityAnalysisResponse,
} from '$lib/types';

/**
 * Analyze seasonality patterns for a symbol.
 */
export async function analyzeSeasonality(
  request: SeasonalityAnalysisRequest
): Promise<SeasonalityAnalysisResponse> {
  return apiClient.post<SeasonalityAnalysisResponse>('/seasonality/analyze', request);
}
