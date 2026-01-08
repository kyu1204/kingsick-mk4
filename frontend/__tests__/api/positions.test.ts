/**
 * Tests for positions API module.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  positionsApi,
  PositionListResponse,
  PositionSchema,
  BalanceResponse,
  StockPriceResponse,
  DailyPriceResponse,
} from '@/lib/api/positions';
import { ApiError } from '@/lib/api/client';

// MSW server setup
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('positionsApi', () => {
  describe('getPositions', () => {
    it('returns list of current positions', async () => {
      const expectedPositions: PositionSchema[] = [
        {
          stock_code: '005930',
          stock_name: 'Samsung Electronics',
          quantity: 10,
          avg_price: 70000,
          current_price: 72500,
          profit_loss: 25000,
          profit_loss_rate: 3.57,
        },
        {
          stock_code: '000660',
          stock_name: 'SK Hynix',
          quantity: 5,
          avg_price: 180000,
          current_price: 185000,
          profit_loss: 25000,
          profit_loss_rate: 2.78,
        },
      ];

      server.use(
        http.get('http://localhost:8000/api/v1/positions/', () => {
          return HttpResponse.json({ positions: expectedPositions });
        })
      );

      const result = await positionsApi.getPositions();
      expect(result.positions).toHaveLength(2);
      expect(result.positions[0].stock_code).toBe('005930');
      expect(result.positions[0].profit_loss_rate).toBe(3.57);
    });

    it('returns empty list when no positions', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/positions/', () => {
          return HttpResponse.json({ positions: [] });
        })
      );

      const result = await positionsApi.getPositions();
      expect(result.positions).toHaveLength(0);
    });

    it('throws ApiError when KIS API is not configured', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/positions/', () => {
          return HttpResponse.json(
            { detail: 'KIS API credentials not configured' },
            { status: 503 }
          );
        })
      );

      await expect(positionsApi.getPositions()).rejects.toThrow(ApiError);
    });
  });

  describe('getBalance', () => {
    it('returns account balance information', async () => {
      const expectedBalance: BalanceResponse = {
        deposit: 50000000,
        available_amount: 35000000,
        total_evaluation: 65000000,
        net_worth: 65000000,
        purchase_amount: 15000000,
        evaluation_amount: 15500000,
      };

      server.use(
        http.get('http://localhost:8000/api/v1/positions/balance', () => {
          return HttpResponse.json(expectedBalance);
        })
      );

      const result = await positionsApi.getBalance();
      expect(result).toEqual(expectedBalance);
      expect(result.deposit).toBe(50000000);
      expect(result.available_amount).toBe(35000000);
    });

    it('throws ApiError on server error', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/positions/balance', () => {
          return HttpResponse.json(
            { detail: 'KIS API error' },
            { status: 502 }
          );
        })
      );

      await expect(positionsApi.getBalance()).rejects.toThrow(ApiError);
    });
  });

  describe('getStockPrice', () => {
    it('returns current stock price', async () => {
      const expectedPrice: StockPriceResponse = {
        code: '005930',
        name: 'Samsung Electronics',
        current_price: 72500,
        open: 71000,
        high: 73000,
        low: 70500,
        change_rate: 2.11,
        volume: 15000000,
      };

      server.use(
        http.get('http://localhost:8000/api/v1/positions/price/005930', () => {
          return HttpResponse.json(expectedPrice);
        })
      );

      const result = await positionsApi.getStockPrice('005930');
      expect(result).toEqual(expectedPrice);
      expect(result.code).toBe('005930');
      expect(result.current_price).toBe(72500);
    });

    it('throws ApiError when stock not found', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/positions/price/999999', () => {
          return HttpResponse.json(
            { detail: 'Stock not found' },
            { status: 404 }
          );
        })
      );

      await expect(positionsApi.getStockPrice('999999')).rejects.toThrow(ApiError);
    });
  });

  describe('getDailyPrices', () => {
    it('returns daily OHLCV data with default count', async () => {
      const expectedPrices: DailyPriceResponse[] = [
        {
          date: '2024-01-15',
          open: 71000,
          high: 73000,
          low: 70500,
          close: 72500,
          volume: 15000000,
        },
        {
          date: '2024-01-14',
          open: 70000,
          high: 72000,
          low: 69500,
          close: 71000,
          volume: 12000000,
        },
      ];

      server.use(
        http.get('http://localhost:8000/api/v1/positions/daily-prices/005930', ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get('count')).toBe('100');
          return HttpResponse.json(expectedPrices);
        })
      );

      const result = await positionsApi.getDailyPrices('005930');
      expect(result).toHaveLength(2);
      expect(result[0].date).toBe('2024-01-15');
      expect(result[0].close).toBe(72500);
    });

    it('returns daily OHLCV data with custom count', async () => {
      const expectedPrices: DailyPriceResponse[] = [
        {
          date: '2024-01-15',
          open: 71000,
          high: 73000,
          low: 70500,
          close: 72500,
          volume: 15000000,
        },
      ];

      server.use(
        http.get('http://localhost:8000/api/v1/positions/daily-prices/005930', ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get('count')).toBe('50');
          return HttpResponse.json(expectedPrices);
        })
      );

      const result = await positionsApi.getDailyPrices('005930', 50);
      expect(result).toHaveLength(1);
    });

    it('throws ApiError on API error', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/positions/daily-prices/005930', () => {
          return HttpResponse.json(
            { detail: 'Failed to fetch daily prices' },
            { status: 502 }
          );
        })
      );

      await expect(positionsApi.getDailyPrices('005930')).rejects.toThrow(ApiError);
    });
  });
});
