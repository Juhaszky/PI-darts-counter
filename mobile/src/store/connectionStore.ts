import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { CONFIG } from '../constants/config';
import { ConnectionStatus } from '../services/websocketService';

interface ConnectionStore {
  host: string;
  port: string;
  status: ConnectionStatus;
  gameId: string | null;

  setHost: (host: string) => void;
  setPort: (port: string) => void;
  setStatus: (status: ConnectionStatus) => void;
  setGameId: (gameId: string | null) => void;

  loadStoredConnection: () => Promise<void>;
  saveConnection: () => Promise<void>;
  reset: () => void;
}

export const useConnectionStore = create<ConnectionStore>((set, get) => ({
  host: CONFIG.DEFAULT_HOST,
  port: CONFIG.DEFAULT_PORT,
  status: ConnectionStatus.DISCONNECTED,
  gameId: null,

  setHost: (host) => set({ host }),
  setPort: (port) => set({ port }),
  setStatus: (status) => set({ status }),
  setGameId: (gameId) => set({ gameId }),

  loadStoredConnection: async () => {
    try {
      const [host, port] = await Promise.all([
        AsyncStorage.getItem(CONFIG.STORAGE_KEYS.LAST_HOST),
        AsyncStorage.getItem(CONFIG.STORAGE_KEYS.LAST_PORT),
      ]);

      set({
        host: host || CONFIG.DEFAULT_HOST,
        port: port || CONFIG.DEFAULT_PORT,
      });
    } catch (error) {
      console.error('Failed to load stored connection:', error);
    }
  },

  saveConnection: async () => {
    try {
      const { host, port } = get();
      await Promise.all([
        AsyncStorage.setItem(CONFIG.STORAGE_KEYS.LAST_HOST, host),
        AsyncStorage.setItem(CONFIG.STORAGE_KEYS.LAST_PORT, port),
      ]);
    } catch (error) {
      console.error('Failed to save connection:', error);
    }
  },

  reset: () =>
    set({
      host: CONFIG.DEFAULT_HOST,
      port: CONFIG.DEFAULT_PORT,
      status: ConnectionStatus.DISCONNECTED,
      gameId: null,
    }),
}));
