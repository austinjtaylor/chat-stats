/**
 * Stripe.js integration
 * Handles Stripe Elements and payment method tokenization
 */

import { loadStripe, Stripe, StripeElements, StripePaymentElement } from '@stripe/stripe-js';

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
 * Create Stripe Elements instance for Payment Element
 * Always uses setup mode for collecting payment methods
 */
export async function createStripeElements(): Promise<StripeElements | null> {
  const stripe = await getStripe();
  if (!stripe) return null;

  // Setup mode configuration for Payment Element
  const options = {
    mode: 'setup' as const,
    currency: 'usd',
    setupFutureUsage: 'off_session' as const,
    paymentMethodTypes: ['card', 'link'], // Only allow card and Link payment methods
    appearance: {
      theme: 'night' as const,
      variables: {
        colorPrimary: '#5e8d90',
        colorBackground: '#2a2e36',
        colorText: '#e4e4e7',
        colorDanger: '#ef4444',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        spacingUnit: '4px',
        borderRadius: '6px',
        focusBoxShadow: 'none',
        focusOutline: 'none',
        boxShadow: 'none',
      },
      rules: {
        '.Input': {
          backgroundColor: '#2a2e36',
          border: '1px solid #3f3f46',
          color: '#e4e4e7',
          boxShadow: 'none',
        },
        '.Input:focus': {
          border: '1px solid #5e8d90',
          boxShadow: 'none',
          outline: 'none',
        },
        '.Label': {
          color: '#e4e4e7',
          fontWeight: '500',
        },
        '.Block': {
          boxShadow: 'none',
        },
        '.PickerItem': {
          boxShadow: 'none',
          border: '1px solid #3f3f46',
        },
        '.PickerItem:hover': {
          boxShadow: 'none',
          border: '1px solid #3f3f46',
        },
        '.PickerItem--selected': {
          boxShadow: 'none',
          border: '1px solid #3f3f46',
        },
        '.Tab': {
          boxShadow: 'none',
        },
        '.Tab:hover': {
          boxShadow: 'none',
        },
        '.Tab:focus': {
          boxShadow: 'none',
        },
        '.Tab--selected': {
          boxShadow: 'none',
        },
        '.TabLabel': {
          boxShadow: 'none',
        },
        '.RedactedText': {
          boxShadow: 'none',
        },
        '.RedactedCardNumber': {
          boxShadow: 'none',
        },
        '.SavedPaymentMethod': {
          boxShadow: 'none',
          border: '1px solid #3f3f46',
        },
      },
    }
  };

  return stripe.elements(options);
}

/**
 * Create a Payment Element
 * This unified element handles cards, Link, and other payment methods
 */
export function createPaymentElement(
  elements: StripeElements,
  options?: {
    defaultValues?: {
      billingDetails?: {
        name?: string;
        email?: string;
        address?: {
          line1?: string;
          line2?: string;
          city?: string;
          state?: string;
          postal_code?: string;
          country?: string;
        };
      };
    };
  }
): StripePaymentElement {
  return elements.create('payment', {
    layout: 'tabs',
    terms: {
      card: 'never', // Hide the mandate text for cards
    },
    fields: {
      billingDetails: 'never', // Don't collect billing details - we handle this separately
    },
    ...options,
  });
}

/**
 * Confirm setup with Payment Element
 * This should be called on form submission
 */
export async function confirmSetup(
  elements: StripeElements,
  clientSecret: string,
  returnUrl: string
): Promise<{ error?: any }> {
  const stripe = await getStripe();
  if (!stripe) {
    return { error: { message: 'Stripe not initialized' } };
  }

  const { error } = await stripe.confirmSetup({
    elements,
    clientSecret,
    confirmParams: {
      return_url: returnUrl,
    },
  });

  return { error };
}

/**
 * Default options for Payment Element
 */
export const paymentElementOptions = {
  layout: 'tabs' as const,
};
