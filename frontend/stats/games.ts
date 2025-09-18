// Games page functionality - TypeScript version

import type { Game, Team } from '../types/models';
import type { GameStatsResponse } from '../types/api';

interface GameFilters {
    year?: string | number;
    team_id?: string | number;
}

class GamesPage {
    private gamesContainer: HTMLElement | null;
    private yearFilter: HTMLSelectElement | null;
    private teamFilter: HTMLSelectElement | null;
    private modal: HTMLElement | null;
    private closeModal: HTMLElement | null;
    private teams: Team[] = [];
    private games: Game[] = [];

    constructor() {
        this.gamesContainer = document.getElementById('gamesContainer');
        this.yearFilter = document.getElementById('yearFilter') as HTMLSelectElement;
        this.teamFilter = document.getElementById('teamFilter') as HTMLSelectElement;
        this.modal = document.getElementById('gameDetailModal');
        this.closeModal = document.getElementById('closeModal');

        this.init();
    }

    private async init(): Promise<void> {
        this.setupEventListeners();
        await this.loadTeams();
        await this.loadGames();
    }

    private setupEventListeners(): void {
        // Filter event listeners
        if (this.yearFilter) {
            this.yearFilter.addEventListener('change', () => this.loadGames());
        }

        if (this.teamFilter) {
            this.teamFilter.addEventListener('change', () => this.loadGames());
        }

        // Modal functionality
        if (this.closeModal) {
            this.closeModal.addEventListener('click', () => {
                if (this.modal) {
                    this.modal.style.display = 'none';
                }
            });
        }

        // Click outside modal to close
        window.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                if (this.modal) {
                    this.modal.style.display = 'none';
                }
            }
        });
    }

    private async loadTeams(): Promise<void> {
        try {
            // Use API client for teams
            this.teams = await window.statsAPI.getTeams();

            if (this.teamFilter) {
                this.teamFilter.innerHTML = '<option value="all">All</option>';
                const filter = this.teamFilter; // Capture in const for type narrowing

                this.teams.forEach(team => {
                    const option = document.createElement('option');
                    option.value = String(team.id || '');
                    option.textContent = `${team.city || ''} ${team.name || ''}`.trim();
                    filter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    private async loadGames(): Promise<void> {
        try {
            if (this.gamesContainer) {
                window.ufaStats.showLoading(this.gamesContainer, 'Loading games...');
            }

            const filters: GameFilters = {};

            if (this.yearFilter && this.yearFilter.value !== 'all') {
                filters.year = this.yearFilter.value;
            }

            if (this.teamFilter && this.teamFilter.value !== 'all') {
                filters.team_id = this.teamFilter.value;
            }

            // Use API client for games
            const response = await window.statsAPI.getGames(filters);

            // Handle both direct array and response object
            if (Array.isArray(response)) {
                this.games = response;
            } else if (response && 'games' in response) {
                this.games = (response as GameStatsResponse).games || [];
            } else {
                this.games = [];
            }

            this.displayGames(this.games);
        } catch (error) {
            console.error('Failed to load games:', error);
            if (this.gamesContainer) {
                this.gamesContainer.innerHTML = '<div class="error-message">Failed to load games. Please make sure the backend is running.</div>';
            }
        }
    }

    private displayGames(games: Game[]): void {
        if (!this.gamesContainer) return;

        if (!games || games.length === 0) {
            this.gamesContainer.innerHTML = '<div class="no-data">No games found</div>';
            return;
        }

        this.gamesContainer.innerHTML = games.map(game => this.renderGameCard(game)).join('');
    }

    private renderGameCard(game: Game): string {
        const formattedDate = window.Format ?
            window.Format.date(game.date) :
            new Date(game.date).toLocaleDateString();

        const gameId = game.game_id || game.id || '';

        return `
            <div class="game-card" data-game-id="${gameId}" style="cursor: pointer;">
                <div class="game-date">${formattedDate}</div>
                <div class="game-teams">
                    <span class="team-name">${game.home_team || ''}</span>
                    <span class="score">${game.home_score || 0}</span>
                    <span class="vs">vs</span>
                    <span class="score">${game.away_score || 0}</span>
                    <span class="team-name">${game.away_team || ''}</span>
                </div>
                ${game.venue ? `<div class="game-venue">${game.venue}</div>` : ''}
                <div style="margin-top: 8px;">
                    <a href="/stats/game-detail.html?game=${gameId}" style="color: var(--primary-color); text-decoration: none; font-size: 12px;">View Details →</a>
                </div>
            </div>
        `;
    }

    // Public method to show game details (can be called from external code)
    public async showGameDetails(gameId: string): Promise<void> {
        try {
            const gameDetails = await window.statsAPI.getGameDetails(gameId);
            // Implement game details modal display
            console.log('Game details:', gameDetails);
        } catch (error) {
            console.error('Failed to load game details:', error);
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.statsAPI) {
        new GamesPage();
    } else {
        // Wait for API to be available
        setTimeout(() => new GamesPage(), 100);
    }
});

// Export for module usage
export { GamesPage };
export default GamesPage;