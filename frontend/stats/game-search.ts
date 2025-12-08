/**
 * Game Search Component - Handles game selection panel
 */

import { statsAPI } from '../src/api/client';
import { MultiSelect } from './components/multi-select';
import type { MultiSelectOption } from './components/multi-select';

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

    // MultiSelect instance for team filter (year filter is fire-and-forget)
    private teamMultiSelect: MultiSelect | null = null;

    // DOM elements
    private elements = {
        gameSearchIcon: null as HTMLElement | null,
        gameSelectionPanel: null as HTMLElement | null,
        closePanel: null as HTMLElement | null,
        yearFilter: null as HTMLElement | null,
        teamFilter: null as HTMLElement | null,
        gameList: null as HTMLElement | null,
    };

    // Callbacks
    private onGameSelect: ((gameId: string) => void) | null = null;

    constructor() {
        this.initializeElements();
        this.initializeYearMultiSelect();
        this.initializeTeamMultiSelect();
        this.attachEventListeners();
    }

    private initializeYearMultiSelect(): void {
        const yearOptions: MultiSelectOption[] = [
            { value: 2025, label: '2025' },
            { value: 2024, label: '2024' },
            { value: 2023, label: '2023' },
            { value: 2022, label: '2022' },
            { value: 2021, label: '2021' },
            { value: 2020, label: '2020' },
            { value: 2019, label: '2019' },
            { value: 2018, label: '2018' },
            { value: 2017, label: '2017' },
            { value: 2016, label: '2016' },
            { value: 2015, label: '2015' },
            { value: 2014, label: '2014' },
            { value: 2013, label: '2013' },
            { value: 2012, label: '2012' }
        ];

        // Year filter is fire-and-forget - no need to store reference
        new MultiSelect({
            containerId: 'yearFilter',
            options: yearOptions,
            selectedValues: [2025],  // Default to 2025
            placeholder: 'Select year...',
            allowSelectAll: false,
            searchable: false,
            exclusiveMode: true,  // Single-select mode
            onChange: (selected) => this.handleYearChange(selected)
        });
    }

    private initializeTeamMultiSelect(): void {
        const teamOptions: MultiSelectOption[] = [
            { value: 'all', label: 'All' }
        ];

        this.teamMultiSelect = new MultiSelect({
            containerId: 'teamFilter',
            options: teamOptions,
            selectedValues: ['all'],
            placeholder: 'Select team...',
            allowSelectAll: false,
            searchable: false,
            exclusiveMode: true,  // Single-select mode
            onChange: (selected) => this.handleTeamChange(selected)
        });
    }

    private handleYearChange(selected: (string | number)[]): void {
        const value = selected[0];
        this.currentYear = typeof value === 'number' ? value : parseInt(String(value));
        this.loadTeams();
        this.loadGamesList();
    }

    private handleTeamChange(selected: (string | number)[]): void {
        const value = selected[0];
        this.currentTeamFilter = String(value);
        this.loadGamesList();
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

        // Close when clicking outside the iframe (parent document)
        window.addEventListener('blur', () => {
            const panel = this.elements.gameSelectionPanel;
            if (panel && panel.classList.contains('active')) {
                this.closeGameSearch();
            }
        });

        // Filter changes are now handled by MultiSelect in initializeYearMultiSelect() and initializeTeamMultiSelect()
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
            this.teams = await statsAPI.getTeams(this.currentYear);

            if (this.teamMultiSelect) {
                const teamOptions: MultiSelectOption[] = [
                    { value: 'all', label: 'All' }
                ];

                this.teams.forEach(team => {
                    teamOptions.push({
                        value: team.team_id,
                        label: team.name
                    });
                });

                // Check if current selection still exists in new team list
                const teamExists = this.teams.some(team => team.team_id === this.currentTeamFilter);
                if (!teamExists && this.currentTeamFilter !== 'all') {
                    this.currentTeamFilter = 'all';
                }

                this.teamMultiSelect.updateOptions(teamOptions);
                this.teamMultiSelect.setSelected([this.currentTeamFilter]);
            }
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    public async loadGamesList(): Promise<void> {
        try {
            const params: any = {
                limit: 500,
                year: this.currentYear
            };

            if (this.currentTeamFilter !== 'all') {
                params.team_id = this.currentTeamFilter;
            }

            const data = await statsAPI.getGamesList(params);

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