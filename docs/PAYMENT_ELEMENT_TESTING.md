# Payment Element Integration Testing Checklist

This document provides a comprehensive testing checklist for the Stripe Payment Element integration. Use this to verify all functionality works correctly before deploying to production.

**Last Updated**: October 2024
**Feature**: Stripe Payment Element Backend Integration

---

## Quick Reference

### Test Cards

```
✅ Success (No 3DS):
4242 4242 4242 4242 - Visa
5555 5555 5555 4444 - Mastercard

✅ Success (Requires 3DS):
4000 0027 6000 3184 - Visa (3D Secure 2)
4000 0025 0000 3155 - Mastercard (3D Secure 2)

❌ Declined:
4000 0000 0000 0002 - Generic decline
4000 0000 0000 9995 - Insufficient funds
4000 0000 0000 9987 - Lost card

⚠️ Test Expiration: Any future date (e.g., 12/25)
⚠️ Test CVC: Any 3 digits (e.g., 123)
⚠️ Test ZIP: Any valid ZIP (e.g., 94102, 10001)
```

---

## 1. Backend API Endpoint Testing

### 1.1 `/api/stripe/create-setup-intent` (NEW)

#### Authentication Tests
- [ ] **Valid auth token**: Returns 200 with `client_secret`
- [ ] **No auth token**: Returns 401 Unauthorized
- [ ] **Expired auth token**: Returns 401 Unauthorized
- [ ] **Invalid auth token**: Returns 401 Unauthorized

#### Valid Request Tests
- [ ] **New user with Stripe customer**: Creates SetupIntent successfully
- [ ] **Returns valid client_secret**: String starts with `seti_`
- [ ] **Client secret can be used**: Works with `stripe.confirmSetup()`

#### Error Cases
- [ ] **No Stripe customer ID**: Returns 400 with helpful error message
- [ ] **Stripe API failure**: Returns 400 with error details
- [ ] **Database query fails**: Handles gracefully

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/stripe/create-setup-intent \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "client_secret": "seti_1ABC123_secret_DEF456"
}
```

---

### 1.2 `/api/stripe/update-payment-method` (EXISTING)

#### Success Cases
- [ ] **Valid payment method ID**: Updates customer default successfully
- [ ] **Payment method attaches**: Visible in Stripe Dashboard
- [ ] **invoice_settings updated**: Default payment method set
- [ ] **Returns success message**: Status 200

#### Error Cases
- [ ] **Invalid payment method ID**: Returns 400
- [ ] **Payment method from different customer**: Returns 400 (security)
- [ ] **Missing payment_method_id**: Returns 400
- [ ] **Stripe API error**: Returns 400 with error message

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/stripe/update-payment-method \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payment_method_id": "pm_1ABC123"}'
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Payment method updated successfully"
}
```

---

### 1.3 `/api/stripe/payment-methods` (EXISTING)

#### Success Cases
- [ ] **After adding payment method**: New card appears
- [ ] **Card details correct**: brand, last4, exp_month, exp_year
- [ ] **No payment method**: Returns `{"payment_method": null}`
- [ ] **Multiple updates**: Always shows latest payment method

#### Response Validation
- [ ] **Correct structure**: Contains id, type, card object
- [ ] **Card object**: brand, last4, exp_month, exp_year fields present
- [ ] **Expiration format**: Numeric values (not strings)

**Example Request:**
```bash
curl http://localhost:8000/api/stripe/payment-methods \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "payment_method": {
    "id": "pm_1ABC123",
    "type": "card",
    "card": {
      "brand": "visa",
      "last4": "4242",
      "exp_month": 12,
      "exp_year": 2025
    }
  }
}
```

---

## 2. Frontend Payment Modal Testing

### 2.1 Modal Display

#### With Existing Payment Method
- [ ] **Modal opens**: Displays on click
- [ ] **Shows card details**: "Use Visa •••• 4242"
- [ ] **Shows expiration**: "Expires 12/2025" format
- [ ] **Change button visible**: Allows switching payment methods
- [ ] **Styling correct**: Matches design specs

#### Without Existing Payment Method
- [ ] **Payment Element shows immediately**: No "Use existing" option
- [ ] **Form fields visible**: Name, Country, Address, ZIP
- [ ] **Stripe Element loads**: Card input appears
- [ ] **No existing card option**: Only new card form

