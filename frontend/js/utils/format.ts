/**
 * Data Formatting Utilities - TypeScript version
 */

type DateFormat = 'short' | 'long' | 'time' | 'datetime';
type StatType = 'FG%' | 'FT%' | '3P%' | 'TS%' | 'HOLD%' | 'BREAK%' | 'PPG' | 'APG' | 'RPG' | 'SPG' | 'BPG' | 'TOPG' | string;

const Format = {
    /**
     * Format number with commas
     */
    number(value: number | null | undefined, decimals: number = 0): string {
        if (value == null || isNaN(value)) return '-';
        return Number(value).toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    },

    /**
     * Format percentage
     */
    percentage(value: number | null | undefined, decimals: number = 1): string {
        if (value == null || isNaN(value)) return '-';
        return `${(value * 100).toFixed(decimals)}%`;
    },

    /**
     * Format currency
     */
    currency(value: number | null | undefined, currency: string = 'USD'): string {
        if (value == null || isNaN(value)) return '-';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(value);
    },

    /**
     * Format date
     */
    date(value: string | Date | null | undefined, format: DateFormat = 'short'): string {
        if (!value) return '-';
        const date = new Date(value);

        if (format === 'short') {
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        } else if (format === 'long') {
            return date.toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
                year: 'numeric'
            });
        } else if (format === 'time') {
            return date.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            });
        } else if (format === 'datetime') {
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            });
        }

        return date.toLocaleDateString('en-US');
    },

    /**
     * Format relative time
     */
    relativeTime(value: string | Date | null | undefined): string {
        if (!value) return '-';
        const date = new Date(value);
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) {
            return `${days} day${days > 1 ? 's' : ''} ago`;
        } else if (hours > 0) {
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else if (minutes > 0) {
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else {
            return 'Just now';
        }
    },

    /**
     * Format player name
     */
    playerName(firstName: string | null | undefined, lastName?: string | null | undefined): string {
        // Handle both formats: full name as first param, or first/last as separate params
        if (arguments.length === 1) {
            return firstName || '-';
        }

        if (!firstName && !lastName) return '-';
        if (!firstName) return lastName || '-';
        if (!lastName) return firstName;
        return `${firstName} ${lastName}`;
    },

    /**
     * Format team name
     */
    teamName(city: string | null | undefined, name?: string | null | undefined): string {
        // Handle both formats: full name as first param, or city/name as separate params
        if (arguments.length === 1) {
            return city || '-';
        }

        if (!city && !name) return '-';
        if (!city) return name || '-';
        if (!name) return city;
        return `${city} ${name}`;
    },

    /**
     * Format position
     */
    position(position: string | null | undefined): string {
        const positions: Record<string, string> = {
            'C': 'Cutter',
            'H': 'Handler',
            'D': 'Defender',
            'HY': 'Hybrid'
        };
        return positions[position || ''] || position || '-';
    },

    /**
     * Format game score
     */
    gameScore(homeScore: number | null | undefined, awayScore: number | null | undefined): string {
        if (homeScore == null || awayScore == null) return '-';
        return `${homeScore} - ${awayScore}`;
    },

    /**
     * Format stat value based on type
     */
    statValue(value: number | null | undefined, statType?: StatType, isPercentage?: boolean): string {
        if (value == null) return '-';

        // Handle the two-parameter version for backward compatibility
        if (typeof statType === 'boolean') {
            isPercentage = statType;
            statType = undefined;
        }

        // If isPercentage is explicitly set, use that
        if (isPercentage !== undefined) {
            return isPercentage ? this.percentage(value, 1) : this.number(value, 0);
        }

        // Otherwise use statType if provided
        if (statType) {
            const percentageStats = ['FG%', 'FT%', '3P%', 'TS%', 'HOLD%', 'BREAK%'];
            const decimalStats = ['PPG', 'APG', 'RPG', 'SPG', 'BPG', 'TOPG'];

            if (percentageStats.includes(statType)) {
                return this.percentage(value, 1);
            } else if (decimalStats.includes(statType)) {
                return this.number(value, 1);
            }
        }

        return this.number(value, 0);
    },

    /**
     * Format duration (in seconds)
     */
    duration(seconds: number | null | undefined): string {
        if (!seconds || seconds < 0) return '-';

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    },

    /**
     * Format time (minutes and optional seconds)
     */
    time(minutes: number | null | undefined, seconds?: number): string {
        if (minutes == null) return '-';

        if (seconds !== undefined) {
            return `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }

        // If only minutes provided, convert to MM:SS format
        const mins = Math.floor(minutes);
        const secs = Math.round((minutes - mins) * 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    },

    /**
     * Format file size
     */
    fileSize(bytes: number | null | undefined): string {
        if (!bytes || bytes === 0) return '0 B';

        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));

        return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
    },

    /**
     * Pluralize word
     */
    pluralize(count: number, singular: string, plural?: string | null): string {
        if (count === 1) return `${count} ${singular}`;
        return `${count} ${plural || singular + 's'}`;
    },

    /**
     * Truncate text
     */
    truncate(text: string | null | undefined, maxLength: number = 50, ellipsis: string = '...'): string {
        if (!text || text.length <= maxLength) return text || '';
        return text.substring(0, maxLength - ellipsis.length) + ellipsis;
    },

    /**
     * Format ordinal number
     */
    ordinal(number: number | null | undefined): string {
        if (!number || isNaN(number)) return '-';

        const suffixes = ['th', 'st', 'nd', 'rd'];
        const v = number % 100;

        return number + (suffixes[(v - 20) % 10] || suffixes[v] || suffixes[0]);
    },

    /**
     * Format win-loss record
     */
    record(wins: number | null | undefined, losses: number | null | undefined): string {
        if (wins == null || losses == null) return '-';
        return `${wins}-${losses}`;
    },

    /**
     * Format plus/minus
     */
    plusMinus(value: number | null | undefined): string {
        if (value == null || isNaN(value)) return '-';
        if (value > 0) return `+${value}`;
        return value.toString();
    }
};

// ES Module exports
export { Format };
export default Format;

// Also export individual functions for convenience
export const { number, percentage, currency, date, relativeTime, playerName, teamName, position, gameScore, statValue, duration, time, fileSize, pluralize, truncate, ordinal, record, plusMinus } = Format;

// For backward compatibility with script tags
if (typeof window !== 'undefined') {
    (window as any).Format = Format;
}