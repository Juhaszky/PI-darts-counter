import { useCallback } from 'react';
import { apiService } from '../services/apiService';
import { wsService } from '../services/websocketService';
import { useGameStore } from '../store/gameStore';
import { useConnectionStore } from '../store/connectionStore';
import type { CreateGameRequest, ManualScoreRequest } from '../types/api.types';

export function useGame() {
  const { gameState, updateThrow, setCurrentPlayer } = useGameStore();

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
        console.log("players", gameState?.players);
        console.log("player_id", res.throw.player_id);
        const currentPlayerIdx = gameState?.players.findIndex((p) => p.id == res.throw.player_id);
        console.log("current", currentPlayerIdx);
        if (currentPlayerIdx) {
          const nextPlayer = gameState?.players[currentPlayerIdx + 1];
          if (nextPlayer) {
            setCurrentPlayer(nextPlayer?.id)
            console.log(gameState);
          }
        }
      }
      console.log("res", res);
      updateThrow(res.throw);
    } catch (error) {
      console.error('[useGame] Manual score failed:', error);
      throw error;
    }
  }, []);

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

  return {
    gameState,
    createGame,
    startGame,
    submitManualScore,
    undoLastThrow,
    getCurrentPlayer,
  };
}
