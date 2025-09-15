// Player statistics page functionality - TypeScript version

import type { PlayerSeasonStats, SortConfig, StatsFilter } from '../types/models';
import type { StatsResponse, PlayerStatsResponse } from '../types/api';

interface TeamInfo {
    id: string | number;
    name: string;
    is_current?: boolean;
    last_year?: number | string;
}

interface PlayerColumn {
    key: string;
    label: string;
    sortable: boolean;
}

interface PlayerFilters extends StatsFilter {
    season: string | number;
    per: 'total' | 'per-game';
    team: string;
}

class PlayerStats {
    currentPage: number;
    pageSize: number;
    currentSort: SortConfig;
    filters: PlayerFilters;
    players: PlayerSeasonStats[];
    totalPages: number;
    totalPlayers: number;
    teams: TeamInfo[];

    constructor() {
        this.currentPage = 1;
        this.pageSize = 20;
        this.currentSort = { key: 'calculated_plus_minus', direction: 'desc' };
        this.filters = {
            season: 'career',
            per: 'total',
            team: 'all'
        };
        this.players = [];
        this.totalPages = 0;
        this.totalPlayers = 0;
        this.teams = [];

        this.init();
    }

    async init(): Promise<void> {
        await this.loadTeams();
        this.setupEventListeners();
        this.renderTableHeaders();
        await this.loadPlayerStats();
    }

