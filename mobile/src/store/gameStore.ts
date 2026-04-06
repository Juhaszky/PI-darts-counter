import { create } from 'zustand';
import type { GameState, ThrowData, BustData, GameOverData } from '../types/game.types';

interface GameStore {
  gameState: GameState | null;
  lastThrow: ThrowData | null;
  isBust: boolean;
  bustData: BustData | null;
  gameOverData: GameOverData | null;

  setGameState: (state: GameState) => void;
  updateThrow: (throwData: ThrowData) => void;
  setBust: (bustData: BustData) => void;
  clearBust: () => void;
  setGameOver: (data: GameOverData) => void;
  updatePlayerScore: (playerId: string, newScore: number) => void;
  setCurrentPlayer: (playerId: string) => void;
  reset: () => void;
}

export const useGameStore = create<GameStore>((set) => ({
  gameState: null,
  lastThrow: null,
  isBust: false,
  bustData: null,
  gameOverData: null,

  setGameState: (state) =>
    set({
      gameState: state,
      lastThrow: null,
      isBust: false,
      bustData: null,
    }),

  updateThrow: (throwData) =>
    set((state) => {
      console.log("érkező res", throwData);
      console.log("sztét", state);
      if (!state.gameState) return state;

      const updatedPlayers = state.gameState.players.map((player) =>
        player.id === throwData.player_id
          ? {
              ...player,
              score: throwData.remaining_score,
              throwsThisTurn: throwData.throwNumber,
            }
          : player
      );
      console.log("updated", updatedPlayers);

      return {
        lastThrow: throwData,
        gameState: {
          ...state.gameState,
          players: updatedPlayers,
          lastThrow: throwData,
        },
        isBust: false,
        bustData: null,
      };
    }),

  setBust: (bustData) =>
    set((state) => {
      if (!state.gameState) return state;

      const updatedPlayers = state.gameState.players.map((player) =>
        player.id === bustData.playerId
          ? {
              ...player,
              score: bustData.scoreRestored,
              throwsThisTurn: 0,
            }
          : player
      );

      return {
        isBust: true,
        bustData,
        gameState: {
          ...state.gameState,
          players: updatedPlayers,
        },
      };
    }),

  clearBust: () => set({ isBust: false, bustData: null }),

  setGameOver: (data) => set({ gameOverData: data }),

  updatePlayerScore: (playerId, newScore) =>
    set((state) => {
      if (!state.gameState) return state;

      const updatedPlayers = state.gameState.players.map((player) =>
        player.id === playerId ? { ...player, score: newScore } : player
      );

      return {
        gameState: {
          ...state.gameState,
          players: updatedPlayers,
        },
      };
    }),

  setCurrentPlayer: (playerId) =>
    set((state) => {
      if (!state.gameState) return state;

      const updatedPlayers = state.gameState.players.map((player) => ({
        ...player,
        isCurrent: player.id === playerId,
        throwsThisTurn: player.id === playerId ? player.throwsThisTurn : 0,
      }));

      return {
        gameState: {
          ...state.gameState,
          currentPlayerId: playerId,
          players: updatedPlayers,
        },
      };
    }),

  reset: () =>
    set({
      gameState: null,
      lastThrow: null,
      isBust: false,
      bustData: null,
      gameOverData: null,
    }),
}));
