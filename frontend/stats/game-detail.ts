/**
 * Game Detail Page - Main Logic
 */

interface GameListItem {
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

interface PlayerStats {
    name: string;
    jersey_number: string;
    points_played: number;
    o_points_played: number;
    d_points_played: number;
    assists: number;
    goals: number;
    blocks: number;
    plus_minus: number;
    yards_received: number;
    yards_thrown: number;
    total_yards: number;
    completions: number;
    completion_percentage: number;
    hockey_assists: number;
    hucks_completed: number;
    hucks_received: number;
    huck_percentage: number;
    turnovers: number;
    yards_per_turn: number | null;
    stalls: number;
    callahans: number;
    drops: number;
}

interface StatDetail {
    percentage: number;
    made: number;
    total?: number;
    attempted?: number;
}

interface TeamStatistics {
    completions: StatDetail;
    hucks: StatDetail;
    blocks: number;
    turnovers: number;
    hold?: StatDetail;
    o_line_conversion?: StatDetail;
    break?: StatDetail;
    d_line_conversion?: StatDetail;
    redzone_conversion?: StatDetail;
}

interface TeamData {
    team_id: string;
    name: string;
    full_name: string;
    city: string;
    final_score: number;
    quarter_scores: number[];
    players: PlayerStats[];
    stats?: TeamStatistics;
}

interface BoxScoreData {
    game_id: string;
    status: string;
    start_timestamp: string;
    location: string;
    year: number;
    week: string;
    home_team: TeamData;
    away_team: TeamData;
}

class GameDetailPage {
    private gameList: GameListItem[] = [];
    private currentGame: BoxScoreData | null = null;
    private currentTeam: 'home' | 'away' = 'away';
    private sortColumn: string = 'plus_minus';
    private sortDirection: 'asc' | 'desc' = 'desc';
    private currentYear: number = 2025;
    private currentTeamFilter: string = 'all';
    private teams: any[] = [];

    // DOM elements
    private elements = {
        gameSearchIcon: null as HTMLElement | null,
        gameSelectionPanel: null as HTMLElement | null,
        closePanel: null as HTMLElement | null,
        yearFilter: null as HTMLSelectElement | null,
        teamFilter: null as HTMLSelectElement | null,
        gameList: null as HTMLElement | null,
        // Scoreboard elements
        awayLogo: null as HTMLElement | null,
        awayName: null as HTMLElement | null,
        awayScore: null as HTMLElement | null,
        homeLogo: null as HTMLElement | null,
        homeName: null as HTMLElement | null,
        homeScore: null as HTMLElement | null,
        awayQuarters: null as HTMLTableRowElement | null,
        homeQuarters: null as HTMLTableRowElement | null,
        awayTeamAbbrev: null as HTMLElement | null,
        homeTeamAbbrev: null as HTMLElement | null,
        // Box score elements
        awayTeamRadio: null as HTMLElement | null,
        homeTeamRadio: null as HTMLElement | null,
        statsTable: null as HTMLTableElement | null,
        statsTableBody: null as HTMLElement | null,
    };

    constructor() {
        this.initializeElements();
        this.attachEventListeners();
        this.loadTeams();
        this.loadGamesList();
        this.checkURLParams();
    }

    private getCityAbbreviation(city: string): string {
        // Handle special cases and common city abbreviations
        const cityAbbreviations: Record<string, string> = {
            'Atlanta': 'ATL',
            'Austin': 'AUS',
            'Boston': 'BOS',
            'Carolina': 'CAR',
            'Chicago': 'CHI',
            'Colorado': 'COL',
            'DC': 'DC',
            'Detroit': 'DET',
            'Houston': 'HOU',
            'Indianapolis': 'IND',
            'LA': 'LA',
            'Madison': 'MAD',
            'Minnesota': 'MIN',
            'Montreal': 'MTL',
            'New York': 'NY',
            'Oakland': 'OAK',
            'Oregon': 'ORE',
            'Philadelphia': 'PHI',
            'Pittsburgh': 'PIT',
            'Salt Lake': 'SLC',
            'San Diego': 'SD',
            'Seattle': 'SEA',
            'Toronto': 'TOR',
            'Vegas': 'LV'
        };

        // Return the mapped abbreviation if it exists
        if (cityAbbreviations[city]) {
            return cityAbbreviations[city];
        }

        // Fallback: take first 3 characters and uppercase
        return city.substring(0, 3).toUpperCase();
    }

