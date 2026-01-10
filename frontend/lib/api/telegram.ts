/**
 * Telegram API client for managing Telegram integration.
 */

import { apiClient } from './client';

// Types
export interface TelegramLinkResponse {
  deep_link: string;
  expires_in: number; // seconds
}

export interface TelegramStatusResponse {
  linked: boolean;
  linked_at: string | null;
}

export interface TelegramUnlinkResponse {
  message: string;
}

// API functions
export const telegramApi = {
  /**
   * Create a Telegram link token and get the deep link URL.
   * The deep link will open the bot in Telegram for account linking.
   */
  createLinkToken: async (): Promise<TelegramLinkResponse> => {
    const response = await apiClient.post('/api/v1/telegram/link', {});
    return response.data;
  },

  /**
   * Get the current Telegram link status.
   */
  getStatus: async (): Promise<TelegramStatusResponse> => {
    const response = await apiClient.get('/api/v1/telegram/status');
    return response.data;
  },

  /**
   * Unlink the Telegram account.
   */
  unlink: async (): Promise<TelegramUnlinkResponse> => {
    const response = await apiClient.delete('/api/v1/telegram/link');
    return response.data;
  },
};
