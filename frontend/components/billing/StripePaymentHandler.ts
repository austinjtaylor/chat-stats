/**
 * Stripe Payment Integration Handler
 * Handles Stripe Payment Element initialization and payment method operations
 */

import { StripePaymentElement, StripeElements } from '@stripe/stripe-js';
import { createStripeElements, createPaymentElement } from '../../lib/stripe';
import { PaymentMethodModalOptions } from './PaymentMethodTypes';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Handles Stripe Payment Element and payment method operations
 */
export class StripePaymentHandler {
  private paymentElement: StripePaymentElement | null = null;
  private elements: StripeElements | null = null;
  private options: PaymentMethodModalOptions;
  private onLinkAuthComplete?: () => Promise<void>;
  private onPaymentElementReady?: () => void;

  constructor(options: PaymentMethodModalOptions) {
    this.options = options;
  }

  /**
   * Initialize Stripe Payment Element
   */
  async initialize(
    container: HTMLElement,
    onReady?: () => void,
    onLinkAuth?: () => Promise<void>
  ): Promise<boolean> {
    this.onPaymentElementReady = onReady;
    this.onLinkAuthComplete = onLinkAuth;

    // Create Elements instance
    this.elements = await createStripeElements();
    if (!this.elements) {
      console.error('Failed to initialize Stripe Elements');
      return false;
    }

    // Create Payment Element with Link support
    this.paymentElement = createPaymentElement(this.elements, {
      defaultValues: {
        billingDetails: {
          name: this.options.userName || '',
        },
      },
    });

    // Mount Payment Element
    this.paymentElement.mount(container);

    // Attach event listeners
    this.paymentElement.on('ready', () => {
      if (this.onPaymentElementReady) {
        this.onPaymentElementReady();
      }
    });

    this.paymentElement.on('change', async (event) => {
      await this.handlePaymentElementChange(event);
    });

    return true;
  }

  /**
   * Handle Payment Element change event (detects Link authentication)
   */
  private async handlePaymentElementChange(event: any): Promise<void> {
    console.log('Payment Element change event:', event);

    // Check if Link authentication completed
    if (event.complete && this.onLinkAuthComplete) {
      console.log('Payment Element is complete - triggering Link auth handler...');

      // Add delay to ensure Stripe has processed the Link authentication
      setTimeout(async () => {
        if (this.onLinkAuthComplete) {
          await this.onLinkAuthComplete();
        }
      }, 300);
    }
  }

  /**
   * Submit the Payment Element for validation
   */
  async submit(): Promise<{ error?: any }> {
    if (!this.elements) {
      return { error: { message: 'Payment Element not initialized' } };
    }

    return await this.elements.submit();
  }

  /**
   * Create a SetupIntent
   */
  async createSetupIntent(accessToken: string): Promise<{ client_secret?: string; error?: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/stripe/create-setup-intent`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        return { error: 'Failed to create setup intent' };
      }

      const data = await response.json();
      return { client_secret: data.client_secret };
    } catch (error) {
      console.error('Error creating setup intent:', error);
      return { error: 'Failed to create setup intent' };
    }
  }

  /**
   * Confirm SetupIntent and return payment method ID
   */
  async confirmSetup(
    clientSecret: string,
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
    }
  ): Promise<{ paymentMethodId?: string; error?: string }> {
    if (!this.elements) {
      return { error: 'Payment Element not initialized' };
    }

    try {
      const { getStripe } = await import('../../lib/stripe');
      const stripe = await getStripe();

      if (!stripe) {
        return { error: 'Stripe not initialized' };
      }

      console.log('Confirming SetupIntent with billing details:', billingDetails);

      // Build confirmParams with billing details if provided
      const confirmParams: any = {
        elements: this.elements,
        clientSecret: clientSecret,
        redirect: 'if_required',
      };

      // Add billing details if provided
      if (billingDetails) {
        confirmParams.confirmParams = {
          payment_method_data: {
            billing_details: billingDetails,
          },
        };
      }

      const { error: confirmError, setupIntent } = await stripe.confirmSetup(confirmParams);

      if (confirmError) {
        return { error: confirmError.message };
      }

      if (!setupIntent || !setupIntent.payment_method) {
        return { error: 'No payment method was attached to the setup' };
      }

      // Extract payment method ID
      const paymentMethodId = typeof setupIntent.payment_method === 'string'
        ? setupIntent.payment_method
        : setupIntent.payment_method.id;

      console.log('Extracted payment method ID from SetupIntent:', paymentMethodId);

      return { paymentMethodId };
    } catch (error: any) {
      console.error('Error confirming setup:', error);
      return { error: error.message || 'Failed to confirm setup' };
    }
  }

  /**
   * Update payment method on backend
   */
  async updatePaymentMethod(
    paymentMethodId: string,
    accessToken: string
  ): Promise<{ success: boolean; error?: string }> {
    try {
      console.log('updatePaymentMethod called with:', paymentMethodId);

      const response = await fetch(`${API_BASE_URL}/api/stripe/update-payment-method`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          payment_method_id: paymentMethodId,
        }),
      });

      console.log('Backend response status:', response.status, response.statusText);

      if (!response.ok) {
        const error = await response.json();
        console.error('Backend returned error:', error);
        return { success: false, error: error.detail || 'Failed to update payment method' };
      }

      const result = await response.json();
      console.log('Backend response:', result);

      return { success: true };
    } catch (error: any) {
      console.error('Error updating payment method:', error);
      return { success: false, error: error.message || 'Failed to update payment method' };
    }
  }

  /**
   * Get Elements instance (for advanced use cases)
   */
  getElements(): StripeElements | null {
    return this.elements;
  }

  /**
   * Clean up Stripe elements
   */
  destroy(): void {
    if (this.paymentElement) {
      this.paymentElement.destroy();
      this.paymentElement = null;
    }
    if (this.elements) {
      this.elements = null;
    }
  }
}
