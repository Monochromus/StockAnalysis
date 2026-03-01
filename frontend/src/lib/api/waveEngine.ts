/**
 * API client functions for Wave Engine endpoints.
 */

import { APIClient } from './client';
import type {
  WaveEngineRequest,
  WaveEngineResponse,
  EngineConfig,
  ConfigValidationResponse,
  DFAResult,
  RegimeState,
  ThresholdResult,
  RegimeEvent,
} from '$lib/types/waveEngine';

const client = new APIClient();

/**
 * Perform full wave analysis with DFA and adaptive thresholds.
 */
export async function analyzeWithWaveEngine(
  request: WaveEngineRequest
): Promise<WaveEngineResponse> {
  return client.post<WaveEngineResponse>('/wave-engine', request);
}

/**
 * Get the default engine configuration.
 */
export async function getDefaultConfig(): Promise<EngineConfig> {
  return client.get<EngineConfig>('/wave-engine/config/default');
}

/**
 * Validate a configuration.
 */
export async function validateConfig(
  config: EngineConfig
): Promise<ConfigValidationResponse> {
  return client.post<ConfigValidationResponse>('/wave-engine/config/validate', config);
}

/**
 * Get DFA analysis for a symbol.
 */
export async function getDFA(
  symbol: string,
  period: string = '1y',
  interval: string = '1d',
  window: number = 150
): Promise<{
  symbol: string;
  timestamp: string;
  dfa_result: DFAResult;
  regime_state: RegimeState;
}> {
  return client.get(`/wave-engine/dfa/${symbol}`, {
    period,
    interval,
    window: window.toString(),
  });
}

/**
 * Get current market regime for a symbol.
 */
export async function getRegime(
  symbol: string,
  period: string = '1y',
  interval: string = '1d'
): Promise<{
  symbol: string;
  timestamp: string;
  regime_state: RegimeState;
  regime_events: RegimeEvent[];
}> {
  return client.get(`/wave-engine/regime/${symbol}`, {
    period,
    interval,
  });
}

/**
 * Get adaptive threshold calculation for a symbol.
 */
export async function getThreshold(
  symbol: string,
  period: string = '1y',
  interval: string = '1d'
): Promise<{
  symbol: string;
  timestamp: string;
  threshold_result: ThresholdResult;
  dfa_alpha: number;
  regime: string;
}> {
  return client.get(`/wave-engine/threshold/${symbol}`, {
    period,
    interval,
  });
}
