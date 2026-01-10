/**
 * Trading API module for managing trading operations.
 *
 * Provides functions for:
 * - Getting/setting trading mode (AUTO/ALERT)
 * - Managing trading alerts
 * - Risk management checks
 */

import { apiClient } from './client';
import { SignalType } from './signals';

/**
 * Trading mode enum.
 */
export enum TradingMode {
  AUTO = 'AUTO',
  ALERT = 'ALERT',
}

/**
 * Risk action enum.
 */
export enum RiskAction {
  HOLD = 'HOLD',
  STOP_LOSS = 'STOP_LOSS',
  TAKE_PROFIT = 'TAKE_PROFIT',
  TRAILING_STOP = 'TRAILING_STOP',
}

/**
 * Order status enum.
 */
export enum OrderStatus {
  PENDING = 'PENDING',
  EXECUTED = 'EXECUTED',
  CANCELLED = 'CANCELLED',
  FAILED = 'FAILED',
}

/**
 * Trading status response.
 */
export interface TradingStatusResponse {
  mode: TradingMode;
  pending_alerts_count: number;
  trailing_stops_count: number;
}

/**
 * Alert schema.
 */
export interface AlertSchema {
  alert_id: string;
  stock_code: string;
  signal_type: SignalType;
  confidence: number;
  reason: string;
  current_price: number;
  suggested_quantity: number;
  created_at: string;
}

/**
 * Alerts list response.
 */
export interface AlertsResponse {
  alerts: AlertSchema[];
}

/**
 * Order response.
 */
export interface OrderResponse {
  success: boolean;
  order_id: string;
  message: string;
  status: OrderStatus;
}

/**
 * Reject alert response.
 */
export interface RejectAlertResponse {
  rejected: boolean;
}

/**
 * Risk check request.
 */
export interface RiskCheckRequest {
  entry_price: number;
  current_price: number;
}

/**
 * Risk check response.
 */
export interface RiskCheckResponse {
  action: RiskAction;
  reason: string;
  current_profit_pct: number;
  trigger_price: number | null;
}

/**
 * Position size request.
 */
export interface PositionSizeRequest {
  available_capital: number;
  stock_price: number;
  risk_per_trade_pct: number;
}

/**
 * Position size response.
 */
export interface PositionSizeResponse {
  quantity: number;
}

/**
 * Can open position request.
 */
export interface CanOpenPositionRequest {
  investment_amount: number;
  current_positions_count: number;
  daily_pnl_pct: number;
}

/**
 * Can open position response.
 */
export interface CanOpenPositionResponse {
  can_open: boolean;
  reason: string;
}

/**
 * Risk settings request.
 */
export interface RiskSettingsRequest {
  stop_loss_pct: number;
  take_profit_pct: number;
  daily_loss_limit_pct: number;
}

/**
 * Risk settings response.
 */
export interface RiskSettingsResponse {
  stop_loss_pct: number;
  take_profit_pct: number;
  daily_loss_limit_pct: number;
}

/**
 * Trading API functions.
 */
export const tradingApi = {
  /**
   * Get current trading status.
   */
  async getStatus(): Promise<TradingStatusResponse> {
    const response = await apiClient.get<TradingStatusResponse>('/api/v1/trading/status');
    return response.data;
  },

  /**
   * Set trading mode.
   */
  async setMode(mode: TradingMode): Promise<TradingStatusResponse> {
    const response = await apiClient.post<TradingStatusResponse>('/api/v1/trading/mode', { mode });
    return response.data;
  },

  /**
   * Get pending alerts.
   */
  async getAlerts(): Promise<AlertsResponse> {
    const response = await apiClient.get<AlertsResponse>('/api/v1/trading/alerts');
    return response.data;
  },

  /**
   * Approve an alert and execute the order.
   */
  async approveAlert(alertId: string): Promise<OrderResponse> {
    const response = await apiClient.post<OrderResponse>('/api/v1/trading/alerts/approve', {
      alert_id: alertId,
    });
    return response.data;
  },

  /**
   * Reject an alert.
   */
  async rejectAlert(alertId: string): Promise<RejectAlertResponse> {
    const response = await apiClient.post<RejectAlertResponse>('/api/v1/trading/alerts/reject', {
      alert_id: alertId,
    });
    return response.data;
  },

  /**
   * Check risk for a position.
   */
  async checkRisk(request: RiskCheckRequest): Promise<RiskCheckResponse> {
    const response = await apiClient.post<RiskCheckResponse>('/api/v1/trading/risk/check', request);
    return response.data;
  },

  /**
   * Calculate position size based on risk parameters.
   */
  async calculatePositionSize(request: PositionSizeRequest): Promise<PositionSizeResponse> {
    const response = await apiClient.post<PositionSizeResponse>(
      '/api/v1/trading/risk/position-size',
      request
    );
    return response.data;
  },

  /**
   * Check if a new position can be opened.
   */
  async canOpenPosition(request: CanOpenPositionRequest): Promise<CanOpenPositionResponse> {
    const response = await apiClient.post<CanOpenPositionResponse>(
      '/api/v1/trading/risk/can-open',
      request
    );
    return response.data;
  },

  /**
   * Get current risk settings.
   */
  async getRiskSettings(): Promise<RiskSettingsResponse> {
    const response = await apiClient.get<RiskSettingsResponse>('/api/v1/trading/risk-settings');
    return response.data;
  },

  /**
   * Update risk settings.
   */
  async updateRiskSettings(request: RiskSettingsRequest): Promise<RiskSettingsResponse> {
    const response = await apiClient.post<RiskSettingsResponse>(
      '/api/v1/trading/risk-settings',
      request
    );
    return response.data;
  },
};
