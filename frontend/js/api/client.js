/**
 * Centralized API Client for Sports Stats Application
 */

class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }

    /**
     * Make an API request
     * @private
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.defaultHeaders,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
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
            throw new APIError(`Network error: ${error.message}`, 0, error);
        }
    }

    /**
     * GET request
     */
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET' });
    }

    /**
     * POST request
     */
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT request
     */
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}

/**
 * Custom API Error
 */
class APIError extends Error {
    constructor(message, status = 0, data = null) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }

    isNetworkError() {
        return this.status === 0;
    }

    isClientError() {
        return this.status >= 400 && this.status < 500;
    }

    isServerError() {
        return this.status >= 500;
    }
}

/**
 * Sports Stats API Methods
 */
class StatsAPI extends APIClient {
    /**
     * Query the chat endpoint
     */
    async query(message, sessionId = null) {
        const payload = { query: message };
        if (sessionId) {
            payload.session_id = sessionId;
        }
        return this.post('/query', payload);
    }

    /**
     * Get summary statistics
     */
    async getStats() {
        return this.get('/stats');
    }

    /**
     * Search for players
     */
    async searchPlayers(query) {
        return this.get('/players/search', { q: query });
    }

    /**
     * Get player details
     */
    async getPlayer(playerId) {
        return this.get(`/players/${playerId}`);
    }

    /**
     * Get all players with filters
     */
    async getPlayers(filters = {}) {
        return this.get('/players', filters);
    }

    /**
     * Get player stats
     */
    async getPlayerStats(season = null, team = null, position = null, limit = 100, offset = 0) {
        const params = { limit, offset };
        if (season) params.season = season;
        if (team) params.team = team;
        if (position) params.position = position;
        return this.get('/players/stats', params);
    }

    /**
     * Search for teams
     */
    async searchTeams(query) {
        return this.get('/teams/search', { q: query });
    }

    /**
     * Get all teams
     */
    async getTeams(season = null) {
        const params = {};
        if (season) params.season = season;
        return this.get('/teams', params);
    }

    /**
     * Get team details
     */
    async getTeam(teamId) {
        return this.get(`/teams/${teamId}`);
    }

    /**
     * Get team stats
     */
    async getTeamStats(season = null, limit = 100, offset = 0) {
        const params = { limit, offset };
        if (season) params.season = season;
        return this.get('/teams/stats', params);
    }

    /**
     * Get recent games
     */
    async getRecentGames(limit = 10) {
        return this.get('/games/recent', { limit });
    }

    /**
     * Get all games with filters
     */
    async getGames(filters = {}) {
        return this.get('/games', filters);
    }

    /**
     * Get game details
     */
    async getGame(gameId) {
        return this.get(`/games/${gameId}`);
    }

    /**
     * Get game events
     */
    async getGameEvents(gameId) {
        return this.get(`/games/${gameId}/events`);
    }

    /**
     * Get standings
     */
    async getStandings(season = null, division = null) {
        const params = {};
        if (season) params.season = season;
        if (division) params.division = division;
        return this.get('/standings', params);
    }

    /**
     * Get league leaders
     */
    async getLeagueLeaders(category, season = null, limit = 10) {
        const params = { category, limit };
        if (season) params.season = season;
        return this.get('/leaders', params);
    }

    /**
     * Get database info
     */
    async getDatabaseInfo() {
        return this.get('/database/info');
    }

    /**
     * Import data
     */
    async importData(file) {
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
    async getSeasons() {
        return this.get('/seasons');
    }

    /**
     * Get positions
     */
    async getPositions() {
        return this.get('/positions');
    }
}

// Export for use in other modules
const statsAPI = new StatsAPI();

// Make available globally for non-module scripts
if (typeof window !== 'undefined') {
    window.StatsAPI = StatsAPI;
    window.statsAPI = statsAPI;
    window.APIError = APIError;
}