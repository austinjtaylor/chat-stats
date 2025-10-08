/**
 * Centralized API Client for Sports Stats Application - TypeScript version
 */

import type {
    QueryRequest,
    QueryResponse,
    StatsResponse,
    PlayerStatsResponse,
    TeamStatsResponse,
    GameStatsResponse,
    SearchPlayersRequest,
    SearchTeamsRequest,
    GameDetailsResponse
} from '../../types/api';

import type {
    Player,
    Team,
    Game,
    PlayerSeasonStats,
    TeamSeasonStats
} from '../../types/models';

interface RequestOptions extends RequestInit {
    headers?: HeadersInit;
}


/**
 * Custom API Error
 */
class APIError extends Error {
    status: number;
    data: any;

    constructor(message: string, status: number = 0, data: any = null) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }

    isNetworkError(): boolean {
        return this.status === 0;
    }

    isClientError(): boolean {
        return this.status >= 400 && this.status < 500;
    }

    isServerError(): boolean {
        return this.status >= 500;
    }
}

/**
 * Base API Client
 */
class APIClient {
    protected baseURL: string;
    protected defaultHeaders: Record<string, string>;

    constructor(baseURL: string = '/api') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }

    /**
     * Get the current auth token from Supabase
     * @private
     */
    private async getAuthToken(): Promise<string | null> {
        try {
            // Dynamically import to avoid circular dependencies
            const { getAccessToken } = await import('../../lib/auth');
            return await getAccessToken();
        } catch (error) {
            console.warn('Failed to get auth token:', error);
            return null;
        }
    }

    /**
     * Make an API request
     * @private
     */
    protected async request<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T | null> {
        const url = `${this.baseURL}${endpoint}`;

        // Get auth token and add to headers if available
        const token = await this.getAuthToken();
        const authHeaders: Record<string, string> = {};
        if (token) {
            authHeaders['Authorization'] = `Bearer ${token}`;
        }

        const config: RequestOptions = {
            ...options,
            headers: {
                ...this.defaultHeaders,
                ...authHeaders,
                ...(options.headers as Record<string, string>)
            }
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                // Handle 401 Unauthorized errors
                if (response.status === 401) {
                    // Dispatch event to show login modal
                    if (typeof window !== 'undefined') {
                        window.dispatchEvent(new CustomEvent('auth-required'));
                    }
                }

                const error = await response.json().catch(() => ({}));
                throw new APIError(
                    error.detail || `HTTP ${response.status}: ${response.statusText}`,
                    response.status,
                    error
                );
            }

            // Handle empty responses
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }

            return null;
        } catch (error) {
            if (error instanceof APIError) {
                throw error;
            }
            throw new APIError(`Network error: ${(error as Error).message}`, 0, error);
        }
    }

    /**
     * GET request
     */
    async get<T = any>(endpoint: string, params: Record<string, any> = {}): Promise<T> {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request<T>(url, { method: 'GET' }) as Promise<T>;
    }

    /**
     * POST request
     */
    async post<T = any>(endpoint: string, data: any = {}): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        }) as Promise<T>;
    }

    /**
     * PUT request
     */
    async put<T = any>(endpoint: string, data: any = {}): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        }) as Promise<T>;
    }

    /**
     * DELETE request
     */
    async delete<T = any>(endpoint: string): Promise<T> {
        return this.request<T>(endpoint, { method: 'DELETE' }) as Promise<T>;
    }
}

/**
 * Sports Stats API Methods
 */
class StatsAPI extends APIClient {
    /**
     * Query the chat endpoint
     */
    async query(message: string, sessionId?: string | null): Promise<QueryResponse> {
        const payload: QueryRequest = { query: message };
        if (sessionId) {
            payload.session_id = sessionId;
        }
        return this.post<QueryResponse>('/query', payload);
    }

    /**
     * Get summary statistics
     */
    async getStats(): Promise<StatsResponse> {
        return this.get<StatsResponse>('/stats');
    }

    /**
     * Search for players
     */
    async searchPlayers(params: SearchPlayersRequest | string): Promise<Player[]> {
        if (typeof params === 'string') {
            return this.get<Player[]>('/players/search', { q: params });
        }
        return this.get<Player[]>('/players/search', params);
    }

    /**
     * Get player details
     */
    async getPlayer(playerId: number | string): Promise<Player> {
        return this.get<Player>(`/players/${playerId}`);
    }

    /**
     * Get all players with filters
     */
    async getPlayers(filters: Record<string, any> = {}): Promise<Player[]> {
        return this.get<Player[]>('/players', filters);
    }

    /**
     * Get player stats
     */
    async getPlayerStats(
        params?: {
            season?: number | string | null;
            team?: string | null;
            position?: string | null;
            limit?: number;
            offset?: number;
            page?: number;
            per?: 'total' | 'per-game';
        } | null
    ): Promise<PlayerStatsResponse> {
        const requestParams: Record<string, any> = {
            limit: params?.limit ?? 100,
            offset: params?.offset ?? 0
        };

        if (params?.season) requestParams.season = params.season;
        if (params?.team) requestParams.team = params.team;
        if (params?.position) requestParams.position = params.position;
        if (params?.page) requestParams.page = params.page;
        if (params?.per) requestParams.per = params.per;

        return this.get<PlayerStatsResponse>('/players/stats', requestParams);
    }

