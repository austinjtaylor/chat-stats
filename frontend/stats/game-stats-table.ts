/**
 * Game Stats Table Component - Handles player statistics table
 */

import { PlayerStats } from './game-detail';

export class GameStatsTable {
    private players: PlayerStats[] = [];
    private sortColumn: string = 'plus_minus';
    private sortDirection: 'asc' | 'desc' = 'desc';

    // DOM elements
    private elements = {
        statsTable: null as HTMLTableElement | null,
        statsTableBody: null as HTMLElement | null,
    };

    constructor() {
        this.initializeElements();
        this.attachEventListeners();
    }

    private initializeElements(): void {
        this.elements.statsTable = document.getElementById('statsTable') as HTMLTableElement;
        this.elements.statsTableBody = document.getElementById('statsTableBody');
    }

    private attachEventListeners(): void {
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

    public updatePlayers(players: PlayerStats[]): void {
        this.players = players;
        this.renderTable();
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

        this.renderTable();
    }

    private renderTable(): void {
        if (!this.elements.statsTableBody) return;

        const players = [...this.players];

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
}

export default GameStatsTable;