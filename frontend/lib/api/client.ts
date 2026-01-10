/**
 * Base API client for making HTTP requests to the backend.
 *
 * Uses axios for HTTP requests with proper error handling.
 */

import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';

/**
 * Custom API error class with status code and message.
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly data?: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Get the API base URL from environment or use default.
 */
export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

// Token storage key (must match auth module)
const ACCESS_TOKEN_KEY = 'kingsick_access_token';

/**
 * Get stored access token from localStorage.
 */
function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Create axios instance with base configuration.
 */
function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: getApiBaseUrl(),
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor to add auth token
  client.interceptors.request.use(
    (config) => {
      const token = getStoredToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor to handle errors
  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error: AxiosError<{ detail?: string }>) => {
      if (error.response) {
        const { status, data } = error.response;
        const message = data?.detail || error.message || '오류가 발생했습니다';
        throw new ApiError(status, message, data);
      }
      throw error;
    }
  );

  return client;
}

/**
 * Singleton API client instance.
 */
export const apiClient = createApiClient();
