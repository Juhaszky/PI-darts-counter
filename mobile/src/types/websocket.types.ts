import { GameState, ThrowData, BustData, TurnComplete, GameOverData } from './game.types';

export type WsEventType =
  | 'game_state'
  | 'throw_detected'
  | 'bust'
  | 'turn_complete'
  | 'game_over'
  | 'camera_status'
  | 'error';

export interface WsEvent<T = any> {
  type: WsEventType;
  data: T;
}

export interface WsGameStateEvent extends WsEvent<GameState> {
  type: 'game_state';
}

export interface WsThrowDetectedEvent extends WsEvent<ThrowData> {
  type: 'throw_detected';
}

export interface WsBustEvent extends WsEvent<BustData> {
  type: 'bust';
}

export interface WsTurnCompleteEvent extends WsEvent<TurnComplete> {
  type: 'turn_complete';
}

export interface WsGameOverEvent extends WsEvent<GameOverData> {
  type: 'game_over';
}

export interface WsErrorEvent extends WsEvent<ErrorData> {
  type: 'error';
}

export interface ErrorData {
  code: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
}

export interface CameraStatus {
  id: number;
  label: string;
  active: boolean;
}

// ---- Outgoing (client → server) message types ----

export type WsOutgoingEventType =
  | 'manual_score'
  | 'undo_throw'
  | 'next_turn'
  | 'camera_frame';

export interface WsCameraFramePayload {
  frame: string; // base64-encoded JPEG
}
