/**
 * API Type Definitions
 *
 * These types match the backend Pydantic schemas for API request/response models.
 */

// ============================================================
// Indicator Types
// ============================================================

export interface SMARequest {
  prices: number[];
  period: number;
}

export interface SMAResponse {
  values: (number | null)[];
}

export interface EMARequest {
  prices: number[];
  period: number;
}

export interface EMAResponse {
  values: (number | null)[];
}

export interface RSIRequest {
  prices: number[];
  period?: number;
}

export interface RSIResponse {
  values: (number | null)[];
}

export interface MACDRequest {
  prices: number[];
  fast?: number;
  slow?: number;
  signal?: number;
}

export interface MACDResponse {
  macd_line: (number | null)[];
  signal_line: (number | null)[];
  histogram: (number | null)[];
}

export interface BollingerBandsRequest {
  prices: number[];
  period?: number;
  std_dev?: number;
}

export interface BollingerBandsResponse {
  upper: (number | null)[];
  middle: (number | null)[];
  lower: (number | null)[];
}

export interface VolumeSpikeRequest {
  volumes: number[];
  threshold?: number;
  lookback?: number;
}

export interface VolumeSpikeResponse {
  spikes: boolean[];
}

export interface CrossDetectionRequest {
  prices: number[];
  short_period?: number;
  long_period?: number;
}

export interface CrossDetectionResponse {
  detected: boolean;
}

// ============================================================
// Signal Types
// ============================================================

export type SignalTypeEnum = 'BUY' | 'SELL' | 'HOLD';

export interface GenerateSignalRequest {
  prices: number[];
  volumes: number[];
}

export interface TradingSignalResponse {
  signal: SignalTypeEnum;
  confidence: number;
  reason: string;
  indicators: Record<string, number | null>;
}

// ============================================================
// Trading Types
// ============================================================

export type TradingModeEnum = 'AUTO' | 'ALERT';
export type RiskActionEnum = 'HOLD' | 'STOP_LOSS' | 'TAKE_PROFIT' | 'TRAILING_STOP';
export type OrderSideEnum = 'BUY' | 'SELL';
export type OrderStatusEnum = 'PENDING' | 'FILLED' | 'PARTIAL' | 'CANCELLED' | 'FAILED';

export interface TradingStatusResponse {
  mode: TradingModeEnum;
  pending_alerts_count: number;
  trailing_stops_count: number;
}

export interface SetModeRequest {
  mode: TradingModeEnum;
}

export interface AlertSchema {
  alert_id: string;
  stock_code: string;
  signal_type: SignalTypeEnum;
  confidence: number;
  reason: string;
  current_price: number;
  suggested_quantity: number;
  created_at: string;
}

export interface AlertListResponse {
  alerts: AlertSchema[];
}

export interface ApproveAlertRequest {
  alert_id: string;
}

export interface RejectAlertRequest {
  alert_id: string;
}

export interface OrderResponse {
  success: boolean;
  order_id: string | null;
  message: string;
  status: OrderStatusEnum;
}

export interface RiskCheckRequest {
  entry_price: number;
  current_price: number;
  trailing_stop_price?: number;
}

export interface RiskCheckResponse {
  action: RiskActionEnum;
  reason: string;
  current_profit_pct: number;
  trigger_price: number | null;
}

export interface PositionSizeRequest {
  available_capital: number;
  stock_price: number;
  risk_per_trade_pct?: number;
}

export interface PositionSizeResponse {
  quantity: number;
}

export interface CanOpenPositionRequest {
  investment_amount: number;
  current_positions_count: number;
  daily_pnl_pct: number;
}

export interface CanOpenPositionResponse {
  can_open: boolean;
  reason: string;
}

// ============================================================
// Position Types
// ============================================================

export interface PositionSchema {
  stock_code: string;
  stock_name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  profit_loss: number;
  profit_loss_rate: number;
}

export interface PositionListResponse {
  positions: PositionSchema[];
}

export interface BalanceResponse {
  deposit: number;
  available_amount: number;
  total_evaluation: number;
  net_worth: number;
  purchase_amount: number;
  evaluation_amount: number;
}

export interface StockPriceResponse {
  code: string;
  name: string;
  current_price: number;
  open: number;
  high: number;
  low: number;
  change_rate: number;
  volume: number;
}

export interface DailyPriceResponse {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// ============================================================
// Error Types
// ============================================================

export interface ErrorResponse {
  detail: string;
}

// ============================================================
// Scanner Types
// ============================================================

export type ScanTypeEnum = 'BUY' | 'SELL';

export interface ScanResultResponse {
  stock_code: string;
  stock_name: string;
  signal: string;
  confidence: number;
  current_price: number;
  rsi: number;
  volume_spike: boolean;
  reasoning: string[];
}

export interface ScanResponse {
  results: ScanResultResponse[];
  total: number;
  scan_type: string;
  min_confidence: number;
}

export interface StockInfo {
  code: string;
  name: string;
}

export interface StockUniverseResponse {
  kospi: StockInfo[];
  kosdaq: StockInfo[];
  total: number;
}
