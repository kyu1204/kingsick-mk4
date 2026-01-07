/**
 * WebSocket client for real-time market data and trading signals
 */

type MessageHandler = (data: unknown) => void;
type ConnectionHandler = () => void;
type ErrorHandler = (error: Event) => void;

interface WebSocketClientOptions {
  url: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onOpen?: ConnectionHandler;
  onClose?: ConnectionHandler;
  onError?: ErrorHandler;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnect: boolean;
  private reconnectInterval: number;
  private maxReconnectAttempts: number;
  private reconnectAttempts: number = 0;
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private onOpen?: ConnectionHandler;
  private onClose?: ConnectionHandler;
  private onError?: ErrorHandler;
  private isConnecting: boolean = false;

  constructor(options: WebSocketClientOptions) {
    this.url = options.url;
    this.reconnect = options.reconnect ?? true;
    this.reconnectInterval = options.reconnectInterval ?? 5000;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 10;
    this.onOpen = options.onOpen;
    this.onClose = options.onClose;
    this.onError = options.onError;
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        console.log('[WebSocket] Connected to', this.url);
        this.onOpen?.();
      };

      this.ws.onclose = () => {
        this.isConnecting = false;
        console.log('[WebSocket] Disconnected from', this.url);
        this.onClose?.();

        // Attempt reconnection
        if (this.reconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(
            `[WebSocket] Reconnecting in ${this.reconnectInterval}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
          );
          setTimeout(() => this.connect(), this.reconnectInterval);
        }
      };

      this.ws.onerror = (event) => {
        this.isConnecting = false;
        console.error('[WebSocket] Error:', event);
        this.onError?.(event);
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;

          // Notify handlers for this message type
          const handlers = this.messageHandlers.get(type);
          if (handlers) {
            handlers.forEach((handler) => handler(data));
          }

          // Also notify wildcard handlers
          const wildcardHandlers = this.messageHandlers.get('*');
          if (wildcardHandlers) {
            wildcardHandlers.forEach((handler) => handler(message));
          }
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };
    } catch (error) {
      this.isConnecting = false;
      console.error('[WebSocket] Failed to connect:', error);
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.reconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Subscribe to messages of a specific type
   */
  subscribe(type: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }
    this.messageHandlers.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(type);
      if (handlers) {
        handlers.delete(handler);
      }
    };
  }

  /**
   * Send a message to the server
   */
  send(type: string, data?: unknown): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    } else {
      console.warn('[WebSocket] Cannot send message - not connected');
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

// Default WebSocket URL
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

// Singleton instance for market data
let marketDataClient: WebSocketClient | null = null;

/**
 * Get or create the market data WebSocket client
 */
export function getMarketDataClient(): WebSocketClient {
  if (!marketDataClient) {
    marketDataClient = new WebSocketClient({
      url: `${WS_URL}/market`,
      reconnect: true,
      reconnectInterval: 5000,
      maxReconnectAttempts: 10,
    });
  }
  return marketDataClient;
}

// Singleton instance for trading signals
let tradingSignalClient: WebSocketClient | null = null;

/**
 * Get or create the trading signal WebSocket client
 */
export function getTradingSignalClient(): WebSocketClient {
  if (!tradingSignalClient) {
    tradingSignalClient = new WebSocketClient({
      url: `${WS_URL}/signals`,
      reconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 15,
    });
  }
  return tradingSignalClient;
}
