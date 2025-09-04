class PlayerStats {
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

    async init() {
        await this.loadTeams();
        this.setupEventListeners();
        this.renderTableHeaders();
        await this.loadPlayerStats();
    }

    async loadTeams() {
        try {
            const data = await window.ufaStats.fetchData('/stats');
            if (data.team_standings) {
                this.teams = data.team_standings.map(team => ({
                    id: team.team_id || team.name,
                    name: team.full_name || team.name
                }));
                this.populateTeamFilter();
            }
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    populateTeamFilter() {
        const teamFilter = document.getElementById('teamFilter');
        const currentValue = teamFilter.value;
        
        // Clear existing options except "All"
        teamFilter.innerHTML = '<option value="all">All</option>';
        
        // Add team options
        this.teams.forEach(team => {
            const option = document.createElement('option');
            option.value = team.id;
            option.textContent = team.name;
            teamFilter.appendChild(option);
        });
        
        // Restore previous selection if it exists
        if (currentValue && [...teamFilter.options].find(opt => opt.value === currentValue)) {
            teamFilter.value = currentValue;
        }
    }

    setupEventListeners() {
        // Filter change handlers
        document.getElementById('seasonFilter').addEventListener('change', (e) => {
            this.filters.season = e.target.value;
            this.currentPage = 1;
            this.renderTableHeaders(); // Re-render headers for the new season
            this.loadPlayerStats();
        });

        document.getElementById('perFilter').addEventListener('change', (e) => {
            this.filters.per = e.target.value;
            this.currentPage = 1;
            this.loadPlayerStats();
        });

        document.getElementById('teamFilter').addEventListener('change', (e) => {
            this.filters.team = e.target.value;
            this.currentPage = 1;
            this.loadPlayerStats();
        });

        // Table header click handlers for sorting
        document.getElementById('tableHeaders').addEventListener('click', (e) => {
            if (e.target.tagName === 'TH' && e.target.hasAttribute('data-sort')) {
                const sortKey = e.target.getAttribute('data-sort');
                this.currentSort = window.ufaStats.handleTableSort(
                    document.getElementById('playersTable'),
                    sortKey,
                    this.currentSort
                );
                this.currentPage = 1;
                this.loadPlayerStats();
            }
        });
    }

    getColumnsForSeason(season) {
        // Base columns available for all years
        const baseColumns = [
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
        const advancedStats2021 = [
            { key: 'total_yards', label: 'Y', sortable: true },
            { key: 'total_yards_thrown', label: 'TY', sortable: true },
            { key: 'total_yards_received', label: 'RY', sortable: true }
        ];

        // OEFF available for all years
        const oeffColumn = [{ key: 'offensive_efficiency', label: 'OEFF', sortable: true }];

        // Hockey assists available from 2014
        const hockeyAssistColumn = [{ key: 'total_hockey_assists', label: 'HA', sortable: true }];

        // Other base columns
        const otherBaseColumns = [
            { key: 'total_throwaways', label: 'T', sortable: true },
            { key: 'total_stalls', label: 'S', sortable: true },
            { key: 'total_drops', label: 'D', sortable: true },
            { key: 'total_callahans', label: 'C', sortable: true }
        ];

        // Huck stats available from 2021
        const huckStats2021 = [
            { key: 'total_hucks_completed', label: 'Hck', sortable: true },
            { key: 'huck_percentage', label: 'Hck%', sortable: true }
        ];

        // Final columns
        const finalColumns = [
            { key: 'total_pulls', label: 'Pul', sortable: true },
            { key: 'total_o_points_played', label: 'OPP', sortable: true },
            { key: 'total_d_points_played', label: 'DPP', sortable: true },
            { key: 'minutes_played', label: 'MP', sortable: true }
        ];

        // Build column list based on season
        let columns = [...baseColumns];
        
        // For career stats or 2021+, show all columns
        if (season === 'career' || (season && parseInt(season) >= 2021)) {
            columns.push(...advancedStats2021);
        }
        
        columns.push(...oeffColumn);
        
        // Hockey assists available from 2014
        if (season === 'career' || (season && parseInt(season) >= 2014)) {
            columns.push(...hockeyAssistColumn);
        }
        
        columns.push(...otherBaseColumns);
        
        // Huck stats from 2021
        if (season === 'career' || (season && parseInt(season) >= 2021)) {
            columns.push(...huckStats2021);
        }
        
        columns.push(...finalColumns);
        
        return columns;
    }

    renderTableHeaders() {
        const headerRow = document.getElementById('tableHeaders');
        
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

    async loadPlayerStats() {
        try {
            window.ufaStats.showLoading('#playersTableBody', 'Loading player statistics...');
            
            // Use the new dedicated API endpoint
            const response = await window.ufaStats.fetchData('/players/stats', {
                season: this.filters.season,
                team: this.filters.team,
                page: this.currentPage,
                per_page: this.pageSize,
                sort: this.currentSort.key,
                order: this.currentSort.direction
            });

            if (response) {
                this.players = response.players || [];
                this.totalPlayers = response.total || 0;
                this.totalPages = response.total_pages || 0;
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
            document.getElementById('playersTableBody').innerHTML = 
                '<tr><td colspan="26" class="error">Failed to load player statistics</td></tr>';
        }
    }

    async fetchData(endpoint, params = {}, options = {}) {
        try {
            const url = new URL(`${window.ufaStats.apiBase}${endpoint}`);
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined) {
                    url.searchParams.append(key, params[key]);
                }
            });

            const defaultOptions = {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            };

            const response = await fetch(url, { ...defaultOptions, ...options });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    getSortColumn() {
        const columnMapping = {
            'total_goals': 'total_goals',
            'total_assists': 'total_assists',
            'total_blocks': 'total_blocks',
            'calculated_plus_minus': 'calculated_plus_minus',
            'completion_percentage': 'completion_percentage',
            'player_name': 'full_name'
        };
        return columnMapping[this.currentSort.key] || this.currentSort.key;
    }

    getSortValue(player, key) {
        const value = player[key] || player[this.getSortColumn()] || 0;
        return typeof value === 'string' ? value.toLowerCase() : (parseFloat(value) || 0);
    }

    renderPlayersTable() {
        const tbody = document.getElementById('playersTableBody');
        
        if (this.players.length === 0) {
            tbody.innerHTML = '<tr><td colspan="26" class="no-data">No players found</td></tr>';
            return;
        }

        // Get columns for current season to match headers
        const columns = this.getColumnsForSeason(this.filters.season);
        
        tbody.innerHTML = this.players.map(player => {
            const cells = columns.map(col => {
                let value;
                
                switch(col.key) {
                    case 'full_name':
                        return `<td class="player-name">${player.full_name || `${player.first_name || ''} ${player.last_name || ''}`.trim()}</td>`;
                    case 'total_points_played':
                        value = (player.total_o_points_played || 0) + (player.total_d_points_played || 0);
                        return `<td class="numeric">${this.formatValue(value)}</td>`;
                    case 'score_total':
                        value = (player.total_goals || 0) + (player.total_assists || 0);
                        return `<td class="numeric">${this.formatValue(value)}</td>`;
                    case 'calculated_plus_minus':
                        return `<td class="numeric">${this.formatValue(player[col.key] || 0, true)}</td>`;
                    case 'completion_percentage':
                        return `<td class="numeric">${this.formatPercentage(player[col.key])}</td>`;
                    case 'huck_percentage':
                        return `<td class="numeric">${this.formatPercentage(this.calculateHuckPercentage(player))}</td>`;
                    default:
                        return `<td class="numeric">${this.formatValue(player[col.key] || 0)}</td>`;
                }
            });
            
            return `<tr>${cells.join('')}</tr>`;
        }).join('');
    }

    getPlayerGames(player) {
        // Try to calculate from available data or use a default
        return player.games || Math.ceil((player.total_o_points_played + player.total_d_points_played) / 25) || 0;
    }

    calculateHuckPercentage(player) {
        if (!player.total_hucks_attempted || player.total_hucks_attempted === 0) return 0;
        return (player.total_hucks_completed / player.total_hucks_attempted) * 100;
    }

    calculateMinutesPlayed(player) {
        // Estimate based on points played (assuming ~2.5 minutes per point)
        return Math.round((player.total_o_points_played + player.total_d_points_played) * 2.5) || 0;
    }

    formatValue(value, showSign = false) {
        if (value === null || value === undefined) return '-';
        const num = parseFloat(value);
        if (isNaN(num)) return '-';
        
        if (showSign && num > 0) {
            return `+${num}`;
        }
        return num.toString();
    }

    formatPercentage(value) {
        if (value === null || value === undefined || isNaN(value)) return '-';
        return `${parseFloat(value).toFixed(1)}%`;
    }

    renderPagination() {
        const container = document.getElementById('paginationContainer');
        
        if (this.totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        const pagination = window.ufaStats.createPagination(
            this.currentPage,
            this.totalPages,
            (page) => {
                this.currentPage = page;
                this.loadPlayerStats();
            }
        );

        container.innerHTML = '';
        container.appendChild(pagination);
    }

    updatePlayerCount() {
        const countElement = document.getElementById('playerCount');
        if (countElement) {
            countElement.textContent = this.totalPlayers.toLocaleString();
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