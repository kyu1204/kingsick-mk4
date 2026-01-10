/**
 * API module exports.
 *
 * Re-exports all API modules for convenient importing.
 */

export { apiClient, ApiError, getApiBaseUrl } from './client';

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

export { signalsApi, SignalType } from './signals';
export type {
  GenerateSignalRequest,
  SignalIndicators,
  TradingSignalResponse,
} from './signals';

export { positionsApi } from './positions';
export type {
  PositionSchema,
  PositionListResponse,
  BalanceResponse,
  StockPriceResponse,
  DailyPriceResponse,
} from './positions';

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

export { watchlistApi } from './watchlist';
export type {
  WatchlistItem,
  WatchlistListResponse,
  CreateWatchlistItemRequest,
  UpdateWatchlistItemRequest,
  ToggleResponse,
  DeleteResponse,
} from './watchlist';

export { stocksApi } from './stocks';
export type { StockInfo, StockSearchResponse } from './stocks';

export { telegramApi } from './telegram';
export type {
  TelegramLinkResponse,
  TelegramStatusResponse,
  TelegramUnlinkResponse,
} from './telegram';

export { slackApi } from './slack';
export type {
  SlackStatusResponse,
  SlackWebhookRequest,
  SlackMessageResponse,
} from './slack';

export { scannerApi } from './scanner';
