import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { backtestApi, type BacktestResult, type BacktestListResponse } from '@/lib/api/backtest';

const mockBacktestResult: BacktestResult = {
  id: 'bt-123',
  name: 'Test Backtest',
  start_date: '2023-01-01',
  end_date: '2023-12-31',
  initial_capital: 10000000,
  final_capital: 12500000,
  total_return_pct: 25.0,
  cagr: 25.0,
  mdd: -8.5,
  sharpe_ratio: 1.5,
  win_rate: 0.6,
  profit_factor: 2.1,
  total_trades: 50,
  winning_trades: 30,
  losing_trades: 20,
  avg_win: 5.0,
  avg_loss: -2.5,
  max_win: 15.0,
  max_loss: -7.0,
  created_at: '2024-01-01T00:00:00Z',
  trades: [
    {
      trade_date: '2023-01-15',
      stock_code: '005930',
      side: 'BUY',
      price: 60000,
      quantity: 10,
      amount: 600000,
      commission: 150,
      tax: 0,
      signal_reason: 'RSI oversold',
      pnl: 0,
      pnl_pct: 0,
    },
  ],
  daily_equity: [10000000, 10100000, 10200000],
  daily_returns: [0, 1.0, 0.99],
  drawdown_curve: [0, -0.5, -0.3],
};

const mockListResponse: BacktestListResponse = {
  count: 2,
  results: [
    {
      id: 'bt-123',
      name: 'Test Backtest',
      start_date: '2023-01-01',
      end_date: '2023-12-31',
      total_return_pct: 25.0,
      sharpe_ratio: 1.5,
      total_trades: 50,
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'bt-456',
      name: 'Another Backtest',
      start_date: '2023-06-01',
      end_date: '2023-12-31',
      total_return_pct: -5.0,
      sharpe_ratio: 0.5,
      total_trades: 20,
      created_at: '2024-01-02T00:00:00Z',
    },
  ],
};

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('backtestApi', () => {
  describe('runBacktest', () => {
    it('runs backtest with correct parameters', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/backtest/run', async ({ request }) => {
          const body = await request.json() as Record<string, unknown>;
          expect(body.stock_codes).toEqual(['005930']);
          expect(body.start_date).toBe('2023-01-01');
          expect(body.end_date).toBe('2023-12-31');
          return HttpResponse.json(mockBacktestResult);
        })
      );

      const result = await backtestApi.runBacktest({
        stock_codes: ['005930'],
        start_date: '2023-01-01',
        end_date: '2023-12-31',
      });

      expect(result.id).toBe('bt-123');
      expect(result.total_return_pct).toBe(25.0);
    });
  });

  describe('listResults', () => {
    it('fetches list of backtest results with pagination', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/backtest/results', ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get('limit')).toBe('20');
          expect(url.searchParams.get('offset')).toBe('0');
          return HttpResponse.json(mockListResponse);
        })
      );

      const response = await backtestApi.listResults(20, 0);

      expect(response.count).toBe(2);
      expect(response.results).toHaveLength(2);
      expect(response.results[0].id).toBe('bt-123');
    });
  });

  describe('getResult', () => {
    it('fetches specific backtest result by ID', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/backtest/results/bt-123', () => {
          return HttpResponse.json(mockBacktestResult);
        })
      );

      const result = await backtestApi.getResult('bt-123');

      expect(result.id).toBe('bt-123');
      expect(result.name).toBe('Test Backtest');
      expect(result.trades).toHaveLength(1);
    });
  });

  describe('deleteResult', () => {
    it('deletes backtest result by ID', async () => {
      server.use(
        http.delete('http://localhost:8000/api/v1/backtest/results/bt-123', () => {
          return new HttpResponse(null, { status: 204 });
        })
      );

      await expect(backtestApi.deleteResult('bt-123')).resolves.not.toThrow();
    });
  });

  describe('syncPrices', () => {
    it('syncs stock prices for backtesting', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/backtest/prices/sync', async ({ request }) => {
          const body = await request.json() as Record<string, unknown>;
          expect(body.stock_code).toBe('005930');
          expect(body.days).toBe(365);
          return HttpResponse.json({
            stock_code: '005930',
            synced_count: 250,
            message: 'Successfully synced 250 days of price data',
          });
        })
      );

      const response = await backtestApi.syncPrices({
        stock_code: '005930',
        days: 365,
      });

      expect(response.stock_code).toBe('005930');
      expect(response.synced_count).toBe(250);
    });
  });

  describe('getPrices', () => {
    it('fetches stock price history', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/backtest/prices/005930', ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get('start_date')).toBe('2023-01-01');
          expect(url.searchParams.get('end_date')).toBe('2023-12-31');
          return HttpResponse.json({
            stock_code: '005930',
            start_date: '2023-01-01',
            end_date: '2023-12-31',
            count: 250,
            prices: [
              {
                date: '2023-01-02',
                open: 60000,
                high: 61000,
                low: 59500,
                close: 60500,
                volume: 1000000,
              },
            ],
          });
        })
      );

      const response = await backtestApi.getPrices('005930', '2023-01-01', '2023-12-31');

      expect(response.stock_code).toBe('005930');
      expect(response.count).toBe(250);
      expect(response.prices).toHaveLength(1);
    });
  });
});
