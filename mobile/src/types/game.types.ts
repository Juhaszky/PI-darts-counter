export type GameMode = '301' | '501';
export type GameStatus = 'waiting' | 'in_progress' | 'finished';

export interface Player {
  id: string;
  name: string;
  score: number;
  throwsThisTurn: number;
  isCurrent: boolean;
}

export interface GameState {
  gameId: string;
  mode: GameMode;
  status: GameStatus;
  round: number;
  players: Player[];
  currentPlayerId: string;
  lastThrow?: ThrowData;
}

export interface ThrowData {
  player_id: string;
  playerName: string;
  segment: number;
  multiplier: number;
  totalScore: number;
  segmentName: string;
  remaining_score: number;
  isBust: boolean;
  throws_left: number;
  throwNumber: number;
}

export interface TurnComplete {
  playerId: string;
  throws: Array<{
    segmentName: string;
    total: number;
  }>;
  turnTotal: number;
  nextPlayerId: string;
}

export interface GameOverData {
  winnerId: string;
  winnerName: string;
  finalThrow: string;
  totalRounds: number;
  stats: Record<string, PlayerStats>;
}

export interface PlayerStats {
  avgPerDart: number;
  highestTurn: number;
}

export interface BustData {
  playerId: string;
  playerName: string;
  scoreBefore: number;
  attemptedThrow: number;
  scoreRestored: number;
}