#### Modal Behavior
- [ ] **Close on Cancel**: Modal closes
- [ ] **Close on Escape**: Keyboard shortcut works
- [ ] **Close on overlay click**: Clicking outside closes modal
- [ ] **Prevents body scroll**: Page doesn't scroll when modal open

---

### 2.2 Payment Element Integration

#### Stripe Loading
- [ ] **Payment Element renders**: Appears in container
- [ ] **Stripe.js loads**: No console errors
- [ ] **Element styling**: Matches app theme
- [ ] **Responsive**: Works on mobile

#### Form Interactions
- [ ] **Card number input**: Accepts test card numbers
- [ ] **Expiration input**: Accepts MM/YY format
- [ ] **CVC input**: Accepts 3-4 digits
- [ ] **ZIP input**: Accepts postal codes
- [ ] **Name pre-populated**: User's name appears
- [ ] **Email pre-populated**: User's email appears (in Stripe Element)

#### Link Payment Method
- [ ] **Link tab appears**: If user has Link account
- [ ] **Link autofills**: Email/phone autofill works
- [ ] **Additional fields hide**: When Link selected
- [ ] **Additional fields show**: When Card selected

---

### 2.3 Form Validation

#### Required Fields
- [ ] **Empty name**: Shows "This field is incomplete."
- [ ] **Empty address**: Shows error message
- [ ] **Empty city**: Shows error when Card selected
- [ ] **Empty state**: Shows error when Card selected
- [ ] **Empty ZIP**: Shows error when Card selected
- [ ] **Invalid card**: Stripe shows inline error

#### Field Errors
- [ ] **Red border**: Applied to invalid fields
- [ ] **Error text**: Displayed below field
- [ ] **Error clears**: When field is corrected
- [ ] **Submit prevented**: Cannot submit with errors

---

## 3. Payment Flow Testing

### 3.1 Add First Payment Method (New User)

- [ ] 1. Navigate to Settings → Billing
- [ ] 2. Click "Update payment method"
- [ ] 3. Modal shows Payment Element (no existing card)
- [ ] 4. Enter name: "Test User"
- [ ] 5. Enter address: "123 Main St"
- [ ] 6. Enter city: "San Francisco"
- [ ] 7. Select state: "California"
- [ ] 8. Enter ZIP: "94102"
- [ ] 9. Enter card: 4242 4242 4242 4242
- [ ] 10. Enter expiration: 12/25
- [ ] 11. Enter CVC: 123
- [ ] 12. Click "Update"
- [ ] 13. Loading spinner appears
- [ ] 14. Modal closes on success
- [ ] 15. Settings page refreshes
- [ ] 16. New card appears: "Visa •••• 4242"

**Expected Result**: Payment method saved successfully

---

### 3.2 Update Existing Payment Method

- [ ] 1. User has existing payment method
- [ ] 2. Open payment modal
- [ ] 3. See "Use Visa •••• 4242"
- [ ] 4. Click "Change"
- [ ] 5. "New payment method" button appears
- [ ] 6. Click "New payment method"
- [ ] 7. Payment Element appears
- [ ] 8. Enter new card: 5555 5555 5555 4444
- [ ] 9. Fill required fields
- [ ] 10. Click "Update"
- [ ] 11. Success
- [ ] 12. Old card replaced with "Mastercard •••• 4444"

**Expected Result**: Payment method updated successfully

---

### 3.3 3D Secure Flow

- [ ] 1. Open payment modal
- [ ] 2. Click "New payment method"
- [ ] 3. Enter 3DS test card: 4000 0027 6000 3184
- [ ] 4. Fill required fields
- [ ] 5. Click "Update"
- [ ] 6. 3D Secure modal appears inline
- [ ] 7. Click "Complete" (in test modal)
- [ ] 8. Authentication succeeds
- [ ] 9. Payment method saves
- [ ] 10. Modal closes

**Expected Result**: 3DS handled inline, no page redirect

---

### 3.4 Use Link Payment Method

- [ ] 1. Open payment modal
- [ ] 2. Click "Link" tab in Payment Element
- [ ] 3. Enter email/phone
- [ ] 4. Receive Link code (in test mode)
- [ ] 5. Enter code
- [ ] 6. Address fields hide (Link has billing info)
- [ ] 7. Click "Update"
- [ ] 8. Payment method saves via Link

