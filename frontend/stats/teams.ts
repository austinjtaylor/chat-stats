// Team statistics page functionality - TypeScript version

import type { TeamSeasonStats, SortConfig, StatsFilter } from '../types/models';
import type { TeamStatsResponse } from '../types/api';
import { initializeTableTooltips, teamColumnDescriptions } from '../src/utils/table-tooltips';

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
    cache: Map<string, { data: any; timestamp: number }>;

    constructor() {
        this.currentSort = { key: 'wins', direction: 'desc' };
        this.filters = {
            season: 'career',
            view: 'total',
            perspective: 'team'
        };
        this.teams = [];
        this.totalTeams = 0;
        this.cache = new Map();

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

        // Table header click handlers for sorting (now instant client-side sorting!)
        const tableHeaders = document.getElementById('tableHeaders');
        if (tableHeaders) {
            tableHeaders.addEventListener('click', (e) => {
                const target = e.target as HTMLElement;
                if (target.tagName === 'TH' && target.hasAttribute('data-sort')) {
                    const sortKey = target.getAttribute('data-sort')!;
                    // Use client-side sorting for instant results
                    this.sortTeamsLocally(sortKey);
                }
            });
        }
    }

    getColumnsForSeason(season: string | number): TeamColumn[] {
        const isOpponent = this.filters.perspective === 'opponent';
        const oppPrefix = isOpponent ? 'Opp\n' : '';
        const seasonNum = parseInt(String(season));

        // Core columns available for all years
        const coreColumns: TeamColumn[] = [
            { key: 'name', label: 'Team', sortable: true },
            { key: 'games_played', label: 'G', sortable: true },
            { key: 'wins', label: 'W', sortable: true },
            { key: 'losses', label: 'L', sortable: true },
            { key: 'scores', label: 'S', sortable: true },
            { key: 'scores_against', label: 'SA', sortable: true }
        ];

        // Completion stats available from 2013+
        const completionColumns: TeamColumn[] = [
            { key: 'completions', label: `${oppPrefix}C`, sortable: true },
            { key: 'turnovers', label: `${oppPrefix}T`, sortable: true },
            { key: 'completion_percentage', label: `${oppPrefix}C %`, sortable: true }
        ];

        // Possession stats available from 2014+
        const advancedColumns: TeamColumn[] = [
            { key: 'hold_percentage', label: `${oppPrefix}HLD %`, sortable: true },
            { key: 'o_line_conversion', label: `${oppPrefix}OLC %`, sortable: true },
            { key: 'blocks', label: `${oppPrefix}B`, sortable: true },
            { key: 'break_percentage', label: `${oppPrefix}BRK %`, sortable: true },
            { key: 'd_line_conversion', label: `${oppPrefix}DLC %`, sortable: true }
        ];

        const columns = [...coreColumns];

        // Add C, T, C% for 2013+
        if (seasonNum >= 2013) {
            columns.push(...completionColumns);
        }

        // Add H and H% after C% for 2020+
        if (seasonNum >= 2020) {
            columns.push(
                { key: 'hucks_completed', label: `${oppPrefix}H`, sortable: true },
                { key: 'huck_percentage', label: `${oppPrefix}H %`, sortable: true }
            );
        }

        // Add possession stats for 2014+ (HLD%, OLC%, B, BRK%, DLC%)
        if (seasonNum >= 2014) {
            columns.push(...advancedColumns);
        }

        // Add RZC% at the end for 2020+
        if (seasonNum >= 2020) {
            columns.push({ key: 'red_zone_conversion', label: `${oppPrefix}RZC %`, sortable: true });
        }

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
            th.innerHTML = col.label.replace(/\n/g, '<br>');
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

        // Initialize tooltips for the headers
        setTimeout(() => {
            initializeTableTooltips('teamsTable', teamColumnDescriptions);
        }, 0);
    }

    sortTeamsLocally(sortKey: string, toggleDirection: boolean = true): void {
        // Toggle sort direction if same column and toggleDirection is true
        let direction: 'asc' | 'desc' = 'desc';
        if (toggleDirection && this.currentSort.key === sortKey) {
            direction = this.currentSort.direction === 'desc' ? 'asc' : 'desc';
        } else if (!toggleDirection) {
            // Keep current direction when not toggling
            direction = this.currentSort.direction;
        }

        // Update sort state
        this.currentSort = { key: sortKey, direction };

        // Sort the teams array in-place
        this.teams.sort((a, b) => {
            let aVal = a[sortKey as keyof TeamSeasonStats];
            let bVal = b[sortKey as keyof TeamSeasonStats];

            // Handle nulls
            if (aVal === null || aVal === undefined) aVal = 0;
            if (bVal === null || bVal === undefined) bVal = 0;

            // String comparison for team name
            if (sortKey === 'name') {
                const aStr = String(aVal);
                const bStr = String(bVal);
                return direction === 'desc' ? bStr.localeCompare(aStr) : aStr.localeCompare(bStr);
            }

            // Numeric comparison
            const aNum = Number(aVal);
            const bNum = Number(bVal);
            return direction === 'desc' ? bNum - aNum : aNum - bNum;
        });

        // Update the UI
        this.renderTableHeaders();
        this.renderTeamsTable();
    }

    async loadTeamStats(): Promise<void> {
        try {
            // OPTIMIZED: Cache key excludes sort parameters (sorting is client-side now)
            const cacheKey = JSON.stringify({
                season: this.filters.season,
                view: this.filters.view,
                perspective: this.filters.perspective
            });

            // Check cache (5 minute TTL)
            const cached = this.cache.get(cacheKey);
            if (cached && Date.now() - cached.timestamp < 5 * 60 * 1000) {
                this.teams = cached.data.teams || [];
                this.totalTeams = cached.data.total || 0;
                this.sortTeamsLocally(this.currentSort.key, false);  // Apply current sort without toggling
                this.updateTeamCount();
                return;
            }

            window.ufaStats.showLoading('#teamsTableBody', 'Loading team statistics...');

            // OPTIMIZED: Don't send sort/order params (backend ignores them anyway)
            const response = await window.ufaStats.fetchData<TeamStatsResponse>('/teams/stats', {
                season: this.filters.season,
                view: this.filters.view,
                perspective: this.filters.perspective
            });

            if (response && response.teams) {
                this.teams = response.teams;
                this.totalTeams = response.total || response.teams.length || 0;

                // Store in cache
                this.cache.set(cacheKey, {
                    data: response,
                    timestamp: Date.now()
                });

                // Apply client-side sorting without toggling
                this.sortTeamsLocally(this.currentSort.key, false);
            } else {
                this.teams = [];
                this.totalTeams = 0;
                this.renderTeamsTable();
            }

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