    async loadTeams(): Promise<void> {
        try {
            const data = await window.ufaStats.fetchData<StatsResponse>('/stats');
            if (data.team_standings) {
                this.teams = data.team_standings.map(team => ({
                    id: team.team_id || team.team_name || '',
                    name: team.team_name || '',
                    is_current: team.is_current,
                    last_year: team.last_year
                }));
                this.populateTeamFilter();
            }
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    populateTeamFilter(): void {
        const teamFilter = document.getElementById('teamFilter') as HTMLSelectElement;
        if (!teamFilter) return;

        const currentValue = teamFilter.value;

        // Clear existing options except "All"
        teamFilter.innerHTML = '<option value="all">All</option>';

        // Separate teams into current and historical
        const currentTeams = this.teams.filter(team => team.is_current !== false);
        const historicalTeams = this.teams.filter(team => team.is_current === false);

        // Add current teams
        currentTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = String(team.id);
            option.textContent = team.name;
            teamFilter.appendChild(option);
        });

        // Add separator if there are historical teams
        if (historicalTeams.length > 0 && currentTeams.length > 0) {
            const separator = document.createElement('option');
            separator.disabled = true;
            separator.textContent = '── Historical Teams ──';
            teamFilter.appendChild(separator);
        }

        // Add historical teams
        historicalTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = String(team.id);
            option.textContent = `${team.name} (${team.last_year || 'historical'})`;
            teamFilter.appendChild(option);
        });

        // Restore previous selection if it exists
        if (currentValue && [...teamFilter.options].find(opt => opt.value === currentValue)) {
            teamFilter.value = currentValue;
        }
    }

    setupEventListeners(): void {
        // Filter change handlers
        const seasonFilter = document.getElementById('seasonFilter') as HTMLSelectElement;
        if (seasonFilter) {
            seasonFilter.addEventListener('change', (e) => {
                this.filters.season = (e.target as HTMLSelectElement).value;
                this.currentPage = 1;
                this.renderTableHeaders(); // Re-render headers for the new season
                this.loadPlayerStats();
            });
        }

        const perFilter = document.getElementById('perFilter') as HTMLSelectElement;
        if (perFilter) {
            perFilter.addEventListener('change', (e) => {
                this.filters.per = (e.target as HTMLSelectElement).value as 'total' | 'per-game';
                this.currentPage = 1;
                this.loadPlayerStats();
            });
        }

        const teamFilter = document.getElementById('teamFilter') as HTMLSelectElement;
        if (teamFilter) {
            teamFilter.addEventListener('change', (e) => {
                this.filters.team = (e.target as HTMLSelectElement).value;
                this.currentPage = 1;
                this.loadPlayerStats();
            });
        }

        // Table header click handlers for sorting
        const tableHeaders = document.getElementById('tableHeaders');
        if (tableHeaders) {
            tableHeaders.addEventListener('click', (e) => {
                const target = e.target as HTMLElement;
                if (target.tagName === 'TH' && target.hasAttribute('data-sort')) {
                    const sortKey = target.getAttribute('data-sort')!;
                    this.currentSort = window.ufaStats.handleTableSort(
                        document.getElementById('playersTable')!,
                        sortKey,
                        this.currentSort
                    );
                    this.currentPage = 1;
                    this.loadPlayerStats();
                }
            });
        }
    }

    getColumnsForSeason(season: string | number): PlayerColumn[] {
        // Base columns available for all years
        const baseColumns: PlayerColumn[] = [
            { key: 'full_name', label: 'Player', sortable: true },
            { key: 'games_played', label: 'G', sortable: true },
            { key: 'total_points_played', label: 'PP', sortable: true },
            { key: 'possessions', label: 'POS', sortable: true },
            { key: 'score_total', label: 'SCR', sortable: true },
            { key: 'total_assists', label: 'AST', sortable: true },
            { key: 'total_goals', label: 'GLS', sortable: true },
            { key: 'total_blocks', label: 'BLK', sortable: true },
            { key: 'calculated_plus_minus', label: '+/-', sortable: true },
            { key: 'total_completions', label: 'Cmp', sortable: true },
            { key: 'completion_percentage', label: 'Cmp%', sortable: true }
        ];

        // Advanced stats added in 2021
        const advancedStats2021: PlayerColumn[] = [
            { key: 'total_yards', label: 'Y', sortable: true },
            { key: 'total_yards_thrown', label: 'TY', sortable: true },
            { key: 'total_yards_received', label: 'RY', sortable: true }
        ];

        // OEFF available for all years
        const oeffColumn: PlayerColumn[] = [{ key: 'offensive_efficiency', label: 'OEFF', sortable: true }];

        // Hockey assists available from 2014
        const hockeyAssistColumn: PlayerColumn[] = [{ key: 'total_hockey_assists', label: 'HA', sortable: true }];

        // Other base columns
        const otherBaseColumns: PlayerColumn[] = [
            { key: 'total_throwaways', label: 'T', sortable: true },
            { key: 'total_stalls', label: 'S', sortable: true },
            { key: 'total_drops', label: 'D', sortable: true },
            { key: 'total_callahans', label: 'C', sortable: true }
        ];

        // Huck stats available from 2021
        const huckStats2021: PlayerColumn[] = [
            { key: 'total_hucks_completed', label: 'Hck', sortable: true },
            { key: 'huck_percentage', label: 'Hck%', sortable: true }
        ];

        // Final columns
        const finalColumns: PlayerColumn[] = [
            { key: 'total_pulls', label: 'Pul', sortable: true },
            { key: 'total_o_points_played', label: 'OPP', sortable: true },
            { key: 'total_d_points_played', label: 'DPP', sortable: true },
            { key: 'minutes_played', label: 'MP', sortable: true }
        ];

        // Build column list based on season
        let columns = [...baseColumns];

        // For career stats or 2021+, show all columns
        if (season === 'career' || (season && parseInt(String(season)) >= 2021)) {
            columns.push(...advancedStats2021);
        }

        columns.push(...oeffColumn);

        // Hockey assists available from 2014
        if (season === 'career' || (season && parseInt(String(season)) >= 2014)) {
            columns.push(...hockeyAssistColumn);
        }

        columns.push(...otherBaseColumns);

        // Huck stats from 2021
        if (season === 'career' || (season && parseInt(String(season)) >= 2021)) {
            columns.push(...huckStats2021);
        }

        columns.push(...finalColumns);

        return columns;
    }

    renderTableHeaders(): void {
        const headerRow = document.getElementById('tableHeaders');
        if (!headerRow) return;

        // Get columns based on current season filter
        const columns = this.getColumnsForSeason(this.filters.season);

        headerRow.innerHTML = '';
        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col.label;
            th.className = 'numeric';

            if (col.sortable) {
                th.setAttribute('data-sort', col.key);
                th.classList.add('sortable');

                if (this.currentSort.key === col.key) {
                    th.classList.add(this.currentSort.direction);
                }
            }

            headerRow.appendChild(th);
        });
    }

    async loadPlayerStats(): Promise<void> {
        try {
            window.ufaStats.showLoading('#playersTableBody', 'Loading player statistics...');

            // Use the new dedicated API endpoint
            const response = await window.ufaStats.fetchData<PlayerStatsResponse>('/players/stats', {
                season: this.filters.season,
                team: this.filters.team,
                per: this.filters.per,
                page: this.currentPage,
                per_page: this.pageSize,
                sort: this.currentSort.key,
                order: this.currentSort.direction
            });

            if (response) {
                this.players = response.players || [];
                this.totalPlayers = response.total || 0;
                this.totalPages = response.pages || 0;
            } else {
                this.players = [];
                this.totalPlayers = 0;
                this.totalPages = 0;
            }

            this.renderPlayersTable();
            this.renderPagination();
            this.updatePlayerCount();

        } catch (error) {
            console.error('Failed to load player stats:', error);
            const tbody = document.getElementById('playersTableBody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="26" class="error">Failed to load player statistics</td></tr>';
            }
        }
    }

    renderPlayersTable(): void {
        const tbody = document.getElementById('playersTableBody');
        if (!tbody) return;

        if (this.players.length === 0) {
            tbody.innerHTML = '<tr><td colspan="26" class="no-data">No players found</td></tr>';
            return;
        }

        // Get columns for current season to match headers
        const columns = this.getColumnsForSeason(this.filters.season);

        tbody.innerHTML = this.players.map(player => {
            const cells = columns.map(col => {
                let value: number | string;

                switch (col.key) {
                    case 'full_name':
                        const name = player.player_name || `${player.first_name || ''} ${player.last_name || ''}`.trim();
                        return `<td class="player-name">${name}</td>`;
                    case 'total_points_played':
                        value = (player.o_points_for || 0) + (player.d_points_for || 0);
                        // Round to 1 decimal place to avoid floating point precision issues
                        value = Math.round(value * 10) / 10;
                        return `<td class="numeric">${this.formatValue(value)}</td>`;
                    case 'score_total':
                        value = (player.goals || 0) + (player.assists || 0);
                        // Round to 1 decimal place to avoid floating point precision issues
                        value = Math.round(value * 10) / 10;
                        return `<td class="numeric">${this.formatValue(value)}</td>`;
                    case 'calculated_plus_minus':
                        return `<td class="numeric">${this.formatValue(player[col.key as keyof PlayerSeasonStats] || 0, true)}</td>`;
                    case 'completion_percentage':
                        return `<td class="numeric">${this.formatPercentage(player[col.key as keyof PlayerSeasonStats] as number)}</td>`;
                    case 'huck_percentage':
                        return `<td class="numeric">${this.formatPercentage(this.calculateHuckPercentage(player))}</td>`;
                    default:
                        const fieldValue = player[col.key as keyof PlayerSeasonStats];
                        return `<td class="numeric">${this.formatValue(fieldValue || 0)}</td>`;
                }
            });

            return `<tr>${cells.join('')}</tr>`;
        }).join('');
    }

    calculateHuckPercentage(player: PlayerSeasonStats): number {
        if (!player.hucks_attempted || player.hucks_attempted === 0) return 0;
        return ((player.hucks_completed || 0) / player.hucks_attempted) * 100;
    }

    formatValue(value: any, showSign: boolean = false): string {
        if (value === null || value === undefined) return '-';
        const num = parseFloat(String(value));
        if (isNaN(num)) return '-';

        if (showSign && num > 0) {
            return `+${num}`;
        }
        return num.toString();
    }

    formatPercentage(value: number | null | undefined): string {
        // Use Format utility if available
        if (window.Format && window.Format.percentage) {
            return window.Format.percentage(value, 1);
        }
        if (value === null || value === undefined || isNaN(value)) return '-';
        return `${parseFloat(String(value)).toFixed(1)}%`;
    }

    renderPagination(): void {
        const container = document.getElementById('paginationContainer');
        if (!container) return;

        if (this.totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        const pagination = window.ufaStats.createPagination({
            currentPage: this.currentPage,
            totalPages: this.totalPages,
            onPageChange: (page: number) => {
                this.currentPage = page;
                this.loadPlayerStats();
            }
        });

        container.innerHTML = '';
        container.appendChild(pagination);
    }

    updatePlayerCount(): void {
        const countElement = document.getElementById('playerCount');
        if (countElement) {
            countElement.textContent = window.Format ? window.Format.number(this.totalPlayers) : this.totalPlayers.toLocaleString();
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.ufaStats) {
        new PlayerStats();
    } else {
        // Wait for shared.js to load
        setTimeout(() => new PlayerStats(), 100);
    }
});

// Export for module usage
export { PlayerStats };
export default PlayerStats;