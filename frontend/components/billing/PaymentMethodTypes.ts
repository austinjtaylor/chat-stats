/**
 * TypeScript types and interfaces for Payment Method Modal
 */

/**
 * Payment method card details
 */
export interface PaymentMethodCard {
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
}

/**
 * Payment method Link details
 */
export interface PaymentMethodLink {
  email: string;
}

/**
 * Billing address
 */
export interface BillingAddress {
  line1?: string | null;
  line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
}

/**
 * Billing details
 */
export interface BillingDetails {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: BillingAddress | null;
}

/**
 * Current payment method
 */
export interface CurrentPaymentMethod {
  id: string;
  type?: string; // 'card', 'link', etc.
  card: PaymentMethodCard | null;
  link?: PaymentMethodLink | null;
  billing_details?: BillingDetails | null;
}

/**
 * Options for PaymentMethodModal constructor
 */
export interface PaymentMethodModalOptions {
  currentPaymentMethod?: CurrentPaymentMethod | null;
  userEmail: string;
  userName?: string;
  accessToken: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

/**
 * Modal view state
 */
export enum ModalView {
  EXISTING_PAYMENT = 'existing_payment',
  NEW_PAYMENT = 'new_payment',
  EDIT_CARD = 'edit_card',
}

/**
 * Validation error field names
 */
export type ValidationErrorField =
  | 'cardholder-name'
  | 'address-line1'
  | 'city'
  | 'state'
  | 'zip-code';

/**
 * Validation errors map
 */
export type ValidationErrors = Map<ValidationErrorField, string>;

/**
 * Modal state interface
 */
export interface IModalState {
  currentView: ModalView;
  useExisting: boolean;
  isEditingMode: boolean;
  showNewCardForm: boolean;
  isEditingCard: boolean;
  hasCardFieldsChanged: boolean;
  showAdditionalAddressFields: boolean;
  isProcessingLinkAuth: boolean;
  validationErrors: ValidationErrors;
}
