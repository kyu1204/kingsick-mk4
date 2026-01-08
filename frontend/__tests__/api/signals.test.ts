/**
 * Tests for signals API module.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  signalsApi,
  GenerateSignalRequest,
  TradingSignalResponse,
  SignalType,
} from '@/lib/api/signals';
import { ApiError } from '@/lib/api/client';

// MSW server setup
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('signalsApi', () => {
  describe('generateSignal', () => {
    it('generates BUY signal with high confidence', async () => {
      const request: GenerateSignalRequest = {
        prices: [100, 101, 102, 103, 104],
        volumes: [1000, 1100, 1200, 5000, 1300],
      };
      const expectedResponse: TradingSignalResponse = {
        signal: SignalType.BUY,
        confidence: 0.85,
        reason: 'RSI oversold with volume spike',
        indicators: {
          rsi: 28.5,
          macd: 0.5,
          volume_spike: true,
        },
      };

      server.use(
        http.post('http://localhost:8000/api/v1/signals/generate', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await signalsApi.generateSignal(request);
      expect(result).toEqual(expectedResponse);
      expect(result.signal).toBe(SignalType.BUY);
      expect(result.confidence).toBeGreaterThan(0.8);
    });

    it('generates SELL signal when conditions are met', async () => {
      const request: GenerateSignalRequest = {
        prices: [110, 109, 108, 107, 106],
        volumes: [1000, 900, 800, 700, 600],
      };
      const expectedResponse: TradingSignalResponse = {
        signal: SignalType.SELL,
        confidence: 0.75,
        reason: 'RSI overbought with declining volume',
        indicators: {
          rsi: 72.5,
          macd: -0.3,
          volume_spike: false,
        },
      };

      server.use(
        http.post('http://localhost:8000/api/v1/signals/generate', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await signalsApi.generateSignal(request);
      expect(result.signal).toBe(SignalType.SELL);
    });

    it('generates HOLD signal when no clear direction', async () => {
      const request: GenerateSignalRequest = {
        prices: [100, 101, 100, 101, 100],
        volumes: [1000, 1000, 1000, 1000, 1000],
      };
      const expectedResponse: TradingSignalResponse = {
        signal: SignalType.HOLD,
        confidence: 0.5,
        reason: 'No clear signal - market is ranging',
        indicators: {
          rsi: 50.0,
          macd: 0.0,
          volume_spike: false,
        },
      };

      server.use(
        http.post('http://localhost:8000/api/v1/signals/generate', () => {
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await signalsApi.generateSignal(request);
      expect(result.signal).toBe(SignalType.HOLD);
    });

    it('throws ApiError on invalid input', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/signals/generate', () => {
          return HttpResponse.json(
            { detail: 'Prices and volumes must have the same length' },
            { status: 400 }
          );
        })
      );

      await expect(
        signalsApi.generateSignal({ prices: [100], volumes: [1000, 2000] })
      ).rejects.toThrow(ApiError);
    });

    it('includes all required fields in response', async () => {
      const request: GenerateSignalRequest = {
        prices: [100, 101, 102],
        volumes: [1000, 1100, 1200],
      };
      const expectedResponse: TradingSignalResponse = {
        signal: SignalType.HOLD,
        confidence: 0.6,
        reason: 'Insufficient data for strong signal',
        indicators: {},
      };

      server.use(
        http.post('http://localhost:8000/api/v1/signals/generate', () => {
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await signalsApi.generateSignal(request);
      expect(result).toHaveProperty('signal');
      expect(result).toHaveProperty('confidence');
      expect(result).toHaveProperty('reason');
      expect(result).toHaveProperty('indicators');
    });
  });
});

describe('SignalType enum', () => {
  it('has correct values', () => {
    expect(SignalType.BUY).toBe('BUY');
    expect(SignalType.SELL).toBe('SELL');
    expect(SignalType.HOLD).toBe('HOLD');
  });
});