**Expected Result**: Link payment method saved

---

### 3.5 Cancel During Entry

- [ ] 1. Open payment modal
- [ ] 2. Start entering card details
- [ ] 3. Click "Cancel"
- [ ] 4. Modal closes
- [ ] 5. No payment method created
- [ ] 6. No API calls made

**Expected Result**: Safe cancellation

---

## 4. Error Handling Testing

### 4.1 Network Errors

- [ ] **Backend unreachable**: User-friendly error message
- [ ] **Timeout**: Shows timeout error
- [ ] **500 error**: Shows server error message
- [ ] **CORS error**: Handled gracefully

**Test Method**: Disconnect network mid-flow

---

### 4.2 Stripe Errors

- [ ] **Card declined**: Shows decline reason
- [ ] **Invalid card**: Shows "Invalid card number"
- [ ] **Expired card**: Shows expiration error
- [ ] **CVC check failed**: Shows CVC error
- [ ] **Insufficient funds**: Shows "Insufficient funds"
- [ ] **Lost/stolen card**: Shows appropriate error

**Test Cards**: Use decline test cards listed above

---

### 4.3 Validation Errors

- [ ] **Empty required field**: Inline error
- [ ] **Invalid ZIP format**: Validation error
- [ ] **Multiple errors**: All shown simultaneously
- [ ] **Error persists**: Until field corrected
- [ ] **Re-render preserves**: Entered data

---

### 4.4 State Management Errors

- [ ] **Loading state stuck**: Timeout releases button
- [ ] **Duplicate submission**: Button disabled prevents
- [ ] **Modal closed during processing**: Request completes or cancels
- [ ] **Session expired**: Shows auth error

---

## 5. Integration Testing

### 5.1 Complete User Journey - First Subscription

- [ ] 1. New user signs up
- [ ] 2. No existing payment method
- [ ] 3. Subscribe to Pro plan
- [ ] 4. Payment modal auto-opens
- [ ] 5. Enter payment details
- [ ] 6. Save payment method
- [ ] 7. Subscription created
- [ ] 8. Payment method attached to subscription
- [ ] 9. Settings shows active subscription
- [ ] 10. Payment method visible in settings

---

### 5.2 Complete User Journey - Subscription Renewal

- [ ] 1. User has active subscription
- [ ] 2. Has payment method on file
- [ ] 3. Subscription renews monthly
- [ ] 4. Stripe charges saved payment method
- [ ] 5. Invoice generated
- [ ] 6. User receives receipt
- [ ] 7. Subscription remains active

---

### 5.3 Subscription Context

- [ ] **Pro subscription**: Can update payment method
- [ ] **Free tier**: Can add payment method for future subscription
- [ ] **Cancelled subscription**: Can update payment method
- [ ] **Past due**: Can update failed payment method

---

## 6. Stripe Dashboard Verification

After each successful payment method update, verify in Stripe Dashboard:

### Customer Object
- [ ] **Payment method attached**: Visible under "Payment methods"
- [ ] **Default payment method set**: In invoice_settings
- [ ] **Customer email correct**: Matches user email
- [ ] **Metadata present**: user_id stored

### SetupIntent
- [ ] **Status: succeeded**: Payment method attached
- [ ] **Customer linked**: Correct customer_id
- [ ] **Payment method created**: New pm_xxx ID
- [ ] **Usage: off_session**: For future payments

### Payment Method
- [ ] **Type: card**: Correct payment type
- [ ] **Card details**: brand, last4, exp_month, exp_year
- [ ] **Billing details**: Name, address populated
- [ ] **Attached to customer**: customer_id present

---

## 7. Security Testing

### 7.1 Authentication
- [ ] **Unauthenticated requests**: Rejected (401)
- [ ] **Expired token**: Rejected (401)
- [ ] **Invalid token**: Rejected (401)
- [ ] **Token in header**: Required format enforced

### 7.2 Authorization
- [ ] **User A cannot access User B's payment methods**: Isolated
- [ ] **User cannot attach other customer's payment method**: Prevented
- [ ] **Payment method isolation**: Cannot detach others' methods

### 7.3 CORS
- [ ] **Allowed origins only**: Frontend domain whitelisted
- [ ] **Other origins blocked**: Random domains rejected
- [ ] **Preflight requests**: OPTIONS handled correctly

