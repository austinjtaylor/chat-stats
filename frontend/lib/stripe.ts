/**
 * Stripe.js integration
 * Handles Stripe Elements and payment method tokenization
 */

import { loadStripe, Stripe, StripeElements, StripeCardElement } from '@stripe/stripe-js';

// Get Stripe publishable key from environment
const STRIPE_PUBLISHABLE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '';

let stripePromise: Promise<Stripe | null> | null = null;

/**
 * Get Stripe instance (singleton)
 */
export function getStripe(): Promise<Stripe | null> {
  if (!stripePromise) {
    if (!STRIPE_PUBLISHABLE_KEY) {
      console.error('VITE_STRIPE_PUBLISHABLE_KEY not configured');
      return Promise.resolve(null);
    }
    stripePromise = loadStripe(STRIPE_PUBLISHABLE_KEY);
  }
  return stripePromise;
}

/**
 * Create Stripe Elements instance
 */
export async function createStripeElements(): Promise<StripeElements | null> {
  const stripe = await getStripe();
  if (!stripe) return null;

  return stripe.elements();
}

/**
 * Create a payment method from card element
 */
export async function createPaymentMethod(
  cardElement: StripeCardElement,
  billingDetails: {
    name: string;
    email?: string;
    address?: {
      line1?: string;
      city?: string;
      state?: string;
      postal_code?: string;
      country?: string;
    };
  }
): Promise<{ paymentMethod?: any; error?: any }> {
  const stripe = await getStripe();
  if (!stripe) {
    return { error: { message: 'Stripe not initialized' } };
  }

  const { paymentMethod, error } = await stripe.createPaymentMethod({
    type: 'card',
    card: cardElement,
    billing_details: billingDetails,
  });

  return { paymentMethod, error };
}

/**
 * Card element styling options
 */
export const cardElementOptions = {
  style: {
    base: {
      fontSize: '16px',
      color: '#e4e4e7',
      backgroundColor: 'transparent',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      '::placeholder': {
        color: '#71717a',
      },
      iconColor: '#71717a',
    },
    invalid: {
      color: '#ef4444',
      iconColor: '#ef4444',
    },
  },
  hidePostalCode: false,
};
