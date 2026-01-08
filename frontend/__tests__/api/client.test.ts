/**
 * Tests for base API client.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { apiClient, ApiError, getApiBaseUrl } from '@/lib/api/client';

// MSW server setup
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('getApiBaseUrl', () => {
  it('returns default URL when environment variable is not set', () => {
    // Store original value
    const originalEnv = process.env.NEXT_PUBLIC_API_URL;
    delete process.env.NEXT_PUBLIC_API_URL;

    // Should return default
    const url = getApiBaseUrl();
    expect(url).toBe('http://localhost:8000');

    // Restore
    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  });

  it('returns environment variable value when set', () => {
    const originalEnv = process.env.NEXT_PUBLIC_API_URL;
    process.env.NEXT_PUBLIC_API_URL = 'http://custom-api:9000';

    const url = getApiBaseUrl();
    expect(url).toBe('http://custom-api:9000');

    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  });
});

describe('apiClient', () => {
  describe('successful requests', () => {
    it('makes GET request and returns data', async () => {
      const mockData = { message: 'success' };
      server.use(
        http.get('http://localhost:8000/api/v1/test', () => {
          return HttpResponse.json(mockData);
        })
      );

      const response = await apiClient.get('/api/v1/test');
      expect(response.data).toEqual(mockData);
    });

    it('makes POST request with body and returns data', async () => {
      const requestBody = { prices: [100, 110, 120], period: 5 };
      const responseData = { values: [null, null, null, null, 110] };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/sma', async ({ request }) => {
          const body = await request.json();
          expect(body).toEqual(requestBody);
          return HttpResponse.json(responseData);
        })
      );

      const response = await apiClient.post('/api/v1/indicators/sma', requestBody);
      expect(response.data).toEqual(responseData);
    });

    it('includes correct headers for POST requests', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/test', ({ request }) => {
          expect(request.headers.get('Content-Type')).toBe('application/json');
          return HttpResponse.json({ ok: true });
        })
      );

      await apiClient.post('/api/v1/test', { data: 'test' });
    });
  });

  describe('error handling', () => {
    it('throws ApiError on 400 Bad Request', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/test', () => {
          return HttpResponse.json(
            { detail: 'Invalid input data' },
            { status: 400 }
          );
        })
      );

      await expect(apiClient.post('/api/v1/test', {})).rejects.toThrow(ApiError);

      try {
        await apiClient.post('/api/v1/test', {});
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('Invalid input data');
        expect((error as ApiError).status).toBe(400);
      }
    });

    it('throws ApiError on 404 Not Found', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/nonexistent', () => {
          return HttpResponse.json(
            { detail: 'Not found' },
            { status: 404 }
          );
        })
      );

      try {
        await apiClient.get('/api/v1/nonexistent');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).status).toBe(404);
      }
    });

    it('throws ApiError on 500 Internal Server Error', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/test', () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      try {
        await apiClient.get('/api/v1/test');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).status).toBe(500);
        expect((error as ApiError).message).toBe('Internal server error');
      }
    });

    it('throws ApiError on 503 Service Unavailable', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/positions', () => {
          return HttpResponse.json(
            { detail: 'KIS API credentials not configured' },
            { status: 503 }
          );
        })
      );

      try {
        await apiClient.get('/api/v1/positions');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).status).toBe(503);
        expect((error as ApiError).message).toBe('KIS API credentials not configured');
      }
    });

    it('handles network errors', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/test', () => {
          return HttpResponse.error();
        })
      );

      await expect(apiClient.get('/api/v1/test')).rejects.toThrow();
    });
  });
});

describe('ApiError', () => {
  it('creates error with status and message', () => {
    const error = new ApiError(400, 'Bad request');
    expect(error.status).toBe(400);
    expect(error.message).toBe('Bad request');
    expect(error.name).toBe('ApiError');
  });

  it('includes original data if provided', () => {
    const originalData = { errors: ['field1 is required'] };
    const error = new ApiError(422, 'Validation failed', originalData);
    expect(error.data).toEqual(originalData);
  });
});
