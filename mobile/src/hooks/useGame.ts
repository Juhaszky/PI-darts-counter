import { useCallback } from 'react';
import { apiService } from '../services/apiService';
import { wsService } from '../services/websocketService';
import { useGameStore } from '../store/gameStore';
import { useConnectionStore } from '../store/connectionStore';
import type { CreateGameRequest, ManualScoreRequest } from '../types/api.types';
import { GameState } from '../types/game.types';

export function useGame() {
  const { gameState, updateThrow, setCurrentPlayer, setGameState } = useGameStore();

  const createGame = useCallback(async (request: CreateGameRequest) => {
    try {
      const response = await apiService.createGame(request);
      return response;
    } catch (error) {
      console.error('[useGame] Create game failed:', error);
      throw error;
    }
  }, []);

  const startGame = useCallback(async () => {
    const gameId = useConnectionStore.getState().gameId;
    if (!gameId) throw new Error('No game ID');
    try {
      await apiService.startGame(gameId);
    } catch (error) {
      console.error('[useGame] Start game failed:', error);
      throw error;
    }
  }, []);

  const submitManualScore = useCallback(async (score: ManualScoreRequest) => {
    const gameId = useConnectionStore.getState().gameId;
    if (!gameId) throw new Error('No game ID');
    try {
      const res = await apiService.submitManualScore(gameId, score);
      if (res.throw?.throws_left == -1) {
        const players = useGameStore.getState().gameState?.players;
        const currentPlayerIdx = players?.findIndex((p) => p.id == res.throw.player_id);
        if (players && currentPlayerIdx !== undefined && currentPlayerIdx !== -1) {
          const nextPlayer = players[(currentPlayerIdx + 1) % players.length];
          setCurrentPlayer(nextPlayer.id);
        }
      }
      updateThrow(res.throw);
    } catch (error) {
      console.error('[useGame] Manual score failed:', error);
      throw error;
    }
  }, [setCurrentPlayer, updateThrow]);

  const undoLastThrow = useCallback(async () => {
    const gameId = useConnectionStore.getState().gameId;
    if (!gameId) throw new Error('No game ID');
    try {
      await apiService.undoThrow(gameId);
    } catch (error) {
      console.error('[useGame] Undo throw failed:', error);
      throw error;
    }
  }, []);

  const getCurrentPlayer = useCallback(() => {
    if (!gameState) return null;
    return gameState.players.find((p) => p.isCurrent) || null;
  }, [gameState]);

  const fetchPlayers = useCallback(async () => {
    try {
      const players = await apiService.getPlayers();
      if (players && gameState) {
        setGameState({ ...gameState, players });
      }
    } catch (error) {
      console.error('[useGame] Fetch players failed:', error);
    }
  }, [gameState]);

  return {
    gameState,
    createGame,
    startGame,
    submitManualScore,
    undoLastThrow,
    getCurrentPlayer,
    fetchPlayers
  };
}
