/**
 * Stocks API module for stock search and information.
 *
 * Provides functions for:
 * - Searching stocks by name or code
 * - Getting stock information
 */

import { apiClient } from './client';

/**
 * Stock information schema.
 */
export interface StockInfo {
  code: string;
  name: string;
  market: string;
}

/**
 * Stock search response.
 */
export interface StockSearchResponse {
  stocks: StockInfo[];
  total: number;
}

/**
 * Get auth headers from localStorage.
 */
function getAuthHeaders(): { Authorization: string } | Record<string, never> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('kingsick_access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Stocks API functions.
 */
export const stocksApi = {
  /**
   * Search for stocks by name or code.
   */
  async searchStocks(query: string, limit: number = 20): Promise<StockSearchResponse> {
    const response = await apiClient.get<StockSearchResponse>('/api/v1/stocks/search', {
      params: { q: query, limit },
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /**
   * Get stock information by code.
   */
  async getStockInfo(stockCode: string): Promise<StockInfo> {
    const response = await apiClient.get<StockInfo>(`/api/v1/stocks/${stockCode}`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },
};
