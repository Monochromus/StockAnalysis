/**
 * Prophet API client for time series forecasting.
 */

import apiClient from './client';
import type {
  ProphetAnalysisRequest,
  ProphetAnalysisResponse,
  ProphetPriceRequest,
  ProphetPriceResponse,
  ProphetIndicatorsRequest,
  ProphetIndicatorsResponse,
  ProphetComponentsResponse,
  ProphetBacktestRequest,
  ProphetBacktestResponse,
} from '$lib/types';

/**
 * Perform full Prophet analysis including price, volatility, and RSI forecasts.
 */
export async function analyzeProphet(
  request: ProphetAnalysisRequest
): Promise<ProphetAnalysisResponse> {
  return apiClient.post<ProphetAnalysisResponse>('/prophet/analyze', request);
}

/**
 * Forecast prices only, without volatility and RSI.
 */
export async function forecastPrice(
  request: ProphetPriceRequest
): Promise<ProphetPriceResponse> {
  return apiClient.post<ProphetPriceResponse>('/prophet/forecast/price', request);
}

/**
 * Forecast volatility and RSI only.
 */
export async function forecastIndicators(
  request: ProphetIndicatorsRequest
): Promise<ProphetIndicatorsResponse> {
  return apiClient.post<ProphetIndicatorsResponse>('/prophet/forecast/indicators', request);
}

/**
 * Get seasonal components (trend, weekly, monthly, yearly) for a symbol.
 */
export async function getComponents(
  symbol: string,
  horizon: string = 'long_term',
  period: string = '5y',
  interval: string = '1d'
): Promise<ProphetComponentsResponse> {
  const params = new URLSearchParams({
    horizon,
    period,
    interval,
  });
  return apiClient.get<ProphetComponentsResponse>(
    `/prophet/components/${encodeURIComponent(symbol)}?${params}`
  );
}

/**
 * Run Prophet backtest: train on data before cutoff_date, compare forecast to actual.
 */
export async function backtestProphet(
  request: ProphetBacktestRequest
): Promise<ProphetBacktestResponse> {
  return apiClient.post<ProphetBacktestResponse>('/prophet/backtest', request);
}
