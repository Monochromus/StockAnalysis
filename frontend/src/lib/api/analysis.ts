import { apiClient } from './client';
import type {
  TickerSearchResponse,
  MarketDataResponse,
  AnalysisRequest,
  AnalysisResponse,
  PivotResponse,
  ManualWaveRequest,
} from '$lib/types';

export async function searchTickers(query: string, limit: number = 10): Promise<TickerSearchResponse> {
  return apiClient.get<TickerSearchResponse>('/ticker/search', {
    params: { q: query, limit },
  });
}

export async function validateTicker(symbol: string): Promise<{ valid: boolean; error?: string }> {
  try {
    const result = await apiClient.get<{ valid: boolean; error?: string }>(`/ticker/validate/${symbol}`);
    return result;
  } catch (error) {
    return { valid: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

export async function getMarketData(
  symbol: string,
  period: string = '1y',
  interval: string = '1d'
): Promise<MarketDataResponse> {
  return apiClient.get<MarketDataResponse>(`/data/${symbol}`, {
    params: { period, interval },
  });
}

export async function analyzeWaves(request: AnalysisRequest): Promise<AnalysisResponse> {
  return apiClient.post<AnalysisResponse>('/analysis', request);
}

export async function fetchPivots(request: AnalysisRequest): Promise<PivotResponse> {
  return apiClient.post<PivotResponse>('/analysis/pivots', request);
}

export async function analyzeManualWaves(request: ManualWaveRequest): Promise<AnalysisResponse> {
  return apiClient.post<AnalysisResponse>('/analysis/manual', request);
}
