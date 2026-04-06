import { CONFIG } from '../constants/config';
import type { WsEvent } from '../types/websocket.types';

type MessageHandler = (event: WsEvent) => void;

export enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts: number = 0;
  private host: string = '';
  private port: string = '';
  private gameId: string = '';
  private status: ConnectionStatus = ConnectionStatus.DISCONNECTED;
  private statusCallbacks: Set<(status: ConnectionStatus) => void> = new Set();

  connect(host: string, port: string, gameId: string): void {
    this.host = host;
    this.port = port;
    this.gameId = gameId;
    this.reconnectAttempts = 0;
    this._connect();
  }

  private _connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected');
      return;
    }

    const url = `ws://${this.host}:${this.port}/ws/${this.gameId}`;
    console.log('[WS] Connecting to:', url);

    this.setStatus(
      this.reconnectAttempts > 0 ? ConnectionStatus.RECONNECTING : ConnectionStatus.CONNECTING
    );

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('[WS] Connected');
        this.setStatus(ConnectionStatus.CONNECTED);
        this.reconnectAttempts = 0;
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const wsEvent: WsEvent = JSON.parse(event.data);
          console.log('[WS] Message received:', wsEvent.type);
          this.handlers.forEach((handler) => handler(wsEvent));
        } catch (error) {
          console.error('[WS] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WS] Error:', error);
        this.setStatus(ConnectionStatus.ERROR);
      };

      this.ws.onclose = (event) => {
        console.warn('[WS] Connection closed:', event.code, event.reason);
        this.setStatus(ConnectionStatus.DISCONNECTED);
        this.scheduleReconnect();
      };
    } catch (error) {
      console.error('[WS] Failed to create WebSocket:', error);
      this.setStatus(ConnectionStatus.ERROR);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= CONFIG.WS_MAX_RECONNECT_ATTEMPTS) {
      console.error('[WS] Max reconnect attempts reached');
      this.setStatus(ConnectionStatus.ERROR);
      return;
    }

    this.reconnectAttempts++;
    const delay = CONFIG.WS_RECONNECT_DELAY * this.reconnectAttempts; // Exponential backoff
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this._connect();
    }, delay);
  }

  send(type: string, data?: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({ type, data });
      this.ws.send(message);
      console.log('[WS] Sent:', type);
    } else {
      console.warn('[WS] Cannot send, not connected. Message:', type);
    }
  }

  sendManualScore(segment: number, multiplier: number): void {
    this.send('manual_score', { segment, multiplier });
  }

  sendUndo(): void {
    this.send('undo_throw');
  }

  sendNextTurn(): void {
    this.send('next_turn');
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  onStatusChange(callback: (status: ConnectionStatus) => void): () => void {
    this.statusCallbacks.add(callback);
    callback(this.status); // Immediate callback with current status
    return () => this.statusCallbacks.delete(callback);
  }

  private setStatus(status: ConnectionStatus): void {
    if (this.status !== status) {
      this.status = status;
      this.statusCallbacks.forEach((cb) => cb(status));
    }
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  disconnect(): void {
    console.log('[WS] Disconnecting');
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus(ConnectionStatus.DISCONNECTED);
    this.handlers.clear();
  }
}

export const wsService = new WebSocketService();
