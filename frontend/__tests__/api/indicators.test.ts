/**
 * Tests for indicators API module.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  indicatorsApi,
  SMARequest,
  SMAResponse,
  EMARequest,
  EMAResponse,
  RSIRequest,
  RSIResponse,
  MACDRequest,
  MACDResponse,
  BollingerBandsRequest,
  BollingerBandsResponse,
  VolumeSpikeRequest,
  VolumeSpikeResponse,
  CrossDetectionRequest,
  CrossDetectionResponse,
} from '@/lib/api/indicators';
import { ApiError } from '@/lib/api/client';

// MSW server setup
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('indicatorsApi', () => {
  describe('calculateSMA', () => {
    it('calculates SMA with given prices and period', async () => {
      const request: SMARequest = {
        prices: [100, 110, 120, 130, 140],
        period: 3,
      };
      const expectedResponse: SMAResponse = {
        values: [null, null, 110, 120, 130],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/sma', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await indicatorsApi.calculateSMA(request);
      expect(result).toEqual(expectedResponse);
    });

    it('throws ApiError on invalid input', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/indicators/sma', () => {
          return HttpResponse.json(
            { detail: 'Period must be greater than 0' },
            { status: 400 }
          );
        })
      );

      await expect(
        indicatorsApi.calculateSMA({ prices: [], period: 0 })
      ).rejects.toThrow(ApiError);
    });
  });

  describe('calculateEMA', () => {
    it('calculates EMA with given prices and period', async () => {
      const request: EMARequest = {
        prices: [100, 110, 120, 130, 140],
        period: 3,
      };
      const expectedResponse: EMAResponse = {
        values: [null, null, 110, 120, 130],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/ema', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await indicatorsApi.calculateEMA(request);
      expect(result).toEqual(expectedResponse);
    });
  });

  describe('calculateRSI', () => {
    it('calculates RSI with given prices', async () => {
      const request: RSIRequest = {
        prices: [100, 101, 102, 101, 100, 101, 102, 103, 104, 103, 102, 103, 104, 105, 106],
        period: 14,
      };
      const expectedResponse: RSIResponse = {
        values: [null, null, null, null, null, null, null, null, null, null, null, null, null, null, 60.5],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/rsi', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await indicatorsApi.calculateRSI(request);
      expect(result).toEqual(expectedResponse);
    });

    it('uses default period of 14 when not specified', async () => {
      const request: RSIRequest = {
        prices: [100, 101, 102],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/rsi', async ({ request: req }) => {
          const body = await req.json();
          expect(body.period).toBe(14);
          return HttpResponse.json({ values: [null, null, null] });
        })
      );

      await indicatorsApi.calculateRSI(request);
    });
  });

  describe('calculateMACD', () => {
    it('calculates MACD with given prices', async () => {
      const request: MACDRequest = {
        prices: [100, 101, 102, 103, 104, 105],
        fast: 12,
        slow: 26,
        signal: 9,
      };
      const expectedResponse: MACDResponse = {
        macd_line: [null, null, null, 0.5, 0.6, 0.7],
        signal_line: [null, null, null, null, null, 0.6],
        histogram: [null, null, null, null, null, 0.1],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/macd', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await indicatorsApi.calculateMACD(request);
      expect(result).toEqual(expectedResponse);
    });

    it('uses default periods when not specified', async () => {
      const request: MACDRequest = {
        prices: [100, 101, 102],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/macd', async ({ request: req }) => {
          const body = await req.json();
          expect(body.fast).toBe(12);
          expect(body.slow).toBe(26);
          expect(body.signal).toBe(9);
          return HttpResponse.json({ macd_line: [], signal_line: [], histogram: [] });
        })
      );

      await indicatorsApi.calculateMACD(request);
    });
  });

  describe('calculateBollingerBands', () => {
    it('calculates Bollinger Bands with given prices', async () => {
      const request: BollingerBandsRequest = {
        prices: [100, 101, 102, 103, 104],
        period: 20,
        std_dev: 2.0,
      };
      const expectedResponse: BollingerBandsResponse = {
        upper: [null, null, null, null, 110],
        middle: [null, null, null, null, 102],
        lower: [null, null, null, null, 94],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/bollinger-bands', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await indicatorsApi.calculateBollingerBands(request);
      expect(result).toEqual(expectedResponse);
    });

    it('uses default period and std_dev when not specified', async () => {
      const request: BollingerBandsRequest = {
        prices: [100, 101, 102],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/bollinger-bands', async ({ request: req }) => {
          const body = await req.json();
          expect(body.period).toBe(20);
          expect(body.std_dev).toBe(2.0);
          return HttpResponse.json({ upper: [], middle: [], lower: [] });
        })
      );

      await indicatorsApi.calculateBollingerBands(request);
    });
  });

  describe('detectVolumeSpike', () => {
    it('detects volume spikes', async () => {
      const request: VolumeSpikeRequest = {
        volumes: [1000, 1100, 1200, 5000, 1300],
        threshold: 2.0,
        lookback: 20,
      };
      const expectedResponse: VolumeSpikeResponse = {
        spikes: [false, false, false, true, false],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/volume-spike', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await indicatorsApi.detectVolumeSpike(request);
      expect(result).toEqual(expectedResponse);
    });

    it('uses default threshold and lookback when not specified', async () => {
      const request: VolumeSpikeRequest = {
        volumes: [1000, 1100, 1200],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/volume-spike', async ({ request: req }) => {
          const body = await req.json();
          expect(body.threshold).toBe(2.0);
          expect(body.lookback).toBe(20);
          return HttpResponse.json({ spikes: [] });
        })
      );

      await indicatorsApi.detectVolumeSpike(request);
    });
  });

  describe('detectGoldenCross', () => {
    it('detects golden cross', async () => {
      const request: CrossDetectionRequest = {
        prices: [100, 101, 102, 103, 104, 105],
        short_period: 5,
        long_period: 20,
      };
      const expectedResponse: CrossDetectionResponse = {
        detected: true,
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/golden-cross', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await indicatorsApi.detectGoldenCross(request);
      expect(result).toEqual(expectedResponse);
    });

    it('uses default periods when not specified', async () => {
      const request: CrossDetectionRequest = {
        prices: [100, 101, 102],
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/golden-cross', async ({ request: req }) => {
          const body = await req.json();
          expect(body.short_period).toBe(5);
          expect(body.long_period).toBe(20);
          return HttpResponse.json({ detected: false });
        })
      );

      await indicatorsApi.detectGoldenCross(request);
    });
  });

  describe('detectDeathCross', () => {
    it('detects death cross', async () => {
      const request: CrossDetectionRequest = {
        prices: [105, 104, 103, 102, 101, 100],
        short_period: 5,
        long_period: 20,
      };
      const expectedResponse: CrossDetectionResponse = {
        detected: true,
      };

      server.use(
        http.post('http://localhost:8000/api/v1/indicators/death-cross', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await indicatorsApi.detectDeathCross(request);
      expect(result).toEqual(expectedResponse);
    });
  });
});
