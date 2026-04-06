export const CONFIG = {
  DEFAULT_HOST: '192.168.1.5',
  DEFAULT_PORT: '8000',
  WS_RECONNECT_DELAY: 3000,       // 3 seconds
  WS_MAX_RECONNECT_ATTEMPTS: 10,
  API_TIMEOUT: 10000,              // 10 seconds
  STORAGE_KEYS: {
    LAST_HOST: '@darts_last_host',
    LAST_PORT: '@darts_last_port',
    LAST_GAME_MODE: '@darts_last_mode',
  },
};

export const GAME_MODES = {
  301: { label: '301', startScore: 301 },
  501: { label: '501', startScore: 501 },
} as const;
