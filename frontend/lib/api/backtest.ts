/**
 * Backtest API client for running backtests and retrieving results.
 */

import { apiClient } from './client';

// ============================================================
// Request Types
// ============================================================

export interface BacktestRunRequest {
  stock_codes: string[];
  start_date: string;
  end_date: string;
  name?: string;
  initial_capital?: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  max_position_pct?: number;
  max_positions?: number;
}

export interface PriceSyncRequest {
  stock_code: string;
  days?: number;
}

// ============================================================
// Response Types
// ============================================================

export interface BacktestTrade {
  trade_date: string;
  stock_code: string;
  side: 'BUY' | 'SELL';
  price: number;
  quantity: number;
  amount: number;
  commission: number;
  tax: number;
  signal_reason: string;
  pnl: number;
  pnl_pct: number;
}

export interface BacktestResult {
  id: string;
  name: string | null;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return_pct: number;
  cagr: number;
  mdd: number;
  sharpe_ratio: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: number;
  avg_loss: number;
  max_win: number;
  max_loss: number;
  created_at: string | null;
  trades: BacktestTrade[];
  daily_equity: number[];
  daily_returns: number[];
  drawdown_curve: number[];
}

export interface BacktestListItem {
  id: string;
  name: string | null;
  start_date: string;
  end_date: string;
  total_return_pct: number;
  sharpe_ratio: number;
  total_trades: number;
  created_at: string;
}

export interface BacktestListResponse {
  count: number;
  results: BacktestListItem[];
}

export interface PriceSyncResponse {
  stock_code: string;
  synced_count: number;
  message: string;
}

export interface StockPriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PriceListResponse {
  stock_code: string;
  start_date: string;
  end_date: string;
  count: number;
  prices: StockPriceData[];
}

// ============================================================
// API Functions
// ============================================================

export const backtestApi = {
  /**
   * Run a backtest with the specified parameters.
   */
  runBacktest: async (request: BacktestRunRequest): Promise<BacktestResult> => {
    const { data } = await apiClient.post<BacktestResult>(
      '/api/v1/backtest/run',
      request
    );
    return data;
  },

  /**
   * Get list of saved backtest results.
   */
  listResults: async (
    limit: number = 20,
    offset: number = 0
  ): Promise<BacktestListResponse> => {
    const { data } = await apiClient.get<BacktestListResponse>(
      '/api/v1/backtest/results',
      { params: { limit, offset } }
    );
    return data;
  },

  /**
   * Get a specific backtest result by ID.
   */
  getResult: async (backtestId: string): Promise<BacktestResult> => {
    const { data } = await apiClient.get<BacktestResult>(
      `/api/v1/backtest/results/${backtestId}`
    );
    return data;
  },

  /**
   * Delete a backtest result.
   */
  deleteResult: async (backtestId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/backtest/results/${backtestId}`);
  },

  /**
   * Sync stock price data for backtesting.
   */
  syncPrices: async (request: PriceSyncRequest): Promise<PriceSyncResponse> => {
    const { data } = await apiClient.post<PriceSyncResponse>(
      '/api/v1/backtest/prices/sync',
      request
    );
    return data;
  },

  /**
   * Get stock price history.
   */
  getPrices: async (
    stockCode: string,
    startDate: string,
    endDate: string
  ): Promise<PriceListResponse> => {
    const { data } = await apiClient.get<PriceListResponse>(
      `/api/v1/backtest/prices/${stockCode}`,
      { params: { start_date: startDate, end_date: endDate } }
    );
    return data;
  },

  /**
   * Sync latest prices for a stock.
   */
  syncLatestPrices: async (stockCode: string): Promise<PriceSyncResponse> => {
    const { data } = await apiClient.post<PriceSyncResponse>(
      `/api/v1/backtest/prices/${stockCode}/sync-latest`
    );
    return data;
  },
};
