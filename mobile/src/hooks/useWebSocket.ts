import { useEffect, useCallback } from 'react';
import { useNavigation } from '@react-navigation/native';
import * as Haptics from 'expo-haptics';
import { wsService } from '../services/websocketService';
import { useGameStore } from '../store/gameStore';
import { useConnectionStore } from '../store/connectionStore';
import type { WsEvent } from '../types/websocket.types';

export function useWebSocket() {
  const navigation = useNavigation();
  const { setGameState, updateThrow, setBust, clearBust, setGameOver, setCurrentPlayer } = useGameStore();
  const { setStatus } = useConnectionStore();

  const handleMessage = useCallback((event: WsEvent) => {
    console.log('[Hook] WS Event:', event.type);

    switch (event.type) {
      case 'game_state':
        setGameState(event.data);
        break;

      case 'throw_detected':
        updateThrow(event.data);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        break;

      case 'bust':
        setBust(event.data);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
        setTimeout(() => {
          clearBust();
          if (event.data?.nextPlayerId) {
            setCurrentPlayer(event.data.nextPlayerId);
          }
        }, 3000);
        break;

      case 'turn_complete':
        if (event.data?.nextPlayerId) {
          setCurrentPlayer(event.data.nextPlayerId);
        }
        break;

      case 'game_over':
        setGameOver(event.data);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        // Navigate to stats screen
        navigation.navigate('Stats' as never);
        break;

      case 'error':
        console.error('[Hook] WS Error:', event.data);
        break;

      default:
        console.warn('[Hook] Unknown event type:', event.type);
    }
  }, [setGameState, updateThrow, setBust, clearBust, setGameOver, setCurrentPlayer, navigation]);

  useEffect(() => {
    const unsubscribeMessages = wsService.onMessage(handleMessage);
    const unsubscribeStatus = wsService.onStatusChange((status) => {
      setStatus(status);
    });

    return () => {
      unsubscribeMessages();
      unsubscribeStatus();
    };
  }, [handleMessage, setStatus]);
}
