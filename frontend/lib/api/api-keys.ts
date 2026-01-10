/**
 * API Keys management module.
 *
 * Handles Korea Investment API credentials management.
 */

import { apiClient } from './client';

/**
 * API Key information (masked for security).
 */
export interface ApiKeyInfo {
  has_api_key: boolean;
  app_key_masked: string | null;
  account_no_masked: string | null;
  is_paper_trading: boolean;
  updated_at: string | null;
}

/**
 * Request to save API key credentials.
 */
export interface SaveApiKeyRequest {
  app_key: string;
  app_secret: string;
  account_no: string;
  is_paper_trading?: boolean;
}

/**
 * Result of API key verification.
 */
export interface VerifyApiKeyResult {
  valid: boolean;
  message: string;
}

/**
 * Get authorization header from stored token.
 */
function getAuthHeader(): { Authorization: string } | Record<string, never> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('kingsick_access_token');
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

/**
 * Get current API key information.
 *
 * @returns API key info with masked values
 */
export async function getApiKeyInfo(): Promise<ApiKeyInfo> {
  const response = await apiClient.get<ApiKeyInfo>(
    '/api/v1/settings/api-key',
    { headers: getAuthHeader() }
  );
  return response.data;
}

/**
 * Save API key credentials.
 * Credentials are encrypted before storage.
 *
 * @param request - API key credentials to save
 */
export async function saveApiKey(request: SaveApiKeyRequest): Promise<void> {
  await apiClient.post('/api/v1/settings/api-key', request, {
    headers: getAuthHeader(),
  });
}

/**
 * Delete stored API key credentials.
 */
export async function deleteApiKey(): Promise<void> {
  await apiClient.delete('/api/v1/settings/api-key', {
    headers: getAuthHeader(),
  });
}

/**
 * Verify API key credentials with KIS API.
 *
 * @returns Verification result with validity status and message
 */
export async function verifyApiKey(): Promise<VerifyApiKeyResult> {
  const response = await apiClient.post<VerifyApiKeyResult>(
    '/api/v1/settings/api-key/verify',
    null,
    { headers: getAuthHeader() }
  );
  return response.data;
}