### 7.4 Webhook Security
- [ ] **Signature verification**: Webhooks validated
- [ ] **Invalid signature**: Rejected
- [ ] **Replay attacks**: Protected

---

## 8. Browser Compatibility

### Desktop
- [ ] **Chrome (latest)**: Full functionality
- [ ] **Firefox (latest)**: Full functionality
- [ ] **Safari (latest)**: Full functionality
- [ ] **Edge (latest)**: Full functionality

### Mobile
- [ ] **Mobile Safari (iOS)**: Touch interactions work
- [ ] **Chrome (Android)**: Input fields keyboard friendly
- [ ] **Samsung Internet**: Payment Element renders
- [ ] **Mobile keyboard**: Doesn't break layout

### Responsive Design
- [ ] **Desktop (1920x1080)**: Optimal layout
- [ ] **Laptop (1440x900)**: Good layout
- [ ] **Tablet (768px)**: Modal responsive
- [ ] **Mobile (375px)**: Full-width modal, usable

---

## 9. Performance Testing

### Load Times
- [ ] **Stripe.js loads**: < 2 seconds
- [ ] **Payment Element initializes**: < 1 second
- [ ] **Modal opens**: < 500ms
- [ ] **Form submission**: < 3 seconds (including Stripe API)

### Resource Usage
- [ ] **No memory leaks**: Modal cleanup on close
- [ ] **Elements destroyed**: Payment Element removed from DOM
- [ ] **Event listeners removed**: No leaked listeners

---

## 10. Edge Cases

### Unusual Scenarios
- [ ] **Test mode → Live mode switch**: Old test customers handled gracefully
- [ ] **Slow network**: Loading states don't get stuck
- [ ] **Very long name**: Truncates gracefully
- [ ] **International address**: Non-US addresses work
- [ ] **Special characters in name**: Handled correctly

### Multiple Actions
- [ ] **Rapid clicks**: Debounced, no double submission
- [ ] **Multiple modals**: Only one can be open
- [ ] **Modal re-open**: Clears previous state
- [ ] **Browser back button**: Doesn't break state

---

## 11. Console Error Checking

Monitor browser console for:

### Expected (OK)
- Stripe.js initialization logs
- Payment Element ready event

### Unexpected (Fix Required)
- [ ] **TypeScript errors**: Should be zero
- [ ] **React/rendering errors**: Should be zero
- [ ] **Network failures**: Check CORS/auth
- [ ] **Stripe.js errors**: Check API keys
- [ ] **404s**: Missing resources
- [ ] **Uncaught exceptions**: JS errors

---

## 12. Accessibility

### Keyboard Navigation
- [ ] **Tab through form**: Logical tab order
- [ ] **Enter submits**: Keyboard submission works
- [ ] **Escape closes**: Modal closes on Escape
- [ ] **Focus visible**: Clear focus indicators

### Screen Reader
- [ ] **Labels announced**: Input labels read
- [ ] **Errors announced**: Error messages read
- [ ] **Button states**: Disabled/loading announced
- [ ] **Modal role**: Proper ARIA attributes

---

## Testing Priority

### Critical (Must Pass)
1. ✅ Add first payment method
2. ✅ Update existing payment method
3. ✅ 3D Secure flow
4. ✅ Card declined error handling
5. ✅ Stripe Dashboard verification

### Important
6. ✅ Form validation
7. ✅ Authentication errors
8. ✅ Network failure handling
9. ✅ Mobile responsiveness
10. ✅ Browser compatibility (Chrome, Safari, Firefox)

### Nice to Have
11. ✅ Link payment method
12. ✅ Edge cases (slow network, special characters)
13. ✅ Accessibility
14. ✅ Performance metrics
15. ✅ Security tests (payment method isolation)

---

## Sign-off

**Tester Name**: ___________________________
**Date**: ___________________________
**Environment**: [ ] Development [ ] Staging [ ] Production
**Result**: [ ] All tests passed [ ] Issues found (see notes)

**Notes**:
```


```

---

## Related Documentation

- [Stripe Setup Guide](./stripe_setup.md)
- [Manual Testing Guide](./MANUAL_TESTING_GUIDE.md) (step-by-step screenshots)
- [Backend Tests](../backend/tests/test_stripe_payment_element.py)
- [Stripe Payment Element Docs](https://stripe.com/docs/payments/payment-element)
