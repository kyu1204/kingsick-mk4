/**
 * Signals API module for generating trading signals.
 *
 * Provides functions for:
 * - Generating trading signals based on price and volume data
 */

import { apiClient } from './client';

/**
 * Signal type enum.
 */
export enum SignalType {
  BUY = 'BUY',
  SELL = 'SELL',
  HOLD = 'HOLD',
}

/**
 * Generate signal request.
 */
export interface GenerateSignalRequest {
  prices: number[];
  volumes: number[];
}

/**
 * Signal indicators data.
 */
export interface SignalIndicators {
  rsi?: number;
  macd?: number;
  volume_spike?: boolean;
  [key: string]: number | boolean | undefined;
}

/**
 * Trading signal response.
 */
export interface TradingSignalResponse {
  signal: SignalType;
  confidence: number;
  reason: string;
  indicators: SignalIndicators;
}

/**
 * Signals API functions.
 */
export const signalsApi = {
  /**
   * Generate trading signal based on price and volume data.
   */
  async generateSignal(request: GenerateSignalRequest): Promise<TradingSignalResponse> {
    const response = await apiClient.post<TradingSignalResponse>(
      '/api/v1/signals/generate',
      request
    );
    return response.data;
  },
};
