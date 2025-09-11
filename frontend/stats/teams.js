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
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Update active state
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                
                this.filters.view = e.target.dataset.view;
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
        // Base columns available for all years
        const baseColumns = [
            { key: 'name', label: 'Team', sortable: true },
            { key: 'games_played', label: 'G', sortable: true },
            { key: 'wins', label: 'W', sortable: true },
            { key: 'losses', label: 'L', sortable: true },
            { key: 'scores', label: 'S', sortable: true },
            { key: 'scores_against', label: 'SA', sortable: true },
            { key: 'completions', label: 'C', sortable: true },
            { key: 'turnovers', label: 'T', sortable: true },
            { key: 'completion_percentage', label: 'CMP %', sortable: true }
        ];

        // Advanced stats columns
        const advancedColumns = [
            { key: 'hucks_completed', label: 'H', sortable: true },
            { key: 'huck_percentage', label: 'Huck %', sortable: true },
            { key: 'hold_percentage', label: 'HLD %', sortable: true },
            { key: 'o_line_conversion', label: 'OLC %', sortable: true },
            { key: 'blocks', label: 'B', sortable: true },
            { key: 'break_percentage', label: 'BRK %', sortable: true },
            { key: 'd_line_conversion', label: 'DLC %', sortable: true },
            { key: 'red_zone_conversion', label: 'RZC %', sortable: true }
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
                        // Add trophy icon for best record
                        const isLeader = index === 0 && this.currentSort.key === 'wins' && this.currentSort.direction === 'desc';
                        const trophy = isLeader ? '🏆 ' : '';
                        return `<td class="numeric">${trophy}${this.formatValue(team[col.key] || 0)}</td>`;
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

    // Add method to toggle perspective (Team/Opponent)
    addPerspectiveToggle() {
        const filtersRow = document.querySelector('.filters-row');
        if (filtersRow && !document.getElementById('perspectiveToggle')) {
            const perspectiveGroup = document.createElement('div');
            perspectiveGroup.className = 'filter-group';
            perspectiveGroup.innerHTML = `
                <label>Perspective</label>
                <div class="view-tabs" id="perspectiveToggle">
                    <button class="tab-btn active" data-perspective="team">Team</button>
                    <button class="tab-btn" data-perspective="opponent">Opponent</button>
                </div>
            `;
            filtersRow.appendChild(perspectiveGroup);

            // Add event listeners for perspective toggle
            perspectiveGroup.querySelectorAll('.tab-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    // Update active state
                    perspectiveGroup.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    e.target.classList.add('active');
                    
                    this.filters.perspective = e.target.dataset.perspective;
                    this.loadTeamStats();
                });
            });
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.ufaStats) {
        const teamStats = new TeamStats();
        teamStats.addPerspectiveToggle(); // Add the perspective toggle
    } else {
        // Wait for shared.js to load
        setTimeout(() => {
            const teamStats = new TeamStats();
            teamStats.addPerspectiveToggle(); // Add the perspective toggle
        }, 100);
    }
});