/**
 * Table Header Tooltips Utility
 * Provides tooltip descriptions for all table column headers
 */

// Column descriptions for Players table
export const playerColumnDescriptions: Record<string, string> = {
    full_name: 'Player name',
    games_played: 'Games Played',
    total_points_played: 'Points Played',
    possessions: 'Possessions',
    score_total: 'Scores',
    total_assists: 'Assists',
    total_goals: 'Goals',
    total_blocks: 'Blocks',
    calculated_plus_minus: 'Plus/Minus',
    total_completions: 'Completions',
    completion_percentage: 'Completion Percentage',
    total_yards: 'Total Yards',
    total_yards_thrown: 'Throwing Yards',
    total_yards_received: 'Receiving Yards',
    offensive_efficiency: 'Offensive Efficiency',
    total_hockey_assists: 'Hockey Assists',
    total_throwaways: 'Turnovers',
    yards_per_turn: 'Yards per Turn',
    total_stalls: 'Stalls',
    total_drops: 'Drops',
    total_callahans: 'Callahans',
    total_hucks_completed: 'Hucks Completed',
    total_hucks_received: 'Hucks Received',
    huck_percentage: 'Huck Percentage',
    total_pulls: 'Pulls',
    total_o_points_played: 'O-Points Played',
    total_d_points_played: 'D-Points Played',
    minutes_played: 'Minutes Played',
    // Short labels used in the table
    GP: 'Games Played',
    PP: 'Points Played',
    POS: 'Possessions',
    S: 'Scores',
    A: 'Assists',
    G: 'Goals',
    B: 'Blocks',
    '+/-': 'Plus/Minus',
    C: 'Completions',
    'C%': 'Completion Percentage',
    'TOT Y': 'Total Yards',
    TY: 'Throwing Yards',
    RY: 'Receiving Yards',
    OEFF: 'Offensive Efficiency',
    HA: 'Hockey Assists',
    T: 'Turnovers',
    'Y/T': 'Yards per Turn',
    D: 'Drops',
    CAL: 'Callahans',
    H: 'Hucks Completed',
    HR: 'Hucks Received',
    'H%': 'Huck Percentage',
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
    huck_percentage: 'Huck Percentage',
    hold_percentage: 'Hold Percentage',
    o_line_conversion: 'O-Line Conversion',
    blocks: 'Blocks',
    break_percentage: 'Break Percentage',
    d_line_conversion: 'D-Line Conversion',
    red_zone_conversion: 'Red Zone Conversion',
    // Short labels used in the table
    G: 'Games',
    W: 'Wins',
    L: 'Losses',
    S: 'Scores',
    SA: 'Scores Against',
    C: 'Completions',
    T: 'Turnovers',
    'C%': 'Completion Percentage',
    H: 'Hucks',
    'H%': 'Huck Percentage',
    'HLD %': 'Hold Percentage',
    'OLC %': 'O-Line Conversion',
    B: 'Blocks',
    'BRK %': 'Break Percentage',
    'DLC %': 'D-Line Conversion',
    'RZC %': 'Red Zone Conversion',
    // Opponent stats
    'Opp S': 'Opponent Scores',
    'Opp SA': 'Opponent Scores Against',
    'Opp C': 'Opponent Completions',
    'Opp T': 'Opponent Turnovers',
    'Opp C%': 'Opponent Completion Percentage',
    'Opp H': 'Opponent Hucks',
    'Opp H%': 'Opponent Huck Percentage',
    'Opp HLD %': 'Opponent Hold Percentage',
    'Opp OLC %': 'Opponent O-Line Conversion',
    'Opp B': 'Opponent Blocks',
    'Opp BRK %': 'Opponent Break Percentage',
    'Opp DLC %': 'Opponent D-Line Conversion',
    'Opp RZC %': 'Opponent Red Zone Conversion'
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
    turnovers: 'Turnovers',
    yards_per_turn: 'Yards per Turn',
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
    T: 'Turnovers',
    'Y/T': 'Yards per Turn',
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
        const columnKey = th.getAttribute('data-sort') || th.textContent?.trim() || '';
        const description = columnDescriptions[columnKey] || columnDescriptions[th.textContent?.trim() || ''];

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