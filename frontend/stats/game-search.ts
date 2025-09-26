/**
 * Game Search Component - Handles game selection panel
 */

export interface GameListItem {
    game_id: string;
    display_name: string;
    date: string;
    home_team: string;
    away_team: string;
    home_score: number;
    away_score: number;
    year: number;
    week: string;
}

export class GameSearch {
    private gameList: GameListItem[] = [];
    private currentYear: number = 2025;
    private currentTeamFilter: string = 'all';
    private teams: any[] = [];

    // DOM elements
    private elements = {
        gameSearchIcon: null as HTMLElement | null,
        gameSelectionPanel: null as HTMLElement | null,
        closePanel: null as HTMLElement | null,
        yearFilter: null as HTMLSelectElement | null,
        teamFilter: null as HTMLSelectElement | null,
        gameList: null as HTMLElement | null,
    };

    // Callbacks
    private onGameSelect: ((gameId: string) => void) | null = null;

    constructor() {
        this.initializeElements();
        this.attachEventListeners();
    }

    private initializeElements(): void {
        this.elements.gameSearchIcon = document.getElementById('gameSearchIcon');
        this.elements.gameSelectionPanel = document.getElementById('gameSelectionPanel');
        this.elements.closePanel = document.getElementById('closePanel');
        this.elements.yearFilter = document.getElementById('yearFilter') as HTMLSelectElement;
        this.elements.teamFilter = document.getElementById('teamFilter') as HTMLSelectElement;
        this.elements.gameList = document.getElementById('gameList');
    }

    private attachEventListeners(): void {
        // Game search icon toggle
        if (this.elements.gameSearchIcon) {
            this.elements.gameSearchIcon.addEventListener('click', () => {
                this.openGameSearch();
            });
        }

        // Close panel button
        if (this.elements.closePanel) {
            this.elements.closePanel.addEventListener('click', () => {
                this.closeGameSearch();
            });
        }

        // Click outside to close
        document.addEventListener('click', (e) => {
            const panel = this.elements.gameSelectionPanel;
            const icon = this.elements.gameSearchIcon;
            if (panel && icon &&
                panel.classList.contains('active') &&
                !panel.contains(e.target as Node) &&
                !icon.contains(e.target as Node)) {
                this.closeGameSearch();
            }
        });

        // Filter changes
        if (this.elements.yearFilter) {
            this.elements.yearFilter.addEventListener('change', (e) => {
                this.currentYear = parseInt((e.target as HTMLSelectElement).value);
                this.loadTeams();
                this.loadGamesList();
            });
        }

        if (this.elements.teamFilter) {
            this.elements.teamFilter.addEventListener('change', (e) => {
                this.currentTeamFilter = (e.target as HTMLSelectElement).value;
                this.loadGamesList();
            });
        }
    }

    public setOnGameSelect(callback: (gameId: string) => void): void {
        this.onGameSelect = callback;
    }

    public async initialize(): Promise<void> {
        await this.loadTeams();
        await this.loadGamesList();
    }

    private openGameSearch(): void {
        if (this.elements.gameSelectionPanel) {
            this.elements.gameSelectionPanel.classList.add('active');
            document.documentElement.classList.add('sidebar-open');
            document.body.classList.add('sidebar-open');
        }
    }

    public closeGameSearch(): void {
        if (this.elements.gameSelectionPanel) {
            this.elements.gameSelectionPanel.classList.remove('active');
            document.documentElement.classList.remove('sidebar-open');
            document.body.classList.remove('sidebar-open');
        }
    }

    private async loadTeams(): Promise<void> {
        try {
            const response = await fetch(`/api/teams?year=${this.currentYear}`);
            this.teams = await response.json();

            if (this.elements.teamFilter) {
                const currentSelection = this.elements.teamFilter.value;
                this.elements.teamFilter.innerHTML = '<option value="all">All</option>';

                this.teams.forEach(team => {
                    const option = document.createElement('option');
                    option.value = team.team_id;
                    option.textContent = team.name;
                    this.elements.teamFilter!.appendChild(option);
                });

                const teamExists = this.teams.some(team => team.team_id === currentSelection);
                if (teamExists) {
                    this.elements.teamFilter.value = currentSelection;
                } else {
                    this.elements.teamFilter.value = 'all';
                    this.currentTeamFilter = 'all';
                }
            }
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    public async loadGamesList(): Promise<void> {
        try {
            let url = `/api/games/list?limit=500&year=${this.currentYear}`;
            if (this.currentTeamFilter !== 'all') {
                url += `&team_id=${this.currentTeamFilter}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            this.gameList = data.games || [];
            console.log('Loaded games:', this.gameList.length);
            this.updateGameList();

            // Return first game if available
            const urlParams = new URLSearchParams(window.location.search);
            const gameIdFromUrl = urlParams.get('game');
            const isSidebarOpen = this.elements.gameSelectionPanel?.classList.contains('active');

            if (!gameIdFromUrl && this.gameList.length > 0 && !isSidebarOpen) {
                if (this.onGameSelect) {
                    this.onGameSelect(this.gameList[0].game_id);
                }
            }
        } catch (error) {
            console.error('Failed to load games list:', error);
        }
    }

    private updateGameList(): void {
        if (!this.elements.gameList) {
            console.error('gameList element not found');
            return;
        }

        console.log('Updating game list with', this.gameList.length, 'games');
        this.elements.gameList.innerHTML = this.gameList.map(game => {
            const date = new Date(game.date).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
            return `
                <div class="game-list-item" data-game-id="${game.game_id}">
                    <div style="font-weight: 500; margin-bottom: 4px;">
                        ${game.away_team} @ ${game.home_team}
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary);">
                        ${date} • ${game.away_score}-${game.home_score}
                    </div>
                </div>
            `;
        }).join('');

        // Add click handlers
        this.elements.gameList.querySelectorAll('.game-list-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const gameId = (e.currentTarget as HTMLElement).dataset.gameId;
                if (gameId) {
                    // Update active state
                    this.elements.gameList?.querySelectorAll('.game-list-item').forEach(i => {
                        i.classList.remove('active');
                    });
                    (e.currentTarget as HTMLElement).classList.add('active');

                    // Trigger callback
                    if (this.onGameSelect) {
                        this.onGameSelect(gameId);
                    }

                    // Close panel
                    this.closeGameSearch();
                }
            });
        });
    }

    public setActiveGame(gameId: string): void {
        this.elements.gameList?.querySelectorAll('.game-list-item').forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-game-id') === gameId);
        });
    }
}

export default GameSearch;