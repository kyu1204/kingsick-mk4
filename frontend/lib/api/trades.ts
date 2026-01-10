/**
 * Trades API module for managing trade history.
 *
 * Provides functions for:
 * - Getting trade history
 * - Getting trade details
 */

import { apiClient } from './client';

/**
 * Trade schema.
 */
export interface TradeSchema {
  id: number;
  date: string;
  stock_code: string;
  stock_name: string;
  trade_type: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  total: number;
  status: string;
  signal_reason: string | null;
}

/**
 * Trade list response.
 */
export interface TradeListResponse {
  trades: TradeSchema[];
  total_count: number;
  page: number;
  page_size: number;
}

/**
 * Trades API functions.
 */
export const tradesApi = {
  /**
   * Get trade history with pagination.
   */
  async getTrades(page: number = 1, pageSize: number = 10): Promise<TradeListResponse> {
    const response = await apiClient.get<TradeListResponse>('/api/v1/trades/', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  /**
   * Get a specific trade by ID.
   */
  async getTrade(tradeId: number): Promise<TradeSchema> {
    const response = await apiClient.get<TradeSchema>(`/api/v1/trades/${tradeId}`);
    return response.data;
  },
};
