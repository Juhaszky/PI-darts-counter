import axios, { AxiosInstance } from 'axios';
import { CONFIG } from '../constants/config';
import type {
  CreateGameRequest,
  CreateGameResponse,
  ManualScoreRequest,
  HealthResponse,
  ThrowResponse,
} from '../types/api.types';
import type { GameState, Player, ThrowData } from '../types/game.types';

class ApiService {
  private client: AxiosInstance | null = null;
  private baseURL: string = '';

  initialize(host: string, port: string): void {
    this.baseURL = `http://${host}:${port}`;
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: CONFIG.API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  async createGame(request: CreateGameRequest): Promise<CreateGameResponse> {
    if (!this.client) throw new Error('API not initialized');
    const response = await this.client.post<CreateGameResponse>('/api/games', request);
    return response.data;
  }

  async getGameState(gameId: string): Promise<GameState> {
    if (!this.client) throw new Error('API not initialized');
    const response = await this.client.get<GameState>(`/api/games/${gameId}`);
    return response.data;
  }

  async startGame(gameId: string): Promise<void> {
    if (!this.client) throw new Error('API not initialized');
    await this.client.post(`/api/games/${gameId}/start`);
  }

  async resetGame(gameId: string): Promise<void> {
    if (!this.client) throw new Error('API not initialized');
    await this.client.post(`/api/games/${gameId}/reset`);
  }

  async submitManualScore(gameId: string, score: ManualScoreRequest): Promise<ThrowResponse> {
    if (!this.client) throw new Error('API not initialized');
    const response = await this.client.post(`/api/games/${gameId}/throw`, score);
    return response.data;
  }

  async undoThrow(gameId: string): Promise<void> {
    if (!this.client) throw new Error('API not initialized');
    await this.client.post(`/api/games/${gameId}/undo`);
  }

  async getHealth(): Promise<HealthResponse> {
    if (!this.client) throw new Error('API not initialized');
    const response = await this.client.get<HealthResponse>('/api/health');
    return response.data;
  }

  async getPlayers() : Promise<Player[]> {
    if (!this.client) throw new Error('API not initialized');
    const response = await this.client.get<Player[]>(`/api/players`);
    return response.data;
  }

  getBaseURL(): string {
    return this.baseURL;
  }
}

export const apiService = new ApiService();
