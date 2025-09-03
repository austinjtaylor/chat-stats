class UFADashboard {
    constructor() {
        this.apiBase = 'http://localhost:8000/api';
        this.data = {
            stats: null,
            standings: [],
            leaders: [],
            games: []
        };
        this.charts = {};
        this.init();
    }

    async init() {
        await this.loadInitialData();
        this.setupEventListeners();
        this.renderOverview();
        this.renderStandings();
        this.renderLeaders();
        this.renderRecentGames();
        this.renderChart();
    }

    async loadInitialData() {
        try {
            // Load main statistics
            const statsResponse = await fetch(`${this.apiBase}/stats`);
            if (statsResponse.ok) {
                this.data.stats = await statsResponse.json();
            }

            // Load recent games
            const gamesResponse = await fetch(`${this.apiBase}/games/recent`);
            if (gamesResponse.ok) {
                this.data.games = await gamesResponse.json();
            }
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('Failed to load data from server. Make sure the backend is running.');
        }
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshButton').addEventListener('click', () => {
            this.refresh();
        });

        // Search functionality
        document.getElementById('playerSearchButton').addEventListener('click', () => {
            this.searchPlayers();
        });

        document.getElementById('teamSearchButton').addEventListener('click', () => {
            this.searchTeams();
        });

        // Enter key for search
        document.getElementById('playerSearch').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchPlayers();
        });

        document.getElementById('teamSearch').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchTeams();
        });

        // Leader category change
        document.getElementById('leaderCategory').addEventListener('change', (e) => {
            this.renderLeaders(e.target.value);
        });

        // Chart category change
        document.getElementById('chartCategory').addEventListener('change', (e) => {
            this.renderChart(e.target.value);
        });

        // Clear search
        document.getElementById('clearSearch').addEventListener('click', () => {
            this.clearSearch();
        });

        // Load more games
        document.getElementById('loadMoreGames').addEventListener('click', () => {
            this.loadMoreGames();
        });

        // Table sorting
        document.querySelectorAll('[data-sort]').forEach(header => {
            header.addEventListener('click', (e) => {
                const sortBy = e.target.getAttribute('data-sort');
                this.sortTable(e.target.closest('table'), sortBy);
            });
        });
    }

    renderOverview() {
        if (!this.data.stats) return;

        document.getElementById('totalPlayers').textContent = this.data.stats.total_players?.toLocaleString() || '-';
        document.getElementById('totalTeams').textContent = this.data.stats.total_teams?.toLocaleString() || '-';
        document.getElementById('totalGames').textContent = this.data.stats.total_games?.toLocaleString() || '-';
        
        const currentSeason = this.data.stats.seasons?.[0] || '-';
        document.getElementById('currentSeason').textContent = currentSeason;
    }

    renderStandings() {
        const tbody = document.getElementById('standingsBody');
        
        if (!this.data.stats?.team_standings) {
            tbody.innerHTML = '<tr><td colspan="7" class="no-data">No standings data available</td></tr>';
            return;
        }

        const standings = this.data.stats.team_standings.slice(0, 20); // Top 20 teams
        tbody.innerHTML = standings.map(team => `
            <tr>
                <td class="standing">${team.standing}</td>
                <td class="team-name">
                    <div class="team-info">
                        <strong>${team.name}</strong>
                        <span class="team-city">${team.full_name}</span>
                    </div>
                </td>
                <td class="wins">${team.wins}</td>
                <td class="losses">${team.losses}</td>
                <td class="ties">${team.ties || 0}</td>
                <td class="win-percentage">${this.calculateWinPercentage(team.wins, team.losses, team.ties)}</td>
                <td class="division">${team.division_name || '-'}</td>
            </tr>
        `).join('');
    }

    async renderLeaders(category = 'goals') {
        const tbody = document.getElementById('leadersBody');
        const statHeader = document.getElementById('statHeader');
        
        // Update header
        const categoryNames = {
            goals: 'Goals',
            assists: 'Assists', 
            blocks: 'Blocks',
            plus_minus: '+/-',
            completion_percentage: 'Comp %'
        };
        statHeader.textContent = categoryNames[category] || category;

        try {
            // Use current season leaders from stats endpoint
            if (!this.data.stats?.current_season_leaders) {
                tbody.innerHTML = '<tr><td colspan="4" class="no-data">No leaders data available</td></tr>';
                return;
            }

            const leaders = this.data.stats.current_season_leaders
                .sort((a, b) => {
                    const aVal = this.getStatValue(a, category);
                    const bVal = this.getStatValue(b, category);
                    return bVal - aVal;
                })
                .slice(0, 15); // Top 15 players

            tbody.innerHTML = leaders.map((player, index) => `
                <tr>
                    <td class="rank">${index + 1}</td>
                    <td class="player-name">
                        <div class="player-info">
                            <strong>${player.full_name || `${player.first_name} ${player.last_name}`}</strong>
                        </div>
                    </td>
                    <td class="team-name">${player.team_name || player.team_full_name || '-'}</td>
                    <td class="stat-value">${this.formatStatValue(this.getStatValue(player, category), category)}</td>
                </tr>
            `).join('');
        } catch (error) {
            console.error('Failed to render leaders:', error);
            tbody.innerHTML = '<tr><td colspan="4" class="error">Failed to load leaders</td></tr>';
        }
    }

    getStatValue(player, category) {
        const mapping = {
            goals: player.total_goals,
            assists: player.total_assists,
            blocks: player.total_blocks,
            plus_minus: player.calculated_plus_minus,
            completion_percentage: player.completion_percentage
        };
        return mapping[category] || 0;
    }

    formatStatValue(value, category) {
        if (category === 'completion_percentage') {
            return value ? `${value.toFixed(1)}%` : '0.0%';
        }
        return value || 0;
    }

    renderRecentGames() {
        const container = document.getElementById('recentGames');
        
        if (!this.data.games || this.data.games.length === 0) {
            container.innerHTML = '<div class="no-data">No recent games available</div>';
            return;
        }

        const games = this.data.games.slice(0, 10); // Show latest 10 games
        container.innerHTML = games.map(game => `
            <div class="game-card">
                <div class="game-teams">
                    <div class="team away">
                        <span class="team-name">${this.getTeamName(game.away_team_id)}</span>
                        <span class="score">${game.away_score || 0}</span>
                    </div>
                    <div class="vs">@</div>
                    <div class="team home">
                        <span class="team-name">${this.getTeamName(game.home_team_id)}</span>
                        <span class="score">${game.home_score || 0}</span>
                    </div>
                </div>
                <div class="game-info">
                    <div class="game-status">${game.status}</div>
                    <div class="game-date">${this.formatDate(game.start_timestamp)}</div>
                </div>
            </div>
        `).join('');
    }

    async renderChart(category = 'goals') {
        const canvas = document.getElementById('performersChart');
        const ctx = canvas.getContext('2d');

        // Destroy existing chart
        if (this.charts.performers) {
            this.charts.performers.destroy();
        }

        if (!this.data.stats?.current_season_leaders) return;

        const leaders = this.data.stats.current_season_leaders
            .sort((a, b) => this.getStatValue(b, category) - this.getStatValue(a, category))
            .slice(0, 10);

        const categoryNames = {
            goals: 'Goals',
            assists: 'Assists',
            blocks: 'Blocks'
        };

        this.charts.performers = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: leaders.map(p => p.full_name || `${p.first_name} ${p.last_name}`),
                datasets: [{
                    label: categoryNames[category] || category,
                    data: leaders.map(p => this.getStatValue(p, category)),
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    async searchPlayers() {
        const query = document.getElementById('playerSearch').value.trim();
        if (!query) return;

        try {
            const response = await fetch(`${this.apiBase}/players/search?q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const players = await response.json();
                this.showSearchResults('Players', players, 'player');
            }
        } catch (error) {
            console.error('Failed to search players:', error);
        }
    }

    async searchTeams() {
        const query = document.getElementById('teamSearch').value.trim();
        if (!query) return;

        try {
            const response = await fetch(`${this.apiBase}/teams/search?q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const teams = await response.json();
                this.showSearchResults('Teams', teams, 'team');
            }
        } catch (error) {
            console.error('Failed to search teams:', error);
        }
    }

    showSearchResults(title, results, type) {
        const searchResults = document.getElementById('searchResults');
        const content = document.getElementById('searchResultsContent');
        
        if (!results || results.length === 0) {
            content.innerHTML = `<div class="no-data">No ${title.toLowerCase()} found</div>`;
        } else {
            content.innerHTML = `
                <h3>${title} (${results.length} found)</h3>
                <div class="search-results-list">
                    ${results.map(item => this.renderSearchItem(item, type)).join('')}
                </div>
            `;
        }
        
        searchResults.style.display = 'block';
    }

    renderSearchItem(item, type) {
        if (type === 'player') {
            return `
                <div class="search-item">
                    <div class="search-item-title">${item.full_name || `${item.first_name} ${item.last_name}`}</div>
                    <div class="search-item-details">Team: ${this.getTeamName(item.team_id)} | Year: ${item.year}</div>
                </div>
            `;
        } else if (type === 'team') {
            return `
                <div class="search-item">
                    <div class="search-item-title">${item.full_name}</div>
                    <div class="search-item-details">${item.city} | ${item.division_name || 'No Division'}</div>
                </div>
            `;
        }
        return '';
    }

    clearSearch() {
        document.getElementById('playerSearch').value = '';
        document.getElementById('teamSearch').value = '';
        document.getElementById('searchResults').style.display = 'none';
    }

    async loadMoreGames() {
        // This would load more games in a real implementation
        console.log('Load more games functionality would be implemented here');
    }

    sortTable(table, sortBy) {
        // Basic table sorting implementation
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aVal = this.getCellValue(a, sortBy);
            const bVal = this.getCellValue(b, sortBy);
            
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return bVal - aVal; // Descending for numbers
            }
            return aVal.toString().localeCompare(bVal.toString());
        });
        
        rows.forEach(row => tbody.appendChild(row));
    }

    getCellValue(row, sortBy) {
        const cell = row.querySelector(`[data-sort="${sortBy}"]`) || 
                    row.cells[Array.from(row.parentNode.parentNode.querySelectorAll('th')).findIndex(th => th.getAttribute('data-sort') === sortBy)];
        
        if (!cell) return '';
        
        const text = cell.textContent.trim();
        const num = parseFloat(text);
        return isNaN(num) ? text : num;
    }

    getTeamName(teamId) {
        if (!this.data.stats?.team_standings) return teamId;
        
        const team = this.data.stats.team_standings.find(t => t.team_id === teamId);
        return team ? team.full_name : teamId;
    }

    calculateWinPercentage(wins, losses, ties = 0) {
        const total = wins + losses + ties;
        if (total === 0) return '0.000';
        return ((wins + ties * 0.5) / total).toFixed(3);
    }

    formatDate(timestamp) {
        if (!timestamp) return '';
        try {
            return new Date(timestamp).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        } catch {
            return timestamp;
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        document.querySelector('.dashboard-container').prepend(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    async refresh() {
        const refreshButton = document.getElementById('refreshButton');
        refreshButton.textContent = '⟳ Refreshing...';
        refreshButton.disabled = true;
        
        try {
            await this.loadInitialData();
            this.renderOverview();
            this.renderStandings();
            this.renderLeaders();
            this.renderRecentGames();
            this.renderChart();
        } catch (error) {
            console.error('Failed to refresh:', error);
            this.showError('Failed to refresh data');
        } finally {
            refreshButton.textContent = '⟳ Refresh';
            refreshButton.disabled = false;
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new UFADashboard();
});