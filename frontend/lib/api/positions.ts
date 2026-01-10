/**
 * Positions API module for managing stock positions.
 *
 * Provides functions for:
 * - Getting current positions
 * - Getting account balance
 * - Getting stock prices
 * - Getting daily price history
 */

import { apiClient } from './client';

/**
 * Position schema.
 */
export interface PositionSchema {
  stock_code: string;
  stock_name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  profit_loss: number;
  profit_loss_rate: number;
}

/**
 * Position list response.
 */
export interface PositionListResponse {
  positions: PositionSchema[];
}

/**
 * Balance response.
 */
export interface BalanceResponse {
  deposit: number;
  available_amount: number;
  total_evaluation: number;
  net_worth: number;
  purchase_amount: number;
  evaluation_amount: number;
}

/**
 * Stock price response.
 */
export interface StockPriceResponse {
  code: string;
  name: string;
  current_price: number;
  open: number;
  high: number;
  low: number;
  change_rate: number;
  volume: number;
}

/**
 * Daily price response (OHLCV data).
 */
export interface DailyPriceResponse {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * Positions API functions.
 */
export const positionsApi = {
  /**
   * Get all current stock positions.
   */
  async getPositions(): Promise<PositionListResponse> {
    const response = await apiClient.get<PositionListResponse>('/api/v1/positions/');
    return response.data;
  },

  /**
   * Get account balance information.
   */
  async getBalance(): Promise<BalanceResponse> {
    const response = await apiClient.get<BalanceResponse>('/api/v1/positions/balance');
    return response.data;
  },

  /**
   * Get current stock price.
   */
  async getStockPrice(stockCode: string): Promise<StockPriceResponse> {
    const response = await apiClient.get<StockPriceResponse>(
      `/api/v1/positions/price/${stockCode}`
    );
    return response.data;
  },

  /**
   * Get daily OHLCV data for a stock.
   */
  async getDailyPrices(stockCode: string, count: number = 100): Promise<DailyPriceResponse[]> {
    const response = await apiClient.get<DailyPriceResponse[]>(
      `/api/v1/positions/daily-prices/${stockCode}`,
      { params: { count } }
    );
    return response.data;
  },
};
