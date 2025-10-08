/**
 * Game Detail Page - Main Coordinator
 */

import { GameSearch } from './game-search';
import { GameScoreboard } from './game-scoreboard';
import { GameStatsTable } from './game-stats-table';
import { GamePlayByPlay } from './game-play-by-play';

// Export interfaces for use by other modules
export interface PlayerStats {
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

export interface StatDetail {
    percentage: number;
    made: number;
    total?: number;
    attempted?: number;
}

export interface TeamStatistics {
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

export interface TeamData {
    team_id: string;
    name: string;
    full_name: string;
    city: string;
    final_score: number;
    quarter_scores: number[];
    players: PlayerStats[];
    stats?: TeamStatistics;
}

export interface BoxScoreData {
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
    private currentGame: BoxScoreData | null = null;
    private currentTeam: 'home' | 'away' | 'both' = 'both';

    // Components
    private gameSearch: GameSearch;
    private gameScoreboard: GameScoreboard;
    private gameStatsTable: GameStatsTable;
    private gamePlayByPlay: GamePlayByPlay;

    // DOM elements
    private elements = {
        awayTeamRadio: null as HTMLElement | null,
        homeTeamRadio: null as HTMLElement | null,
    };

    constructor() {
        // Initialize components
        this.gameSearch = new GameSearch();
        this.gameScoreboard = new GameScoreboard();
        this.gameStatsTable = new GameStatsTable();
        this.gamePlayByPlay = new GamePlayByPlay(this.getCityAbbreviation.bind(this));

        // Setup component callbacks
        this.gameSearch.setOnGameSelect(this.loadGameDetails.bind(this));

        // Initialize
        this.initializeElements();
        this.attachEventListeners();
        this.gameSearch.initialize();
        this.checkURLParams();
    }

    private getCityAbbreviation(city: string): string {
        // City abbreviation mapping
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

        if (cityAbbreviations[city]) {
            return cityAbbreviations[city];
        }
        return city.substring(0, 3).toUpperCase();
    }

    private initializeElements(): void {
        this.elements.awayTeamRadio = document.getElementById('awayTeamRadio');
        this.elements.homeTeamRadio = document.getElementById('homeTeamRadio');
    }

    private attachEventListeners(): void {
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
                this.currentTeam = (e.target as HTMLInputElement).value as 'home' | 'away' | 'both';
                this.updateStatsTable();
            });
        });
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

    private isPlayByPlayTabActive(): boolean {
        const playByPlayTab = document.getElementById('play-by-play');
        return playByPlayTab?.classList.contains('active') || false;
    }

    private async loadGameDetails(gameId: string, closePanel: boolean = true): Promise<void> {
        try {
            const response = await fetch(`/api/games/${gameId}/box-score`);
            const data: BoxScoreData = await response.json();

            this.currentGame = data;
            this.gameScoreboard.updateScoreboard(data.home_team, data.away_team);
            this.updateTeamRadios();
            this.updateStatsTable();
            this.updateTeamStats();

            // If play-by-play tab is currently active, reload play-by-play data
            if (this.isPlayByPlayTabActive()) {
                this.gamePlayByPlay.loadPlayByPlay(data.game_id).then(() => {
                    this.gamePlayByPlay.renderPlayByPlay(
                        data.home_team.city,
                        data.away_team.city
                    );
                });
            }

            // Update active game in search
            this.gameSearch.setActiveGame(gameId);

            // Close search overlay after selection only if requested
            if (closePanel) {
                this.gameSearch.closeGameSearch();
            }
        } catch (error) {
            console.error('Failed to load game details:', error);
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
        if (!this.currentGame) return;

        let players: PlayerStats[];
        if (this.currentTeam === 'both') {
            // Combine players from both teams
            players = [
                ...this.currentGame.away_team.players,
                ...this.currentGame.home_team.players
            ];
        } else {
            const team = this.currentTeam === 'home' ? this.currentGame.home_team : this.currentGame.away_team;
            players = team.players;
        }
        this.gameStatsTable.updatePlayers(players);
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

        // Load play-by-play data when switching to that tab
        if (tabId === 'play-by-play' && this.currentGame) {
            this.gamePlayByPlay.loadPlayByPlay(this.currentGame.game_id).then(() => {
                this.gamePlayByPlay.renderPlayByPlay(
                    this.currentGame?.home_team.city,
                    this.currentGame?.away_team.city
                );
            });
        }
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
            const denominator = stat.attempted !== undefined ? stat.attempted : stat.total;
            if (denominator === undefined || denominator === 0) return '0 (0/0)';
            return `${stat.percentage} (${stat.made}/${denominator})`;
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