    /**
     * Search for teams
     */
    async searchTeams(query: SearchTeamsRequest | string): Promise<Team[]> {
        if (typeof query === 'string') {
            return this.get<Team[]>('/teams/search', { q: query });
        }
        return this.get<Team[]>('/teams/search', query);
    }

    /**
     * Get all teams
     */
    async getTeams(year?: number | string | null): Promise<Team[]> {
        const params: Record<string, any> = {};
        if (year) params.year = year;
        return this.get<Team[]>('/teams', params);
    }

    /**
     * Get team details
     */
    async getTeam(teamId: number | string): Promise<Team> {
        return this.get<Team>(`/teams/${teamId}`);
    }

    /**
     * Get team stats
     */
    async getTeamStats(
        params?: {
            season?: number | string | null;
            limit?: number;
            offset?: number;
            view?: 'total' | 'per-game';
            perspective?: 'team' | 'opponent';
        } | null
    ): Promise<TeamStatsResponse> {
        const requestParams: Record<string, any> = {
            limit: params?.limit ?? 100,
            offset: params?.offset ?? 0
        };

        if (params?.season) requestParams.season = params.season;
        if (params?.view) requestParams.view = params.view;
        if (params?.perspective) requestParams.perspective = params.perspective;

        return this.get<TeamStatsResponse>('/teams/stats', requestParams);
    }

    /**
     * Get recent games
     */
    async getRecentGames(limit: number = 10): Promise<Game[]> {
        return this.get<Game[]>('/games/recent', { limit });
    }

    /**
     * Get all games with filters
     */
    async getGames(filters: Record<string, any> = {}): Promise<GameStatsResponse> {
        return this.get<GameStatsResponse>('/games', filters);
    }

    /**
     * Get games list for selection dropdown
     */
    async getGamesList(params?: {
        year?: number;
        team_id?: string;
        limit?: number;
    }): Promise<any> {
        const requestParams: Record<string, any> = {
            limit: params?.limit ?? 500
        };
        if (params?.year) requestParams.year = params.year;
        if (params?.team_id) requestParams.team_id = params.team_id;
        return this.get<any>('/games/list', requestParams);
    }

    /**
     * Get game details
     */
    async getGame(gameId: string): Promise<GameDetailsResponse> {
        return this.get<GameDetailsResponse>(`/games/${gameId}`);
    }

    /**
     * Get game play-by-play data
     */
    async getGamePlayByPlay(gameId: string): Promise<any> {
        return this.get<any>(`/games/${gameId}/play-by-play`);
    }

    /**
     * Get game box score
     */
    async getGameBoxScore(gameId: string): Promise<any> {
        return this.get<any>(`/games/${gameId}/box-score`);
    }

    /**
     * Get game events
     */
    async getGameEvents(gameId: string): Promise<any[]> {
        return this.get<any[]>(`/games/${gameId}/events`);
    }

    /**
     * Get standings
     */
    async getStandings(season?: number | string | null, division?: string | null): Promise<TeamSeasonStats[]> {
        const params: Record<string, any> = {};
        if (season) params.season = season;
        if (division) params.division = division;
        return this.get<TeamSeasonStats[]>('/standings', params);
    }

    /**
     * Get league leaders
     */
    async getLeagueLeaders(
        category: string,
        season?: number | string | null,
        limit: number = 10
    ): Promise<PlayerSeasonStats[]> {
        const params: Record<string, any> = { category, limit };
        if (season) params.season = season;
        return this.get<PlayerSeasonStats[]>('/leaders', params);
    }

    /**
     * Get database info
     */
    async getDatabaseInfo(): Promise<any> {
        return this.get('/database/info');
    }

    /**
     * Import data
     */
    async importData(file: File): Promise<any> {
        const formData = new FormData();
        formData.append('file', file);

        return this.request('/data/import', {
            method: 'POST',
            body: formData,
            headers: {} // Let browser set Content-Type with boundary
        });
    }

    /**
     * Get available seasons
     */
    async getSeasons(): Promise<number[]> {
        return this.get<number[]>('/seasons');
    }

    /**
     * Get positions
     */
    async getPositions(): Promise<string[]> {
        return this.get<string[]>('/positions');
    }

    /**
     * Get game details (alias for compatibility)
     */
    async getGameDetails(gameId: string): Promise<GameDetailsResponse> {
        return this.getGame(gameId);
    }
}

// Create singleton instance with environment variable or default to relative path
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const statsAPI = new StatsAPI(API_BASE_URL);

// ES Module exports
export { APIClient, APIError, StatsAPI, statsAPI };
export default statsAPI;

// For backward compatibility with script tags
if (typeof window !== 'undefined') {
    (window as any).StatsAPI = StatsAPI;
    (window as any).statsAPI = statsAPI;
    (window as any).APIError = APIError;
}