/**
 * API module exports.
 *
 * Re-exports all API modules for convenient importing.
 */

// Client
export { apiClient, ApiError, getApiBaseUrl } from './client';

// Trading
export {
  tradingApi,
  TradingMode,
  RiskAction,
  OrderStatus,
} from './trading';
export type {
  TradingStatusResponse,
  AlertSchema,
  AlertsResponse,
  OrderResponse,
  RejectAlertResponse,
  RiskCheckRequest,
  RiskCheckResponse,
  PositionSizeRequest,
  PositionSizeResponse,
  CanOpenPositionRequest,
  CanOpenPositionResponse,
} from './trading';

// Signals
export { signalsApi, SignalType } from './signals';
export type {
  GenerateSignalRequest,
  SignalIndicators,
  TradingSignalResponse,
} from './signals';

// Positions
export { positionsApi } from './positions';
export type {
  PositionSchema,
  PositionListResponse,
  BalanceResponse,
  StockPriceResponse,
  DailyPriceResponse,
} from './positions';

// Indicators
export { indicatorsApi } from './indicators';
export type {
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
} from './indicators';

// Invitations
export {
  createInvitation,
  listInvitations,
  deleteInvitation,
} from './invitations';
export type {
  Invitation,
  CreateInvitationRequest,
  InvitationsResponse,
} from './invitations';

// API Keys
export {
  getApiKeyInfo,
  saveApiKey,
  deleteApiKey,
  verifyApiKey,
} from './api-keys';
export type {
  ApiKeyInfo,
  SaveApiKeyRequest,
  VerifyApiKeyResult,
} from './api-keys';

// Watchlist
export { watchlistApi } from './watchlist';
export type {
  WatchlistItem,
  WatchlistListResponse,
  CreateWatchlistItemRequest,
  UpdateWatchlistItemRequest,
  ToggleResponse,
  DeleteResponse,
} from './watchlist';

// Stocks
export { stocksApi } from './stocks';
export type { StockInfo, StockSearchResponse } from './stocks';

// Telegram
export { telegramApi } from './telegram';
export type {
  TelegramLinkResponse,
  TelegramStatusResponse,
  TelegramUnlinkResponse,
} from './telegram';
