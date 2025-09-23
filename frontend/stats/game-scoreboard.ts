/**
 * Game Scoreboard Component - Handles scoreboard and quarter scores display
 */

import { TeamData } from './game-detail';

export class GameScoreboard {
    // DOM elements
    private elements = {
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
    };

    constructor() {
        this.initializeElements();
    }

    private initializeElements(): void {
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

        if (cityAbbreviations[city]) {
            return cityAbbreviations[city];
        }

        // Fallback: take first 3 characters and uppercase
        return city.substring(0, 3).toUpperCase();
    }

    public updateScoreboard(homeTeam: TeamData, awayTeam: TeamData): void {
        // Update team names and scores
        if (this.elements.awayName) this.elements.awayName.textContent = awayTeam.full_name;
        if (this.elements.awayScore) this.elements.awayScore.textContent = String(awayTeam.final_score);
        if (this.elements.homeName) this.elements.homeName.textContent = homeTeam.full_name;
        if (this.elements.homeScore) this.elements.homeScore.textContent = String(homeTeam.final_score);

        // Update team logos (first letter of team name)
        if (this.elements.awayLogo) this.elements.awayLogo.textContent = awayTeam.name.charAt(0);
        if (this.elements.homeLogo) this.elements.homeLogo.textContent = homeTeam.name.charAt(0);

        // Update team abbreviations in quarter table
        if (this.elements.awayTeamAbbrev) {
            this.elements.awayTeamAbbrev.textContent = this.getCityAbbreviation(awayTeam.city);
        }
        if (this.elements.homeTeamAbbrev) {
            this.elements.homeTeamAbbrev.textContent = this.getCityAbbreviation(homeTeam.city);
        }

        // Update quarter scores
        this.updateQuarterScores(homeTeam, awayTeam);
    }

    private updateQuarterScores(homeTeam: TeamData, awayTeam: TeamData): void {
        // Update away team quarters
        if (this.elements.awayQuarters) {
            const cells = this.elements.awayQuarters.cells;
            awayTeam.quarter_scores.forEach((score, i) => {
                if (cells[i + 1]) {
                    cells[i + 1].textContent = String(score);
                }
            });
            // Update total
            if (cells[5]) {
                cells[5].textContent = String(awayTeam.final_score);
            }
        }

        // Update home team quarters
        if (this.elements.homeQuarters) {
            const cells = this.elements.homeQuarters.cells;
            homeTeam.quarter_scores.forEach((score, i) => {
                if (cells[i + 1]) {
                    cells[i + 1].textContent = String(score);
                }
            });
            // Update total
            if (cells[5]) {
                cells[5].textContent = String(homeTeam.final_score);
            }
        }
    }
}

export default GameScoreboard;