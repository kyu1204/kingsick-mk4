/**
 * Watchlist API module for managing user's watchlist items.
 *
 * Provides functions for:
 * - CRUD operations on watchlist items
 * - Toggle active status
 */

import { apiClient } from './client';

/**
 * Watchlist item schema.
 */
export interface WatchlistItem {
  id: string;
  stock_code: string;
  stock_name: string;
  is_active: boolean;
  target_price: number | null;
  stop_loss_price: number | null;
  quantity: number | null;
  memo: string | null;
  created_at: string;
  updated_at: string;
  current_price: number | null;
  price_change: number | null;
}

/**
 * Watchlist list response.
 */
export interface WatchlistListResponse {
  items: WatchlistItem[];
  total: number;
}

/**
 * Create watchlist item request.
 */
export interface CreateWatchlistItemRequest {
  stock_code: string;
  stock_name: string;
  target_price?: number | null;
  stop_loss_price?: number | null;
  quantity?: number | null;
  memo?: string | null;
}

/**
 * Update watchlist item request.
 */
export interface UpdateWatchlistItemRequest {
  target_price?: number | null;
  stop_loss_price?: number | null;
  quantity?: number | null;
  memo?: string | null;
  is_active?: boolean;
  clear_target_price?: boolean;
  clear_stop_loss_price?: boolean;
  clear_quantity?: boolean;
  clear_memo?: boolean;
}

/**
 * Toggle response.
 */
export interface ToggleResponse {
  id: string;
  is_active: boolean;
}

/**
 * Delete response.
 */
export interface DeleteResponse {
  message: string;
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
 * Watchlist API functions.
 */
export const watchlistApi = {
  /**
   * Get all watchlist items for current user.
   */
  async getWatchlist(activeOnly: boolean = false): Promise<WatchlistListResponse> {
    const response = await apiClient.get<WatchlistListResponse>('/api/v1/watchlist', {
      params: { active_only: activeOnly },
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /**
   * Get a single watchlist item by ID.
   */
  async getWatchlistItem(itemId: string): Promise<WatchlistItem> {
    const response = await apiClient.get<WatchlistItem>(`/api/v1/watchlist/${itemId}`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /**
   * Create a new watchlist item.
   */
  async createWatchlistItem(data: CreateWatchlistItemRequest): Promise<WatchlistItem> {
    const response = await apiClient.post<WatchlistItem>('/api/v1/watchlist', data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /**
   * Update a watchlist item.
   */
  async updateWatchlistItem(
    itemId: string,
    data: UpdateWatchlistItemRequest
  ): Promise<WatchlistItem> {
    const response = await apiClient.put<WatchlistItem>(`/api/v1/watchlist/${itemId}`, data, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },

  /**
   * Toggle active status of a watchlist item.
   */
  async toggleWatchlistItem(itemId: string): Promise<ToggleResponse> {
    const response = await apiClient.patch<ToggleResponse>(
      `/api/v1/watchlist/${itemId}/toggle`,
      {},
      {
        headers: getAuthHeaders(),
      }
    );
    return response.data;
  },

  /**
   * Delete a watchlist item.
   */
  async deleteWatchlistItem(itemId: string): Promise<DeleteResponse> {
    const response = await apiClient.delete<DeleteResponse>(`/api/v1/watchlist/${itemId}`, {
      headers: getAuthHeaders(),
    });
    return response.data;
  },
};
