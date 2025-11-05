/**
 * User Data Cache Utility
 * Caches user profile and subscription data in localStorage for instant loading
 */

interface UserProfile {
  full_name: string | null;
  theme: string;
  default_season: number | null;
  notifications_enabled: boolean;
  email_digest_frequency: string;
  favorite_stat_categories: string[];
}

interface SubscriptionData {
  tier: string;
  status: string;
  queries_this_month: number;
  query_limit: number;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
}

interface PaymentMethod {
  id: string;
  type: string;
  card: {
    brand: string;
    last4: string;
    exp_month: number;
    exp_year: number;
  } | null;
  link: {
    email: string;
  } | null;
}

interface Invoice {
  id: string;
  date: number;
  amount_paid: number;
  currency: string;
  status: string;
  invoice_pdf: string;
  hosted_invoice_url: string;
}

interface CachedUserData {
  profile: UserProfile | null;
  subscription: SubscriptionData | null;
  paymentMethod: PaymentMethod | null;
  invoices: Invoice[];
  timestamp: number;
}

const CACHE_KEY = 'user-data-cache';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

/**
 * Get cached user data from localStorage
 * Returns null if cache is expired or doesn't exist
 */
export function getCachedUserData(): CachedUserData | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;

    const data = JSON.parse(cached) as CachedUserData;
    const now = Date.now();

    // Check if cache is still valid
    if (now - data.timestamp > CACHE_DURATION) {
      // Cache expired, remove it
      localStorage.removeItem(CACHE_KEY);
      return null;
    }

    return data;
  } catch (error) {
    console.error('Failed to read user cache:', error);
    return null;
  }
}

/**
 * Cache user data in localStorage
 */
export function setCachedUserData(data: Partial<CachedUserData>): void {
  try {
    // Get existing cache or create new
    const existing = getCachedUserData() || {
      profile: null,
      subscription: null,
      paymentMethod: null,
      invoices: [],
      timestamp: Date.now(),
    };

    // Merge new data with existing
    const updated: CachedUserData = {
      ...existing,
      ...data,
      timestamp: Date.now(), // Always update timestamp
    };

    localStorage.setItem(CACHE_KEY, JSON.stringify(updated));
  } catch (error) {
    console.error('Failed to cache user data:', error);
  }
}

/**
 * Clear cached user data (call on logout)
 */
export function clearCachedUserData(): void {
  try {
    localStorage.removeItem(CACHE_KEY);
  } catch (error) {
    console.error('Failed to clear user cache:', error);
  }
}

/**
 * Get cached profile only
 */
export function getCachedProfile(): UserProfile | null {
  const cache = getCachedUserData();
  return cache?.profile || null;
}

/**
 * Get cached subscription only
 */
export function getCachedSubscription(): SubscriptionData | null {
  const cache = getCachedUserData();
  return cache?.subscription || null;
}

/**
 * Get cached payment method only
 */
export function getCachedPaymentMethod(): PaymentMethod | null {
  const cache = getCachedUserData();
  return cache?.paymentMethod || null;
}

/**
 * Get cached invoices only
 */
export function getCachedInvoices(): Invoice[] {
  const cache = getCachedUserData();
  return cache?.invoices || [];
}

/**
 * Update only profile in cache
 */
export function updateCachedProfile(profile: UserProfile): void {
  setCachedUserData({ profile });
}

/**
 * Update only subscription in cache
 */
export function updateCachedSubscription(subscription: SubscriptionData): void {
  setCachedUserData({ subscription });
}

/**
 * Update only payment method in cache
 */
export function updateCachedPaymentMethod(paymentMethod: PaymentMethod | null): void {
  setCachedUserData({ paymentMethod });
}

/**
 * Update only invoices in cache
 */
export function updateCachedInvoices(invoices: Invoice[]): void {
  setCachedUserData({ invoices });
}
