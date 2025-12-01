/**
 * Table Header Tooltips Utility
 * Provides tooltip descriptions for all table column headers
 */

// Column descriptions for Players table
export const playerColumnDescriptions: Record<string, string> = {
    full_name: 'Player name',
    games_played: 'Games Played',
    total_points_played: 'Points Played',
    possessions: 'Offensive Possessions',
    score_total: 'Total Scores\nAssists + Goals',
    total_assists: 'Assists',
    total_goals: 'Goals',
    total_blocks: 'Blocks',
    calculated_plus_minus: 'Plus/Minus\n+1 per goal, assist and block\n-1 per throwaway, drop and stall',
    total_completions: 'Completions',
    completion_percentage: 'Completion Percentage\nMinimum 100 throw attempts required',
    total_yards: 'Total Yards',
    total_yards_thrown: 'Throwing Yards',
    total_yards_received: 'Receiving Yards',
    offensive_efficiency: 'Offensive Efficiency\nTeam scores while on the field / offensive possessions\nMust have 100 offensive possessions',
    total_hockey_assists: 'Hockey Assists',
    total_throwaways: 'Throwaways',
    yards_per_turn: 'Total Yards per Turnover',
    yards_per_completion: 'Throwing Yards per Completion',
    yards_per_reception: 'Receiving Yards per Reception',
    assists_per_turnover: 'Assists per Turnover',
    total_stalls: 'Stalls',
    total_drops: 'Drops',
    total_callahans: 'Callahans',
    total_hucks_completed: 'Hucks over 40 yards downfield',
    total_hucks_received: 'Hucks Received',
    huck_percentage: 'Huck completion percentage\nMust have 10 huck attempts',
    total_pulls: 'Pulls',
    total_o_points_played: 'O-Points Played',
    total_d_points_played: 'D-Points Played',
    minutes_played: 'Minutes Played',
    // Short labels used in the table
    GP: 'Games Played',
    PP: 'Points Played',
    POS: 'Offensive Possessions',
    S: 'Total Scores\nAssists + Goals',
    A: 'Assists',
    G: 'Goals',
    B: 'Blocks',
    '+/-': 'Plus/Minus\n+1 per goal, assist and block\n-1 per throwaway, drop and stall',
    C: 'Completions',
    'C%': 'Completion Percentage\nMinimum 100 throw attempts required',
    Y: 'Total Yards',
    'TOT Y': 'Total Yards',
    TY: 'Throwing Yards',
    RY: 'Receiving Yards',
    OEFF: 'Offensive Efficiency\nTeam scores while on the field / offensive possessions\nMust have 100 offensive possessions',
    HA: 'Hockey Assists',
    T: 'Throwaways',
    'TY/C': 'Throwing Yards per Completion',
    'RY/R': 'Receiving Yards per Reception',
    'AST/T': 'Assists per Turnover',
    D: 'Drops',
    CAL: 'Callahans',
    H: 'Hucks over 40 yards downfield',
    HR: 'Hucks Received',
    'H%': 'Huck completion percentage\nMust have 10 huck attempts',
    P: 'Pulls',
    OPP: 'O-Points Played',
    DPP: 'D-Points Played',
    MP: 'Minutes Played'
};

// Column descriptions for Teams table
export const teamColumnDescriptions: Record<string, string> = {
    name: 'Team name',
    games_played: 'Games Played',
    wins: 'Wins',
    losses: 'Losses',
    scores: 'Scores',
    scores_against: 'Scores Against',
    completions: 'Completions',
    turnovers: 'Turnovers',
    completion_percentage: 'Completion Percentage',
    hucks_completed: 'Hucks Completed',
    hucks_attempted: 'Hucks Attempted',
    huck_turnovers: 'Huck Turnovers\n(Hucks attempted - Hucks completed)',
    o_line_scores: 'Holds\n(Points where the O-line scored)',
    d_line_scores: 'Breaks\n(Points where the D-line scored)',
    huck_percentage: 'Huck Percentage',
    hold_percentage: 'Hold Percentage\n(O-line scores / O-line points)',
    o_line_conversion: 'O-line Conversion Percentage\n(O-line scores / O-line possessions)',
    blocks: 'Blocks',
    break_percentage: 'Break Percentage\n(D-line scores / D-line points)',
    d_line_conversion: 'D-line Conversion Percentage\n(D-line scores / D-line possessions)',
    red_zone_conversion: 'Red Zone Conversion Percentage\n(Red zone scores / possessions within 20 yards of the endzone)',
    // Short labels used in the table
    G: 'Games',
    W: 'Wins',
    L: 'Losses',
    S: 'Scores',
    SA: 'Scores Against',
    C: 'Completions',
    T: 'Turnovers',
    'C %': 'Completion Percentage',
    H: 'Hucks',
    HT: 'Huck Turnovers\n(Hucks attempted - Hucks completed)',
    HLD: 'Holds\n(Points where the O-line scored)',
    BRK: 'Breaks\n(Points where the D-line scored)',
    'H %': 'Huck Percentage',
    'HLD %': 'Hold Percentage\n(O-line scores / O-line points)',
    'OLC %': 'O-line Conversion Percentage\n(O-line scores / O-line possessions)',
    B: 'Blocks',
    'BRK %': 'Break Percentage\n(D-line scores / D-line points)',
    'DLC %': 'D-line Conversion Percentage\n(D-line scores / D-line possessions)',
    'RZC %': 'Red Zone Conversion Percentage\n(Red zone scores / possessions within 20 yards of the endzone)',
    // Opponent stats
    'Opp\nC': 'Opponent Completions',
    'Opp\nT': 'Opponent Turnovers',
    'Opp\nH': 'Opponent Hucks',
    'Opp\nHT': 'Opponent Huck Turnovers\n(Opponent hucks attempted - hucks completed)',
    'Opp\nHLD': 'Opponent Holds\n(Points where opponent O-line scored)',
    'Opp\nB': 'Opponent Blocks',
    'Opp\nBRK': 'Opponent Breaks\n(Points where opponent D-line scored)'
};

