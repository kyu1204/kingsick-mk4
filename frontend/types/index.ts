/**
 * KingSick TypeScript Type Definitions
 */

// ============================================================
// User & Authentication Types
// ============================================================

export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

// ============================================================
// Trading Types
// ============================================================

export type TradingMode = 'AUTO' | 'ALERT';

export type SignalType = 'BUY' | 'SELL' | 'HOLD';

export type OrderType = 'MARKET' | 'LIMIT';

export type OrderStatus = 'PENDING' | 'FILLED' | 'PARTIAL' | 'CANCELLED' | 'REJECTED';

export interface Stock {
  symbol: string;
  name: string;
  market: 'KOSPI' | 'KOSDAQ';
  sector?: string;
}

export interface StockPrice {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  previousClose: number;
  timestamp: string;
}

export interface TradingSignal {
  id: string;
  symbol: string;
  stockName: string;
  signal: SignalType;
  confidence: number;
  price: number;
  suggestedQuantity?: number;
  suggestedStopLoss?: number;
  suggestedTakeProfit?: number;
  factors: SignalFactor[];
  createdAt: string;
}

export interface SignalFactor {
  name: string;
  value: string;
  impact: 'positive' | 'negative' | 'neutral';
  description?: string;
}

export interface Order {
  id: string;
  symbol: string;
  stockName: string;
  type: 'BUY' | 'SELL';
  orderType: OrderType;
  quantity: number;
  price: number;
  status: OrderStatus;
  filledQuantity?: number;
  filledPrice?: number;
  createdAt: string;
  updatedAt: string;
}

export interface Position {
  id: string;
  symbol: string;
  stockName: string;
  quantity: number;
  averagePrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  stopLoss?: number;
  takeProfit?: number;
  trailingStop?: number;
  createdAt: string;
  updatedAt: string;
}

export interface Trade {
  id: string;
  symbol: string;
  stockName: string;
  type: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  total: number;
  fee: number;
  pnl?: number;
  pnlPercent?: number;
  executedAt: string;
}

// ============================================================
// Technical Analysis Types
// ============================================================

export interface TechnicalIndicators {
  symbol: string;
  timestamp: string;
  rsi: number;
  macd: MACDValues;
  bollingerBands: BollingerBandValues;
  movingAverages: MovingAverageValues;
  volume: VolumeIndicators;
}

export interface MACDValues {
  macd: number;
  signal: number;
  histogram: number;
}

export interface BollingerBandValues {
  upper: number;
  middle: number;
  lower: number;
  bandwidth: number;
}

export interface MovingAverageValues {
  ma5: number;
  ma10: number;
  ma20: number;
  ma60: number;
  ma120: number;
}

export interface VolumeIndicators {
  current: number;
  average20: number;
  ratio: number;
}

export interface CandlestickData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// ============================================================
// Settings Types
// ============================================================

export interface TradingSettings {
  mode: TradingMode;
  dailyLossLimit: number;
  stopLoss: number;
  takeProfit: number;
  trailingStop?: number;
  maxPositionSize: number;
  maxPositions: number;
}

export interface NotificationSettings {
  telegram: {
    enabled: boolean;
    botToken?: string;
    chatId?: string;
  };
  slack: {
    enabled: boolean;
    webhookUrl?: string;
  };
  email: {
    enabled: boolean;
    address?: string;
  };
  alerts: {
    signalGenerated: boolean;
    orderExecuted: boolean;
    stopLossTriggered: boolean;
    dailyReport: boolean;
  };
}

export interface KISApiSettings {
  connected: boolean;
  accountNumber?: string;
  accountType: 'LIVE' | 'PAPER';
  lastConnectedAt?: string;
}

// ============================================================
// Watchlist Types
// ============================================================

export interface WatchlistItem {
  id: string;
  symbol: string;
  stockName: string;
  addedAt: string;
  notes?: string;
}

export interface Watchlist {
  id: string;
  name: string;
  items: WatchlistItem[];
  createdAt: string;
  updatedAt: string;
}

// ============================================================
// Portfolio Types
// ============================================================

export interface PortfolioSummary {
  totalValue: number;
  totalCost: number;
  totalPnl: number;
  totalPnlPercent: number;
  cash: number;
  positionsCount: number;
  todayPnl: number;
  todayPnlPercent: number;
}

export interface PortfolioPerformance {
  date: string;
  value: number;
  pnl: number;
  pnlPercent: number;
}

// ============================================================
// API Response Types
// ============================================================

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// ============================================================
// WebSocket Message Types
// ============================================================

export interface WebSocketMessage<T = unknown> {
  type: string;
  data: T;
  timestamp: string;
}

export interface MarketDataMessage {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: string;
}

export interface SignalMessage {
  signal: TradingSignal;
  action: 'new' | 'updated' | 'expired';
}

export interface OrderStatusMessage {
  orderId: string;
  status: OrderStatus;
  filledQuantity?: number;
  filledPrice?: number;
  message?: string;
}
