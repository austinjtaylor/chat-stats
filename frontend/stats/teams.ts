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
    savedTotalSort: SortConfig;  // Saved sort for Total view
    filters: TeamFilters;
    teams: TeamSeasonStats[];
    totalTeams: number;
    cache: Map<string, { data: any; timestamp: number }>;

    constructor() {
        this.currentSort = { key: 'wins', direction: 'desc' };
        this.savedTotalSort = { key: 'wins', direction: 'desc' };
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

                const newView = target.dataset.view as 'total' | 'per-game';

                // Save/restore sort based on view change
                if (newView === 'per-game' && this.filters.view === 'total') {
                    // Switching to Per Game: save current sort and use alphabetical
                    this.savedTotalSort = { ...this.currentSort };
                    this.currentSort = { key: 'name', direction: 'asc' };
                } else if (newView === 'total' && this.filters.view === 'per-game') {
                    // Switching back to Total: restore saved sort
                    this.currentSort = { ...this.savedTotalSort };
                }

                this.filters.view = newView;
                this.renderTableHeaders();  // Re-render headers for new column set
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
        // For "All" mode (career), show all available columns
        const effectiveSeason = isNaN(seasonNum) ? 9999 : seasonNum;
        const isPerGame = this.filters.view === 'per-game';

        // Core columns available for all years
        const columns: TeamColumn[] = [
            { key: 'name', label: 'Team', sortable: true },
            { key: 'games_played', label: 'G', sortable: true },
            { key: 'wins', label: 'W', sortable: true },
            { key: 'losses', label: 'L', sortable: true },
            { key: 'scores', label: 'S', sortable: true },
            { key: 'scores_against', label: 'SA', sortable: true }
        ];

        // Add C, T for 2013+
        if (effectiveSeason >= 2013) {
            columns.push(
                { key: 'completions', label: `${oppPrefix}C`, sortable: true },
                { key: 'turnovers', label: `${oppPrefix}T`, sortable: true }
            );
            // Total view: add C%
            if (!isPerGame) {
                columns.push({ key: 'completion_percentage', label: `${oppPrefix}C %`, sortable: true });
            }
        }

        // Add H for 2020+
        if (effectiveSeason >= 2020) {
            columns.push({ key: 'hucks_completed', label: `${oppPrefix}H`, sortable: true });
            if (isPerGame) {
                // Per Game view: add HT
                columns.push({ key: 'huck_turnovers', label: `${oppPrefix}HT`, sortable: true });
            } else {
                // Total view: add H%
                columns.push({ key: 'huck_percentage', label: `${oppPrefix}H %`, sortable: true });
            }
        }

        // Add possession stats for 2014+
        if (effectiveSeason >= 2014) {
            if (isPerGame) {
                // Per Game view: HLD (raw count), B, BRK (raw count)
                columns.push(
                    { key: 'o_line_scores', label: `${oppPrefix}HLD`, sortable: true },
                    { key: 'blocks', label: `${oppPrefix}B`, sortable: true },
                    { key: 'd_line_scores', label: `${oppPrefix}BRK`, sortable: true }
                );
            } else {
                // Total view: HLD%, OLC%, B, BRK%, DLC%
                columns.push(
                    { key: 'hold_percentage', label: `${oppPrefix}HLD %`, sortable: true },
                    { key: 'o_line_conversion', label: `${oppPrefix}OLC %`, sortable: true },
                    { key: 'blocks', label: `${oppPrefix}B`, sortable: true },
                    { key: 'break_percentage', label: `${oppPrefix}BRK %`, sortable: true },
                    { key: 'd_line_conversion', label: `${oppPrefix}DLC %`, sortable: true }
                );
            }
        }

        // Add RZC% at the end for 2020+ (Total view only)
        if (!isPerGame && effectiveSeason >= 2020) {
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
                    case 'wins':
                        // Per Game view: show win ratio
                        if (this.filters.view === 'per-game' && team.games_played > 0) {
                            const ratio = team.wins / team.games_played;
                            return `<td class="numeric">${ratio.toFixed(2)}</td>`;
                        }
                        return `<td class="numeric">${this.formatValue(team.wins || 0)}</td>`;
                    case 'losses':
                        // Per Game view: show loss ratio
                        if (this.filters.view === 'per-game' && team.games_played > 0) {
                            const ratio = team.losses / team.games_played;
                            return `<td class="numeric">${ratio.toFixed(2)}</td>`;
                        }
                        return `<td class="numeric">${this.formatValue(team.losses || 0)}</td>`;
                    case 'huck_turnovers':
                        // Calculate HT = hucks_attempted - hucks_completed
                        // Show "-" if huck stats not available
                        if (team.hucks_attempted === null || team.hucks_attempted === undefined ||
                            team.hucks_completed === null || team.hucks_completed === undefined) {
                            return `<td class="numeric">-</td>`;
                        }
                        const ha = team.hucks_attempted as number;
                        const hc = team.hucks_completed as number;
                        return `<td class="numeric">${this.formatValue(Math.max(0, ha - hc))}</td>`;
                    case 'completion_percentage':
                    case 'huck_percentage':
                    case 'hold_percentage':
                    case 'o_line_conversion':
                    case 'break_percentage':
                    case 'd_line_conversion':
                    case 'red_zone_conversion':
                        return `<td class="numeric">${this.formatPercentage(team[col.key as keyof TeamSeasonStats] as number)}</td>`;
                    default:
                        // Pass null/undefined through to formatValue to show "-"
                        const val = team[col.key as keyof TeamSeasonStats];
                        return `<td class="numeric">${this.formatValue(val)}</td>`;
                }
            });

            return `<tr>${cells.join('')}</tr>`;
        }).join('');
    }

    formatValue(value: any): string {
        if (value === null || value === undefined) return '-';
        const num = parseFloat(String(value));
        if (isNaN(num)) return '-';

        // Format large numbers with commas (for Total view)
        if (num >= 1000) {
            return Math.round(num).toLocaleString();
        }

        // For per-game view, round to 1 decimal place (nearest tenth)
        if (this.filters.view === 'per-game') {
            // Check if it's a decimal number
            if (num % 1 !== 0) {
                return num.toFixed(1);
            }
        }

        // For integers or total view, show as-is
        return Math.round(num * 100) / 100 + '';  // Round to avoid floating point issues
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