    private initializeElements(): void {
        // Get all DOM elements
        this.elements.gameSearchIcon = document.getElementById('gameSearchIcon');
        this.elements.gameSelectionPanel = document.getElementById('gameSelectionPanel');
        this.elements.closePanel = document.getElementById('closePanel');
        this.elements.yearFilter = document.getElementById('yearFilter') as HTMLSelectElement;
        this.elements.teamFilter = document.getElementById('teamFilter') as HTMLSelectElement;
        this.elements.gameList = document.getElementById('gameList');

        // Scoreboard elements
        this.elements.awayLogo = document.getElementById('awayLogo');
        this.elements.awayName = document.getElementById('awayName');
        this.elements.awayScore = document.getElementById('awayScore');
        this.elements.homeLogo = document.getElementById('homeLogo');
        this.elements.homeName = document.getElementById('homeName');
        this.elements.homeScore = document.getElementById('homeScore');
        this.elements.awayQuarters = document.getElementById('awayQuarters') as HTMLTableRowElement;
        this.elements.homeQuarters = document.getElementById('homeQuarters') as HTMLTableRowElement;
        this.elements.awayTeamAbbrev = document.getElementById('awayTeamAbbrev');
        this.elements.homeTeamAbbrev = document.getElementById('homeTeamAbbrev');

        // Box score elements
        this.elements.awayTeamRadio = document.getElementById('awayTeamRadio');
        this.elements.homeTeamRadio = document.getElementById('homeTeamRadio');
        this.elements.statsTable = document.getElementById('statsTable') as HTMLTableElement;
        this.elements.statsTableBody = document.getElementById('statsTableBody');
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

        // Click outside to close (on the shifted content)
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

        // Filter changes
        if (this.elements.yearFilter) {
            this.elements.yearFilter.addEventListener('change', (e) => {
                this.currentYear = parseInt((e.target as HTMLSelectElement).value);
                this.loadTeams();  // Reload teams for the selected year
                this.loadGamesList();
            });
        }

        if (this.elements.teamFilter) {
            this.elements.teamFilter.addEventListener('change', (e) => {
                this.currentTeamFilter = (e.target as HTMLSelectElement).value;
                this.loadGamesList();
            });
        }

        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const tab = (e.target as HTMLElement).dataset.tab;
                if (tab) {
                    this.switchTab(tab);
                }
            });
        });

        // Team toggle
        document.querySelectorAll('input[name="teamSelect"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentTeam = (e.target as HTMLInputElement).value as 'home' | 'away';
                this.updateStatsTable();
            });
        });

        // Table sorting
        if (this.elements.statsTable) {
            const headers = this.elements.statsTable.querySelectorAll('th[data-sort]');
            headers.forEach(header => {
                header.addEventListener('click', (e) => {
                    const column = (e.target as HTMLElement).dataset.sort;
                    if (column) {
                        this.sortTable(column);
                    }
                });
            });
        }
    }

    private async loadTeams(): Promise<void> {
        try {
            const response = await fetch(`/api/teams?year=${this.currentYear}`);
            this.teams = await response.json();

            if (this.elements.teamFilter) {
                // Remember current selection
                const currentSelection = this.elements.teamFilter.value;

                this.elements.teamFilter.innerHTML = '<option value="all">All</option>';
                this.teams.forEach(team => {
                    const option = document.createElement('option');
                    option.value = team.team_id;
                    option.textContent = team.name;
                    this.elements.teamFilter!.appendChild(option);
                });

                // Restore selection if team still exists, otherwise reset to 'all'
                const teamExists = this.teams.some(team => team.team_id === currentSelection);
                if (teamExists) {
                    this.elements.teamFilter.value = currentSelection;
                } else {
                    this.elements.teamFilter.value = 'all';
                    this.currentTeamFilter = 'all';
                }
            }
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    private async loadGamesList(): Promise<void> {
        try {
            let url = `/api/games/list?limit=500&year=${this.currentYear}`;
            if (this.currentTeamFilter !== 'all') {
                url += `&team_id=${this.currentTeamFilter}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            this.gameList = data.games || [];
            this.updateGameList();

            // Only load first game automatically if no game specified in URL
            // AND the sidebar is not currently open (to prevent closing it during filter changes)
            const urlParams = new URLSearchParams(window.location.search);
            const gameIdFromUrl = urlParams.get('game');
            const isSidebarOpen = this.elements.gameSelectionPanel?.classList.contains('active');

            if (!gameIdFromUrl && this.gameList.length > 0 && !isSidebarOpen) {
                this.loadGameDetails(this.gameList[0].game_id, false);
            }
        } catch (error) {
            console.error('Failed to load games list:', error);
        }
    }

    private checkURLParams(): void {
        const urlParams = new URLSearchParams(window.location.search);
        const gameId = urlParams.get('game');

        if (gameId) {
            // Wait for games list to load then select the game
            setTimeout(() => {
                this.loadGameDetails(gameId, false);
            }, 500);
        }
    }

    private openGameSearch(): void {
        if (this.elements.gameSelectionPanel) {
            this.elements.gameSelectionPanel.classList.add('active');
            document.documentElement.classList.add('sidebar-open');
            document.body.classList.add('sidebar-open');
        }
    }

    private closeGameSearch(): void {
        if (this.elements.gameSelectionPanel) {
            this.elements.gameSelectionPanel.classList.remove('active');
            document.documentElement.classList.remove('sidebar-open');
            document.body.classList.remove('sidebar-open');
        }
    }

    private updateGameList(): void {
        if (!this.elements.gameList) return;

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

        // Add click handlers to game list items
        this.elements.gameList.querySelectorAll('.game-list-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const gameId = (e.currentTarget as HTMLElement).dataset.gameId;
                if (gameId) {
                    // Update active state
                    this.elements.gameList?.querySelectorAll('.game-list-item').forEach(i => {
                        i.classList.remove('active');
                    });
                    (e.currentTarget as HTMLElement).classList.add('active');
                    // Load game
                    this.loadGameDetails(gameId);
                }
            });
        });
    }

    private async loadGameDetails(gameId: string, closePanel: boolean = true): Promise<void> {
        try {
            const response = await fetch(`/api/games/${gameId}/box-score`);
            const data: BoxScoreData = await response.json();

            this.currentGame = data;
            this.updateScoreboard();
            this.updateTeamRadios();
            this.updateStatsTable();
            this.updateTeamStats();

            // Update active game in list
            this.elements.gameList?.querySelectorAll('.game-list-item').forEach(item => {
                item.classList.toggle('active', item.getAttribute('data-game-id') === gameId);
            });

            // Close search overlay after selection only if requested
            if (closePanel) {
                this.closeGameSearch();
            }
        } catch (error) {
            console.error('Failed to load game details:', error);
        }
    }

    private updateScoreboard(): void {
        if (!this.currentGame) return;

        const { home_team, away_team } = this.currentGame;

        // Update team names and scores
        if (this.elements.awayName) this.elements.awayName.textContent = away_team.full_name;
        if (this.elements.awayScore) this.elements.awayScore.textContent = String(away_team.final_score);
        if (this.elements.homeName) this.elements.homeName.textContent = home_team.full_name;
        if (this.elements.homeScore) this.elements.homeScore.textContent = String(home_team.final_score);

        // Update team logos (first letter of team name)
        if (this.elements.awayLogo) this.elements.awayLogo.textContent = away_team.name.charAt(0);
        if (this.elements.homeLogo) this.elements.homeLogo.textContent = home_team.name.charAt(0);

        // Update team abbreviations in quarter table
        if (this.elements.awayTeamAbbrev) {
            this.elements.awayTeamAbbrev.textContent = this.getCityAbbreviation(away_team.city);
        }
        if (this.elements.homeTeamAbbrev) {
            this.elements.homeTeamAbbrev.textContent = this.getCityAbbreviation(home_team.city);
        }

        // Update quarter scores
        this.updateQuarterScores();
    }

    private updateQuarterScores(): void {
        if (!this.currentGame) return;

        const { home_team, away_team } = this.currentGame;

        // Update away team quarters
        if (this.elements.awayQuarters) {
            const cells = this.elements.awayQuarters.cells;
            away_team.quarter_scores.forEach((score, i) => {
                if (cells[i + 1]) {
                    cells[i + 1].textContent = String(score);
                }
            });
            // Update total
            if (cells[5]) {
                cells[5].textContent = String(away_team.final_score);
            }
        }

        // Update home team quarters
        if (this.elements.homeQuarters) {
            const cells = this.elements.homeQuarters.cells;
            home_team.quarter_scores.forEach((score, i) => {
                if (cells[i + 1]) {
                    cells[i + 1].textContent = String(score);
                }
            });
            // Update total
            if (cells[5]) {
                cells[5].textContent = String(home_team.final_score);
            }
        }
    }

    private updateTeamRadios(): void {
        if (!this.currentGame) return;

        const { home_team, away_team } = this.currentGame;

        if (this.elements.awayTeamRadio) {
            this.elements.awayTeamRadio.textContent = away_team.full_name;
        }
        if (this.elements.homeTeamRadio) {
            this.elements.homeTeamRadio.textContent = home_team.full_name;
        }
    }

    private updateStatsTable(): void {
        if (!this.currentGame || !this.elements.statsTableBody) return;

        const team = this.currentTeam === 'home' ? this.currentGame.home_team : this.currentGame.away_team;
        const players = [...team.players];

        // Sort players
        players.sort((a, b) => {
            const aVal = a[this.sortColumn as keyof PlayerStats] ?? 0;
            const bVal = b[this.sortColumn as keyof PlayerStats] ?? 0;

            if (this.sortDirection === 'asc') {
                return aVal > bVal ? 1 : -1;
            } else {
                return aVal < bVal ? 1 : -1;
            }
        });

        // Render table rows
        this.elements.statsTableBody.innerHTML = players.map(player => `
            <tr>
                <td class="player-name">${player.name}</td>
                <td>${player.jersey_number || '-'}</td>
                <td class="numeric">${player.points_played}</td>
                <td class="numeric">${player.o_points_played}</td>
                <td class="numeric">${player.d_points_played}</td>
                <td class="numeric">${player.assists}</td>
                <td class="numeric">${player.goals}</td>
                <td class="numeric">${player.blocks}</td>
                <td class="numeric">${player.plus_minus >= 0 ? '+' : ''}${player.plus_minus}</td>
                <td class="numeric">${player.yards_received}</td>
                <td class="numeric">${player.yards_thrown}</td>
                <td class="numeric">${player.total_yards}</td>
                <td class="numeric">${player.completions}</td>
                <td class="numeric">${player.completion_percentage.toFixed(1)}%</td>
                <td class="numeric">${player.hucks_completed}</td>
                <td class="numeric">${player.hucks_received}</td>
                <td class="numeric">${player.huck_percentage.toFixed(1)}%</td>
                <td class="numeric">${player.hockey_assists}</td>
                <td class="numeric">${player.turnovers}</td>
                <td class="numeric">${player.yards_per_turn !== null ? player.yards_per_turn.toFixed(1) : '-'}</td>
                <td class="numeric">${player.stalls}</td>
                <td class="numeric">${player.callahans}</td>
                <td class="numeric">${player.drops}</td>
            </tr>
        `).join('');
    }

    private sortTable(column: string): void {
        // Toggle sort direction if same column
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'desc';
        }

        // Update header classes
        if (this.elements.statsTable) {
            this.elements.statsTable.querySelectorAll('th[data-sort]').forEach(th => {
                th.classList.remove('sorted-asc', 'sorted-desc');
                if (th.getAttribute('data-sort') === column) {
                    th.classList.add(this.sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
                }
            });
        }

        this.updateStatsTable();
    }

    private switchTab(tabId: string): void {
        // Update active tab button
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.toggle('active', button.getAttribute('data-tab') === tabId);
        });

        // Update active tab pane
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.id === tabId);
        });
    }

    private updateTeamStats(): void {
        if (!this.currentGame) return;

        const { home_team, away_team } = this.currentGame;

        // Update team headers
        const awayTeamHeader = document.getElementById('awayTeamHeader');
        const homeTeamHeader = document.getElementById('homeTeamHeader');
        if (awayTeamHeader) awayTeamHeader.textContent = away_team.full_name;
        if (homeTeamHeader) homeTeamHeader.textContent = home_team.full_name;

        // Helper function to format stat with percentage and fraction
        const formatStat = (stat?: StatDetail): string => {
            if (!stat) return '-';
            // Use 'attempted' for completions and hucks, 'total' for others
            const denominator = stat.attempted !== undefined ? stat.attempted : stat.total;
            if (denominator === undefined || denominator === 0) return '0% (0/0)';
            return `${stat.percentage}% (${stat.made}/${denominator})`;
        };

        // Update away team stats
        if (away_team.stats) {
            const stats = away_team.stats;
            document.getElementById('awayCompletions')!.textContent = formatStat(stats.completions);
            document.getElementById('awayHucks')!.textContent = formatStat(stats.hucks);
            document.getElementById('awayHold')!.textContent = stats.hold ? formatStat(stats.hold) : '-';
            document.getElementById('awayOLineConv')!.textContent = stats.o_line_conversion ? formatStat(stats.o_line_conversion) : '-';
            document.getElementById('awayBreak')!.textContent = stats.break ? formatStat(stats.break) : '-';
            document.getElementById('awayDLineConv')!.textContent = stats.d_line_conversion ? formatStat(stats.d_line_conversion) : '-';
            document.getElementById('awayRedZone')!.textContent = stats.redzone_conversion ? formatStat(stats.redzone_conversion) : '-';
            document.getElementById('awayBlocks')!.textContent = String(stats.blocks);
            document.getElementById('awayTurnovers')!.textContent = String(stats.turnovers);
        } else {
            // Clear all away team stats
            ['awayCompletions', 'awayHucks', 'awayHold', 'awayOLineConv', 'awayBreak',
             'awayDLineConv', 'awayRedZone', 'awayBlocks', 'awayTurnovers'].forEach(id => {
                const element = document.getElementById(id);
                if (element) element.textContent = '-';
            });
        }

        // Update home team stats
        if (home_team.stats) {
            const stats = home_team.stats;
            document.getElementById('homeCompletions')!.textContent = formatStat(stats.completions);
            document.getElementById('homeHucks')!.textContent = formatStat(stats.hucks);
            document.getElementById('homeHold')!.textContent = stats.hold ? formatStat(stats.hold) : '-';
            document.getElementById('homeOLineConv')!.textContent = stats.o_line_conversion ? formatStat(stats.o_line_conversion) : '-';
            document.getElementById('homeBreak')!.textContent = stats.break ? formatStat(stats.break) : '-';
            document.getElementById('homeDLineConv')!.textContent = stats.d_line_conversion ? formatStat(stats.d_line_conversion) : '-';
            document.getElementById('homeRedZone')!.textContent = stats.redzone_conversion ? formatStat(stats.redzone_conversion) : '-';
            document.getElementById('homeBlocks')!.textContent = String(stats.blocks);
            document.getElementById('homeTurnovers')!.textContent = String(stats.turnovers);
        } else {
            // Clear all home team stats
            ['homeCompletions', 'homeHucks', 'homeHold', 'homeOLineConv', 'homeBreak',
             'homeDLineConv', 'homeRedZone', 'homeBlocks', 'homeTurnovers'].forEach(id => {
                const element = document.getElementById(id);
                if (element) element.textContent = '-';
            });
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new GameDetailPage();
});

export default GameDetailPage;