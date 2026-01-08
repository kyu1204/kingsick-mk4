/**
 * Tests for trading API module.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  tradingApi,
  TradingMode,
  TradingStatusResponse,
  AlertSchema,
  RiskAction,
  RiskCheckRequest,
  RiskCheckResponse,
  PositionSizeRequest,
  PositionSizeResponse,
  CanOpenPositionRequest,
  CanOpenPositionResponse,
  OrderResponse,
  OrderStatus,
} from '@/lib/api/trading';
import { ApiError } from '@/lib/api/client';
import { SignalType } from '@/lib/api/signals';

// MSW server setup
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('tradingApi', () => {
  describe('getStatus', () => {
    it('returns current trading status', async () => {
      const expectedResponse: TradingStatusResponse = {
        mode: TradingMode.ALERT,
        pending_alerts_count: 3,
        trailing_stops_count: 2,
      };

      server.use(
        http.get('http://localhost:8000/api/v1/trading/status', () => {
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.getStatus();
      expect(result).toEqual(expectedResponse);
      expect(result.mode).toBe(TradingMode.ALERT);
    });
  });

  describe('setMode', () => {
    it('sets trading mode to AUTO', async () => {
      const expectedResponse: TradingStatusResponse = {
        mode: TradingMode.AUTO,
        pending_alerts_count: 0,
        trailing_stops_count: 2,
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/mode', async ({ request }) => {
          const body = await request.json() as { mode: TradingMode };
          expect(body.mode).toBe(TradingMode.AUTO);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.setMode(TradingMode.AUTO);
      expect(result.mode).toBe(TradingMode.AUTO);
    });

    it('sets trading mode to ALERT', async () => {
      const expectedResponse: TradingStatusResponse = {
        mode: TradingMode.ALERT,
        pending_alerts_count: 0,
        trailing_stops_count: 0,
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/mode', async ({ request }) => {
          const body = await request.json() as { mode: TradingMode };
          expect(body.mode).toBe(TradingMode.ALERT);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.setMode(TradingMode.ALERT);
      expect(result.mode).toBe(TradingMode.ALERT);
    });
  });

  describe('getAlerts', () => {
    it('returns list of pending alerts', async () => {
      const expectedAlerts: AlertSchema[] = [
        {
          alert_id: 'alert-1',
          stock_code: '005930',
          signal_type: SignalType.BUY,
          confidence: 0.85,
          reason: 'RSI oversold',
          current_price: 72500,
          suggested_quantity: 10,
          created_at: '2024-01-15T10:30:00Z',
        },
        {
          alert_id: 'alert-2',
          stock_code: '000660',
          signal_type: SignalType.SELL,
          confidence: 0.75,
          reason: 'RSI overbought',
          current_price: 185000,
          suggested_quantity: 5,
          created_at: '2024-01-15T10:31:00Z',
        },
      ];

      server.use(
        http.get('http://localhost:8000/api/v1/trading/alerts', () => {
          return HttpResponse.json({ alerts: expectedAlerts });
        })
      );

      const result = await tradingApi.getAlerts();
      expect(result.alerts).toHaveLength(2);
      expect(result.alerts[0].stock_code).toBe('005930');
      expect(result.alerts[0].signal_type).toBe(SignalType.BUY);
    });

    it('returns empty list when no pending alerts', async () => {
      server.use(
        http.get('http://localhost:8000/api/v1/trading/alerts', () => {
          return HttpResponse.json({ alerts: [] });
        })
      );

      const result = await tradingApi.getAlerts();
      expect(result.alerts).toHaveLength(0);
    });
  });

  describe('approveAlert', () => {
    it('approves alert and returns order response', async () => {
      const expectedResponse: OrderResponse = {
        success: true,
        order_id: 'ORD-12345678',
        message: 'Order executed for 005930',
        status: OrderStatus.PENDING,
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/alerts/approve', async ({ request }) => {
          const body = await request.json() as { alert_id: string };
          expect(body.alert_id).toBe('alert-1');
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.approveAlert('alert-1');
      expect(result.success).toBe(true);
      expect(result.order_id).toBe('ORD-12345678');
    });

    it('throws ApiError when alert not found', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/trading/alerts/approve', () => {
          return HttpResponse.json(
            { detail: 'Alert not found' },
            { status: 404 }
          );
        })
      );

      await expect(tradingApi.approveAlert('nonexistent')).rejects.toThrow(ApiError);
    });
  });

  describe('rejectAlert', () => {
    it('rejects alert successfully', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/trading/alerts/reject', async ({ request }) => {
          const body = await request.json() as { alert_id: string };
          expect(body.alert_id).toBe('alert-1');
          return HttpResponse.json({ rejected: true });
        })
      );

      const result = await tradingApi.rejectAlert('alert-1');
      expect(result.rejected).toBe(true);
    });

    it('throws ApiError when alert not found', async () => {
      server.use(
        http.post('http://localhost:8000/api/v1/trading/alerts/reject', () => {
          return HttpResponse.json(
            { detail: 'Alert not found' },
            { status: 404 }
          );
        })
      );

      await expect(tradingApi.rejectAlert('nonexistent')).rejects.toThrow(ApiError);
    });
  });

  describe('checkRisk', () => {
    it('returns HOLD action when within limits', async () => {
      const request: RiskCheckRequest = {
        entry_price: 100000,
        current_price: 102000,
      };
      const expectedResponse: RiskCheckResponse = {
        action: RiskAction.HOLD,
        reason: 'Position within acceptable range',
        current_profit_pct: 2.0,
        trigger_price: null,
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/risk/check', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.checkRisk(request);
      expect(result.action).toBe(RiskAction.HOLD);
      expect(result.current_profit_pct).toBe(2.0);
    });

    it('returns STOP_LOSS action when loss exceeds limit', async () => {
      const request: RiskCheckRequest = {
        entry_price: 100000,
        current_price: 92000,
      };
      const expectedResponse: RiskCheckResponse = {
        action: RiskAction.STOP_LOSS,
        reason: 'Stop loss triggered at -8%',
        current_profit_pct: -8.0,
        trigger_price: 95000,
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/risk/check', () => {
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.checkRisk(request);
      expect(result.action).toBe(RiskAction.STOP_LOSS);
    });

    it('returns TAKE_PROFIT action when profit exceeds target', async () => {
      const request: RiskCheckRequest = {
        entry_price: 100000,
        current_price: 115000,
      };
      const expectedResponse: RiskCheckResponse = {
        action: RiskAction.TAKE_PROFIT,
        reason: 'Take profit triggered at +15%',
        current_profit_pct: 15.0,
        trigger_price: 110000,
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/risk/check', () => {
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.checkRisk(request);
      expect(result.action).toBe(RiskAction.TAKE_PROFIT);
    });
  });

  describe('calculatePositionSize', () => {
    it('calculates position size based on risk parameters', async () => {
      const request: PositionSizeRequest = {
        available_capital: 10000000,
        stock_price: 72500,
        risk_per_trade_pct: 2.0,
      };
      const expectedResponse: PositionSizeResponse = {
        quantity: 27,
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/risk/position-size', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.calculatePositionSize(request);
      expect(result.quantity).toBe(27);
    });
  });

  describe('canOpenPosition', () => {
    it('returns true when position can be opened', async () => {
      const request: CanOpenPositionRequest = {
        investment_amount: 1000000,
        current_positions_count: 3,
        daily_pnl_pct: 1.5,
      };
      const expectedResponse: CanOpenPositionResponse = {
        can_open: true,
        reason: '',
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/risk/can-open', async ({ request: req }) => {
          const body = await req.json();
          expect(body).toEqual(request);
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.canOpenPosition(request);
      expect(result.can_open).toBe(true);
    });

    it('returns false when daily loss limit exceeded', async () => {
      const request: CanOpenPositionRequest = {
        investment_amount: 1000000,
        current_positions_count: 3,
        daily_pnl_pct: -5.5,
      };
      const expectedResponse: CanOpenPositionResponse = {
        can_open: false,
        reason: 'Daily loss limit exceeded',
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/risk/can-open', () => {
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.canOpenPosition(request);
      expect(result.can_open).toBe(false);
      expect(result.reason).toBe('Daily loss limit exceeded');
    });

    it('returns false when max positions reached', async () => {
      const request: CanOpenPositionRequest = {
        investment_amount: 1000000,
        current_positions_count: 10,
        daily_pnl_pct: 0,
      };
      const expectedResponse: CanOpenPositionResponse = {
        can_open: false,
        reason: 'Maximum positions limit reached',
      };

      server.use(
        http.post('http://localhost:8000/api/v1/trading/risk/can-open', () => {
          return HttpResponse.json(expectedResponse);
        })
      );

      const result = await tradingApi.canOpenPosition(request);
      expect(result.can_open).toBe(false);
    });
  });
});

describe('TradingMode enum', () => {
  it('has correct values', () => {
    expect(TradingMode.AUTO).toBe('AUTO');
    expect(TradingMode.ALERT).toBe('ALERT');
  });
});

describe('RiskAction enum', () => {
  it('has correct values', () => {
    expect(RiskAction.HOLD).toBe('HOLD');
    expect(RiskAction.STOP_LOSS).toBe('STOP_LOSS');
    expect(RiskAction.TAKE_PROFIT).toBe('TAKE_PROFIT');
    expect(RiskAction.TRAILING_STOP).toBe('TRAILING_STOP');
  });
});
