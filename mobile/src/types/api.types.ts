import { GameMode, ThrowData } from './game.types';

export interface CreateGameRequest {
  mode: GameMode;
  doubleOut: boolean;
  players: Array<{ name: string }>;
}

export interface CreateGameResponse {
  gameId: string;
  mode: GameMode;
  status: string;
  createdAt: string;
}
export interface ThrowResponse {
  message: string;
  throw: ThrowData;
}

export interface ManualScoreRequest {
  segment: number;
  multiplier: number;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  cameras?: CameraStatus[];
}

interface CameraStatus {
  id: number;
  active: boolean;
}
