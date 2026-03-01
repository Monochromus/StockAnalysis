/**
 * HMM API client for regime detection, indicators, and backtesting.
 */

import apiClient from './client';
import type {
  HMMAnalysisRequest,
  HMMAnalysisResponse,
  HMMTrainRequest,
  HMMTrainResponse,
  HMMRegimeRequest,
  HMMRegimeResponse,
  IndicatorRequest,
  IndicatorResponse,
  BacktestRequest,
  BacktestResult,
  SignalRequest,
  SignalResponse,
  HMMOptimizationRequest,
  StrategyOptimizationRequest,
  OptimizationStartResponse,
  OptimizationProgress,
  OptimizationResult,
  PresetSaveRequest,
  Preset,
  PresetListResponse,
} from '$lib/types';

/**
 * Perform full HMM analysis including regime detection, indicators, and signals.
 */
export async function analyzeHMM(request: HMMAnalysisRequest): Promise<HMMAnalysisResponse> {
  return apiClient.post<HMMAnalysisResponse>('/hmm/analyze', request);
}

/**
 * Train a new HMM model for a symbol.
 */
export async function trainHMM(request: HMMTrainRequest): Promise<HMMTrainResponse> {
  return apiClient.post<HMMTrainResponse>('/hmm/train', request);
}

/**
 * Get regime series for chart visualization.
 */
export async function getRegimeSeries(request: HMMRegimeRequest): Promise<HMMRegimeResponse> {
  return apiClient.post<HMMRegimeResponse>('/hmm/regimes', request);
}

/**
 * Get technical indicator series for chart overlays and subplots.
 */
export async function getIndicators(request: IndicatorRequest): Promise<IndicatorResponse> {
  return apiClient.post<IndicatorResponse>('/hmm/indicators', request);
}

/**
 * Run backtest on HMM regime-based strategy.
 */
export async function runBacktest(request: BacktestRequest): Promise<BacktestResult> {
  return apiClient.post<BacktestResult>('/hmm/backtest', request);
}

/**
 * Get current trading signal based on HMM regime and indicator confirmations.
 */
export async function getSignal(request: SignalRequest): Promise<SignalResponse> {
  return apiClient.post<SignalResponse>('/hmm/signal', request);
}

// ============== Optimization API ==============

/**
 * Start HMM parameter optimization asynchronously.
 */
export async function startHMMOptimization(
  request: HMMOptimizationRequest
): Promise<OptimizationStartResponse> {
  return apiClient.post<OptimizationStartResponse>('/hmm/optimize/hmm/start', request);
}

/**
 * Start strategy parameter optimization asynchronously.
 */
export async function startStrategyOptimization(
  request: StrategyOptimizationRequest
): Promise<OptimizationStartResponse> {
  return apiClient.post<OptimizationStartResponse>('/hmm/optimize/strategy/start', request);
}

/**
 * Get current progress of an optimization run.
 */
export async function getOptimizationProgress(
  optimizationId: string
): Promise<OptimizationProgress> {
  return apiClient.get<OptimizationProgress>(`/hmm/optimize/${optimizationId}/progress`);
}

/**
 * Get final result of a completed optimization.
 */
export async function getOptimizationResult(
  optimizationId: string
): Promise<OptimizationResult> {
  return apiClient.get<OptimizationResult>(`/hmm/optimize/${optimizationId}/result`);
}

/**
 * Cancel a running optimization.
 */
export async function cancelOptimization(
  optimizationId: string
): Promise<{ message: string; optimization_id: string }> {
  return apiClient.post<{ message: string; optimization_id: string }>(
    `/hmm/optimize/${optimizationId}/cancel`,
    {}
  );
}

// ============== Preset API ==============

/**
 * Save current settings as a preset.
 */
export async function savePreset(request: PresetSaveRequest): Promise<Preset> {
  return apiClient.post<Preset>('/hmm/presets', request);
}

/**
 * List all saved presets.
 */
export async function listPresets(): Promise<PresetListResponse> {
  return apiClient.get<PresetListResponse>('/hmm/presets');
}

/**
 * Get a specific preset by name.
 */
export async function getPreset(name: string): Promise<Preset> {
  return apiClient.get<Preset>(`/hmm/presets/${encodeURIComponent(name)}`);
}

/**
 * Delete a preset by name.
 */
export async function deletePreset(
  name: string
): Promise<{ message: string; name: string }> {
  return apiClient.delete<{ message: string; name: string }>(
    `/hmm/presets/${encodeURIComponent(name)}`
  );
}
