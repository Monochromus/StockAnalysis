/**
 * XGBoost API client for hybrid Prophet + XGBoost forecasting.
 */

import apiClient from './client';
import type {
  XGBoostAnalysisRequest,
  XGBoostAnalysisResponse,
  XGBoostComparisonResponse,
} from '$lib/types';

/**
 * Perform XGBoost hybrid analysis (Prophet + XGBoost residual correction).
 */
export async function analyzeXGBoost(
  request: XGBoostAnalysisRequest
): Promise<XGBoostAnalysisResponse> {
  return apiClient.post<XGBoostAnalysisResponse>('/xgboost/analyze', request);
}

/**
 * Get Prophet vs Hybrid comparison for a symbol.
 */
export async function getComparison(
  symbol: string,
  period: string = '5y',
  interval: string = '1d'
): Promise<XGBoostComparisonResponse> {
  const params = new URLSearchParams({
    period,
    interval,
  });
  return apiClient.get<XGBoostComparisonResponse>(
    `/xgboost/comparison/${encodeURIComponent(symbol)}?${params}`
  );
}
