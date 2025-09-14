class TeamStats {
    constructor() {
        this.currentSort = { key: 'wins', direction: 'desc' };
        this.filters = {
            season: '2025',
            view: 'total',  // 'total' or 'per-game'
            perspective: 'team'  // 'team' or 'opponent'
        };
        this.teams = [];
        this.totalTeams = 0;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.renderTableHeaders();
        await this.loadTeamStats();
    }

    setupEventListeners() {
        // Season filter
        document.getElementById('seasonFilter').addEventListener('change', (e) => {
            this.filters.season = e.target.value;
            this.renderTableHeaders(); // Re-render headers for the new season
            this.loadTeamStats();
        });

        // View toggle (Total/Per Game)
        document.querySelectorAll('[data-view]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Update active state within the view tabs only
                e.target.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                
                this.filters.view = e.target.dataset.view;
                this.loadTeamStats();
            });
        });

        // Perspective toggle (Team/Opponent)
        document.querySelectorAll('[data-perspective]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Update active state within the perspective tabs only
                e.target.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                
                this.filters.perspective = e.target.dataset.perspective;
                this.renderTableHeaders(); // Re-render headers to show Opp prefix
                this.loadTeamStats();
            });
        });

        // Table header click handlers for sorting
        document.getElementById('tableHeaders').addEventListener('click', (e) => {
            if (e.target.tagName === 'TH' && e.target.hasAttribute('data-sort')) {
                const sortKey = e.target.getAttribute('data-sort');
                this.currentSort = window.ufaStats.handleTableSort(
                    document.getElementById('teamsTable'),
                    sortKey,
                    this.currentSort
                );
                this.loadTeamStats();
            }
        });
    }

    getColumnsForSeason(season) {
        const isOpponent = this.filters.perspective === 'opponent';
        const oppPrefix = isOpponent ? 'Opp ' : '';
        
        // Base columns available for all years
        const baseColumns = [
            { key: 'name', label: 'Team', sortable: true },
            { key: 'games_played', label: 'G', sortable: true },
            { key: 'wins', label: 'W', sortable: true },
            { key: 'losses', label: 'L', sortable: true },
            { key: 'scores', label: isOpponent ? 'Opp S' : 'S', sortable: true },
            { key: 'scores_against', label: isOpponent ? 'Opp SA' : 'SA', sortable: true },
            { key: 'completions', label: `${oppPrefix}C`, sortable: true },
            { key: 'turnovers', label: `${oppPrefix}T`, sortable: true },
            { key: 'completion_percentage', label: `${oppPrefix}CMP %`, sortable: true }
        ];

        // Advanced stats columns
        const advancedColumns = [
            { key: 'hucks_completed', label: `${oppPrefix}H`, sortable: true },
            { key: 'huck_percentage', label: `${oppPrefix}Huck %`, sortable: true },
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

    renderTableHeaders() {
        const headerRow = document.getElementById('tableHeaders');
        
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

    async loadTeamStats() {
        try {
            window.ufaStats.showLoading('#teamsTableBody', 'Loading team statistics...');
            
            const response = await window.ufaStats.fetchData('/teams/stats', {
                season: this.filters.season,
                view: this.filters.view,
                perspective: this.filters.perspective,
                sort: this.currentSort.key,
                order: this.currentSort.direction
            });

            if (response && response.teams) {
                this.teams = response.teams;
                this.totalTeams = response.total || 0;
            } else {
                this.teams = [];
                this.totalTeams = 0;
            }

            this.renderTeamsTable();
            this.updateTeamCount();
            
        } catch (error) {
            console.error('Failed to load team stats:', error);
            document.getElementById('teamsTableBody').innerHTML = 
                '<tr><td colspan="18" class="error">Failed to load team statistics</td></tr>';
        }
    }

    renderTeamsTable() {
        const tbody = document.getElementById('teamsTableBody');
        
        if (this.teams.length === 0) {
            tbody.innerHTML = '<tr><td colspan="18" class="no-data">No teams found</td></tr>';
            return;
        }

        // Get columns for current season to match headers
        const columns = this.getColumnsForSeason(this.filters.season);
        
        tbody.innerHTML = this.teams.map((team, index) => {
            const cells = columns.map(col => {
                let value;
                
                switch(col.key) {
                    case 'name':
                        return `<td class="team-name">${team.name || team.full_name}</td>`;
                    case 'completion_percentage':
                    case 'huck_percentage':
                    case 'hold_percentage':
                    case 'o_line_conversion':
                    case 'break_percentage':
                    case 'd_line_conversion':
                    case 'red_zone_conversion':
                        return `<td class="numeric">${this.formatPercentage(team[col.key])}</td>`;
                    case 'wins':
                        return `<td class="numeric">${this.formatValue(team[col.key] || 0)}</td>`;
                    default:
                        return `<td class="numeric">${this.formatValue(team[col.key] || 0)}</td>`;
                }
            });
            
            return `<tr>${cells.join('')}</tr>`;
        }).join('');
    }

    formatValue(value) {
        if (value === null || value === undefined) return '-';
        const num = parseFloat(value);
        if (isNaN(num)) return '-';
        
        // Format large numbers with commas
        if (num >= 1000) {
            return num.toLocaleString();
        }
        
        return num.toString();
    }

    formatPercentage(value) {
        if (value === null || value === undefined || isNaN(value)) return '-';
        return `${parseFloat(value).toFixed(1)}%`;
    }

    updateTeamCount() {
        const countElement = document.getElementById('teamCount');
        if (countElement) {
            countElement.textContent = this.totalTeams.toLocaleString();
        }
    }

    // Remove the addPerspectiveToggle method as it's no longer needed
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.ufaStats) {
        const teamStats = new TeamStats();
    } else {
        // Wait for shared.js to load
        setTimeout(() => {
            const teamStats = new TeamStats();
        }, 100);
    }
});