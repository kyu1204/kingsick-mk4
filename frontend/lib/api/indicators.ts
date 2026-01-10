/**
 * Indicators API module for technical analysis calculations.
 *
 * Provides functions for:
 * - SMA (Simple Moving Average)
 * - EMA (Exponential Moving Average)
 * - RSI (Relative Strength Index)
 * - MACD (Moving Average Convergence Divergence)
 * - Bollinger Bands
 * - Volume Spike Detection
 * - Golden Cross / Death Cross Detection
 */

import { apiClient } from './client';

// SMA Types
export interface SMARequest {
  prices: number[];
  period: number;
}

export interface SMAResponse {
  values: (number | null)[];
}

// EMA Types
export interface EMARequest {
  prices: number[];
  period: number;
}

export interface EMAResponse {
  values: (number | null)[];
}

// RSI Types
export interface RSIRequest {
  prices: number[];
  period?: number;
}

export interface RSIResponse {
  values: (number | null)[];
}

// MACD Types
export interface MACDRequest {
  prices: number[];
  fast?: number;
  slow?: number;
  signal?: number;
}

export interface MACDResponse {
  macd_line: (number | null)[];
  signal_line: (number | null)[];
  histogram: (number | null)[];
}

// Bollinger Bands Types
export interface BollingerBandsRequest {
  prices: number[];
  period?: number;
  std_dev?: number;
}

export interface BollingerBandsResponse {
  upper: (number | null)[];
  middle: (number | null)[];
  lower: (number | null)[];
}

// Volume Spike Types
export interface VolumeSpikeRequest {
  volumes: number[];
  threshold?: number;
  lookback?: number;
}

export interface VolumeSpikeResponse {
  spikes: boolean[];
}

// Cross Detection Types
export interface CrossDetectionRequest {
  prices: number[];
  short_period?: number;
  long_period?: number;
}

export interface CrossDetectionResponse {
  detected: boolean;
}

/**
 * Indicators API functions.
 */
export const indicatorsApi = {
  /**
   * Calculate Simple Moving Average.
   */
  async calculateSMA(request: SMARequest): Promise<SMAResponse> {
    const response = await apiClient.post<SMAResponse>('/api/v1/indicators/sma', request);
    return response.data;
  },

  /**
   * Calculate Exponential Moving Average.
   */
  async calculateEMA(request: EMARequest): Promise<EMAResponse> {
    const response = await apiClient.post<EMAResponse>('/api/v1/indicators/ema', request);
    return response.data;
  },

  /**
   * Calculate Relative Strength Index.
   */
  async calculateRSI(request: RSIRequest): Promise<RSIResponse> {
    const payload = {
      prices: request.prices,
      period: request.period ?? 14,
    };
    const response = await apiClient.post<RSIResponse>('/api/v1/indicators/rsi', payload);
    return response.data;
  },

  /**
   * Calculate MACD (Moving Average Convergence Divergence).
   */
  async calculateMACD(request: MACDRequest): Promise<MACDResponse> {
    const payload = {
      prices: request.prices,
      fast: request.fast ?? 12,
      slow: request.slow ?? 26,
      signal: request.signal ?? 9,
    };
    const response = await apiClient.post<MACDResponse>('/api/v1/indicators/macd', payload);
    return response.data;
  },

  /**
   * Calculate Bollinger Bands.
   */
  async calculateBollingerBands(request: BollingerBandsRequest): Promise<BollingerBandsResponse> {
    const payload = {
      prices: request.prices,
      period: request.period ?? 20,
      std_dev: request.std_dev ?? 2.0,
    };
    const response = await apiClient.post<BollingerBandsResponse>(
      '/api/v1/indicators/bollinger-bands',
      payload
    );
    return response.data;
  },

  /**
   * Detect volume spikes.
   */
  async detectVolumeSpike(request: VolumeSpikeRequest): Promise<VolumeSpikeResponse> {
    const payload = {
      volumes: request.volumes,
      threshold: request.threshold ?? 2.0,
      lookback: request.lookback ?? 20,
    };
    const response = await apiClient.post<VolumeSpikeResponse>(
      '/api/v1/indicators/volume-spike',
      payload
    );
    return response.data;
  },

  /**
   * Detect golden cross (short MA crosses above long MA).
   */
  async detectGoldenCross(request: CrossDetectionRequest): Promise<CrossDetectionResponse> {
    const payload = {
      prices: request.prices,
      short_period: request.short_period ?? 5,
      long_period: request.long_period ?? 20,
    };
    const response = await apiClient.post<CrossDetectionResponse>(
      '/api/v1/indicators/golden-cross',
      payload
    );
    return response.data;
  },

  /**
   * Detect death cross (short MA crosses below long MA).
   */
  async detectDeathCross(request: CrossDetectionRequest): Promise<CrossDetectionResponse> {
    const payload = {
      prices: request.prices,
      short_period: request.short_period ?? 5,
      long_period: request.long_period ?? 20,
    };
    const response = await apiClient.post<CrossDetectionResponse>(
      '/api/v1/indicators/death-cross',
      payload
    );
    return response.data;
  },
};
