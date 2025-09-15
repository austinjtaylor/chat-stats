// Games page functionality
document.addEventListener('DOMContentLoaded', async () => {
    const gamesContainer = document.getElementById('gamesContainer');
    const yearFilter = document.getElementById('yearFilter');
    const teamFilter = document.getElementById('teamFilter');

    // Load teams for filter
    async function loadTeams() {
        try {
            // Use API client for teams
            const teams = await statsAPI.getTeams();
            teamFilter.innerHTML = '<option value="all">All</option>';
            teams.forEach(team => {
                const option = document.createElement('option');
                option.value = team.id;
                option.textContent = `${team.city} ${team.name}`;
                teamFilter.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    // Load games
    async function loadGames() {
        try {
            window.ufaStats.showLoading(gamesContainer, 'Loading games...');

            const filters = {};
            if (yearFilter.value !== 'all') {
                filters.year = yearFilter.value;
            }
            if (teamFilter.value !== 'all') {
                filters.team_id = teamFilter.value;
            }

            // Use API client for games
            const games = await statsAPI.getGames(filters);
            displayGames(games);
        } catch (error) {
            console.error('Failed to load games:', error);
            gamesContainer.innerHTML = '<div class="error-message">Failed to load games. Please make sure the backend is running.</div>';
        }
    }

    // Display games
    function displayGames(games) {
        if (!games || games.length === 0) {
            gamesContainer.innerHTML = '<div class="no-data">No games found</div>';
            return;
        }

        gamesContainer.innerHTML = games.map(game => `
            <div class="game-card">
                <div class="game-date">${window.Format ? window.Format.date(game.date) : new Date(game.date).toLocaleDateString()}</div>
                <div class="game-teams">
                    <span class="team-name">${game.home_team}</span>
                    <span class="score">${game.home_score || 0}</span>
                    <span class="vs">vs</span>
                    <span class="score">${game.away_score || 0}</span>
                    <span class="team-name">${game.away_team}</span>
                </div>
            </div>
        `).join('');
    }

    // Event listeners
    yearFilter.addEventListener('change', loadGames);
    teamFilter.addEventListener('change', loadGames);

    // Modal functionality
    const modal = document.getElementById('gameDetailModal');
    const closeModal = document.getElementById('closeModal');

    if (closeModal) {
        closeModal.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    // Click outside modal to close
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Initial load
    loadTeams();
    loadGames();
});