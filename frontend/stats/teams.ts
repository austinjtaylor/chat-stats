// Team statistics page functionality - TypeScript version

import type { TeamSeasonStats, SortConfig, StatsFilter } from '../types/models';
import type { TeamStatsResponse } from '../types/api';

interface TeamColumn {
    key: string;
    label: string;
    sortable: boolean;
}

interface TeamFilters extends StatsFilter {
    season: string | number;
    view: 'total' | 'per-game';
    perspective: 'team' | 'opponent';
}

class TeamStats {
    currentSort: SortConfig;
    filters: TeamFilters;
    teams: TeamSeasonStats[];
    totalTeams: number;

    constructor() {
        this.currentSort = { key: 'wins', direction: 'desc' };
        this.filters = {
            season: '2025',
            view: 'total',
            perspective: 'team'
        };
        this.teams = [];
        this.totalTeams = 0;

        this.init();
    }

    async init(): Promise<void> {
        this.setupEventListeners();
        this.renderTableHeaders();
        await this.loadTeamStats();
    }

    setupEventListeners(): void {
        // Season filter
        const seasonFilter = document.getElementById('seasonFilter') as HTMLSelectElement;
        if (seasonFilter) {
            seasonFilter.addEventListener('change', (e) => {
                this.filters.season = (e.target as HTMLSelectElement).value;
                this.renderTableHeaders(); // Re-render headers for the new season
                this.loadTeamStats();
            });
        }

        // View toggle (Total/Per Game)
        document.querySelectorAll('[data-view]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.target as HTMLElement;
                const parent = target.parentElement;

                // Update active state within the view tabs only
                if (parent) {
                    parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                }
                target.classList.add('active');

                this.filters.view = target.dataset.view as 'total' | 'per-game';
                this.loadTeamStats();
            });
        });

        // Perspective toggle (Team/Opponent)
        document.querySelectorAll('[data-perspective]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.target as HTMLElement;
                const parent = target.parentElement;

                // Update active state within the perspective tabs only
                if (parent) {
                    parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                }
                target.classList.add('active');

                this.filters.perspective = target.dataset.perspective as 'team' | 'opponent';
                this.renderTableHeaders(); // Re-render headers to show Opp prefix
                this.loadTeamStats();
            });
        });

        // Table header click handlers for sorting
        const tableHeaders = document.getElementById('tableHeaders');
        if (tableHeaders) {
            tableHeaders.addEventListener('click', (e) => {
                const target = e.target as HTMLElement;
                if (target.tagName === 'TH' && target.hasAttribute('data-sort')) {
                    const sortKey = target.getAttribute('data-sort')!;
                    this.currentSort = window.ufaStats.handleTableSort(
                        document.getElementById('teamsTable')!,
                        sortKey,
                        this.currentSort
                    );
                    this.loadTeamStats();
                }
            });
        }
    }

    getColumnsForSeason(_season: string | number): TeamColumn[] {
        const isOpponent = this.filters.perspective === 'opponent';
        const oppPrefix = isOpponent ? 'Opp ' : '';

        // Base columns available for all years
        const baseColumns: TeamColumn[] = [
            { key: 'name', label: 'Team', sortable: true },
            { key: 'games_played', label: 'G', sortable: true },
            { key: 'wins', label: 'W', sortable: true },
            { key: 'losses', label: 'L', sortable: true },
            { key: 'scores', label: isOpponent ? 'Opp S' : 'S', sortable: true },
            { key: 'scores_against', label: isOpponent ? 'Opp SA' : 'SA', sortable: true },
            { key: 'completions', label: `${oppPrefix}C`, sortable: true },
            { key: 'turnovers', label: `${oppPrefix}T`, sortable: true },
            { key: 'completion_percentage', label: `${oppPrefix}C%`, sortable: true }
        ];

        // Advanced stats columns
        const advancedColumns: TeamColumn[] = [
            { key: 'hucks_completed', label: `${oppPrefix}H`, sortable: true },
            { key: 'huck_percentage', label: `${oppPrefix}H%`, sortable: true },
            { key: 'hold_percentage', label: `${oppPrefix}HLD %`, sortable: true },
            { key: 'o_line_conversion', label: `${oppPrefix}OLC %`, sortable: true },
            { key: 'blocks', label: `${oppPrefix}B`, sortable: true },
            { key: 'break_percentage', label: `${oppPrefix}BRK %`, sortable: true },
            { key: 'd_line_conversion', label: `${oppPrefix}DLC %`, sortable: true },
            { key: 'red_zone_conversion', label: `${oppPrefix}RZC %`, sortable: true }
        ];

        // For now, show all columns for all seasons
        // In the future, we could filter based on data availability
        return [...baseColumns, ...advancedColumns];
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
            th.className = col.key === 'name' ? 'team-name' : 'numeric';

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

    async loadTeamStats(): Promise<void> {
        try {
            window.ufaStats.showLoading('#teamsTableBody', 'Loading team statistics...');

            const response = await window.ufaStats.fetchData<TeamStatsResponse>('/teams/stats', {
                season: this.filters.season,
                view: this.filters.view,
                perspective: this.filters.perspective,
                sort: this.currentSort.key,
                order: this.currentSort.direction
            });

            if (response && response.teams) {
                this.teams = response.teams;
                this.totalTeams = response.total || response.teams.length || 0;
            } else {
                this.teams = [];
                this.totalTeams = 0;
            }

            this.renderTeamsTable();
            this.updateTeamCount();

        } catch (error) {
            console.error('Failed to load team stats:', error);
            const tbody = document.getElementById('teamsTableBody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="18" class="error">Failed to load team statistics</td></tr>';
            }
        }
    }

    renderTeamsTable(): void {
        const tbody = document.getElementById('teamsTableBody');
        if (!tbody) return;

        if (this.teams.length === 0) {
            tbody.innerHTML = '<tr><td colspan="18" class="no-data">No teams found</td></tr>';
            return;
        }

        // Get columns for current season to match headers
        const columns = this.getColumnsForSeason(this.filters.season);

        tbody.innerHTML = this.teams.map((team) => {
            const cells = columns.map(col => {
                switch (col.key) {
                    case 'name':
                        return `<td class="team-name">${team.name || ''}</td>`;
                    case 'completion_percentage':
                    case 'huck_percentage':
                    case 'hold_percentage':
                    case 'o_line_conversion':
                    case 'break_percentage':
                    case 'd_line_conversion':
                    case 'red_zone_conversion':
                        return `<td class="numeric">${this.formatPercentage(team[col.key as keyof TeamSeasonStats] as number)}</td>`;
                    case 'wins':
                        return `<td class="numeric">${this.formatValue(team[col.key as keyof TeamSeasonStats] || 0)}</td>`;
                    default:
                        return `<td class="numeric">${this.formatValue(team[col.key as keyof TeamSeasonStats] || 0)}</td>`;
                }
            });

            return `<tr>${cells.join('')}</tr>`;
        }).join('');
    }

    formatValue(value: any): string {
        if (value === null || value === undefined) return '-';
        const num = parseFloat(String(value));
        if (isNaN(num)) return '-';

        // Format large numbers with commas
        if (num >= 1000) {
            return num.toLocaleString();
        }

        return num.toString();
    }

    formatPercentage(value: number | null | undefined): string {
        if (value === null || value === undefined || isNaN(value)) return '-';
        return parseFloat(String(value)).toFixed(1);
    }

    updateTeamCount(): void {
        const countElement = document.getElementById('teamCount');
        if (countElement) {
            countElement.textContent = this.totalTeams.toLocaleString();
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.ufaStats) {
        new TeamStats();
    } else {
        // Wait for shared.js to load
        setTimeout(() => {
            new TeamStats();
        }, 100);
    }
});

// Export for module usage
export { TeamStats };
export default TeamStats;