// Column descriptions for Game Box Score table
export const gameBoxScoreColumnDescriptions: Record<string, string> = {
    name: 'Player name',
    jersey_number: 'Jersey Number',
    points_played: 'Points Played',
    o_points_played: 'O-Points Played',
    d_points_played: 'D-Points Played',
    assists: 'Assists',
    goals: 'Goals',
    blocks: 'Blocks',
    plus_minus: 'Plus/Minus',
    yards_received: 'Receiving Yards',
    yards_thrown: 'Throwing Yards',
    total_yards: 'Total Yards',
    completions: 'Completions',
    completion_percentage: 'Completion Percentage',
    hucks_completed: 'Hucks Completed',
    hucks_received: 'Hucks Received',
    huck_percentage: 'Huck Percentage',
    hockey_assists: 'Hockey Assists',
    turnovers: 'Throwaways',
    yards_per_completion: 'Throwing Yards per Completion',
    yards_per_reception: 'Receiving Yards per Reception',
    assists_per_turnover: 'Assists per Turnover',
    stalls: 'Stalls',
    callahans: 'Callahans',
    drops: 'Drops',
    // Short labels used in the table
    '#': 'Jersey Number',
    PP: 'Points Played',
    OPP: 'O-Points Played',
    DPP: 'D-Points Played',
    A: 'Assists',
    G: 'Goals',
    B: 'Blocks',
    '+/-': 'Plus/Minus',
    RY: 'Receiving Yards',
    TY: 'Throwing Yards',
    'TOT Y': 'Total Yards',
    C: 'Completions',
    'C%': 'Completion Percentage',
    H: 'Hucks Completed',
    HR: 'Hucks Received',
    'H%': 'Huck Percentage',
    HA: 'Hockey Assists',
    T: 'Throwaways',
    'TY/C': 'Throwing Yards per Completion',
    'RY/R': 'Receiving Yards per Reception',
    'AST/T': 'Assists per Turnover',
    S: 'Stalls',
    CAL: 'Callahans',
    D: 'Drops'
};

/**
 * Initialize tooltips for table headers
 * @param tableId - The ID of the table to initialize tooltips for
 * @param columnDescriptions - The column descriptions to use for tooltips
 */
export function initializeTableTooltips(tableId: string, columnDescriptions: Record<string, string>): void {
    const table = document.getElementById(tableId);
    if (!table) return;

    // Get or create tooltip element
    let tooltip = document.querySelector('.table-header-tooltip') as HTMLElement;
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.className = 'tooltip table-header-tooltip';
        tooltip.style.cssText = 'position: fixed; opacity: 0; visibility: hidden; pointer-events: none; z-index: 10001;';
        document.body.appendChild(tooltip);
    }

    // Find all table headers with sortable class or data-sort attribute
    const headers = table.querySelectorAll('th[data-sort], th.sortable');

    headers.forEach(header => {
        const th = header as HTMLElement;
        const textContent = th.textContent?.trim() || '';
        const dataSort = th.getAttribute('data-sort') || '';

        // For opponent stats (starting with "Opp"), check textContent first
        // Otherwise use data-sort attribute first
        const columnKey = textContent.startsWith('Opp') ? textContent : (dataSort || textContent);
        const description = columnDescriptions[columnKey] || columnDescriptions[textContent] || columnDescriptions[dataSort];

        if (description) {
            let tooltipTimeout: ReturnType<typeof setTimeout> | undefined;

            th.addEventListener('mouseenter', () => {
                clearTimeout(tooltipTimeout);

                tooltipTimeout = setTimeout(() => {
                    const rect = th.getBoundingClientRect();
                    tooltip.textContent = description;

                    // Position tooltip below the header
                    const tooltipTop = rect.bottom + 8;
                    let tooltipLeft = rect.left + rect.width / 2;

                    // Show tooltip temporarily to measure width
                    tooltip.style.visibility = 'hidden';
                    tooltip.style.display = 'block';
                    const tooltipWidth = tooltip.offsetWidth;
                    tooltip.style.display = '';

                    // Adjust position to keep within viewport
                    const halfWidth = tooltipWidth / 2;
                    if (tooltipLeft - halfWidth < 10) {
                        tooltipLeft = halfWidth + 10;
                    }
                    const viewportWidth = window.innerWidth;
                    if (tooltipLeft + halfWidth > viewportWidth - 10) {
                        tooltipLeft = viewportWidth - halfWidth - 10;
                    }

                    tooltip.style.top = `${tooltipTop}px`;
                    tooltip.style.left = `${tooltipLeft}px`;
                    tooltip.style.transform = 'translateX(-50%)';
                    tooltip.style.opacity = '1';
                    tooltip.style.visibility = 'visible';
                }, 300);
            });

            th.addEventListener('mouseleave', () => {
                clearTimeout(tooltipTimeout);
                tooltip.style.opacity = '0';
                tooltip.style.visibility = 'hidden';
            });
        }
    });
}

export default {
    playerColumnDescriptions,
    teamColumnDescriptions,
    gameBoxScoreColumnDescriptions,
    initializeTableTooltips
};