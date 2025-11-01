# Manual Testing Guide - Payment Element Integration

This guide provides step-by-step instructions for manually testing the Stripe Payment Element integration. Follow these procedures to verify all functionality works correctly.

**Environment**: Development / Staging
**Last Updated**: October 2024

---

## Prerequisites

### Before You Begin

1. **Stripe Account**: Test mode enabled
2. **Test Cards**: Reference the [test cards](#test-card-reference) section
3. **User Account**: Test user with email verification
4. **Browser**: Latest Chrome, Firefox, or Safari
5. **Developer Tools**: Open browser console (F12)

### Test Environment Setup

```bash
# Terminal 1: Start backend
cd backend
uv run uvicorn app:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev
```

**URLs**:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Stripe Dashboard: `https://dashboard.stripe.com/test`

---

## Test Flow 1: Add First Payment Method (New User)

**Objective**: Verify a user without a payment method can add one using Payment Element

**Prerequisites**: User account with no existing payment method

### Steps

1. **Login to Application**
   - Navigate to `http://localhost:3000`
   - Click "Login" or "Sign Up"
   - Complete authentication

   ✅ **Verify**: User is logged in, redirected to dashboard

2. **Navigate to Settings**
   - Click user profile icon (top right)
   - Click "Settings" from dropdown

   ✅ **Verify**: Settings page loads

3. **Open Billing Tab**
   - Click "Billing" tab in settings

   ✅ **Verify**:
   - Billing information displayed
   - "Update payment method" button visible
   - No existing payment method shown

4. **Open Payment Modal**
   - Click "Update payment method" button

   ✅ **Verify**:
   - Modal opens with overlay
   - Title reads "Payment method"
   - Stripe Payment Element loads (card input field visible)
   - No "Use existing" option shown
   - Cancel button visible

5. **Fill Form - Name**
   - Enter: `John Test User`

   ✅ **Verify**: Name field accepts input

6. **Select Country**
   - Select: `United States`

   ✅ **Verify**: Country dropdown works

7. **Enter Address Line 1**
   - Enter: `123 Main Street`

   ✅ **Verify**: Address field accepts input

8. **Additional Address Fields Appear**
   - Observe: City, State, ZIP fields appear

   ✅ **Verify**: Additional fields visible when Card payment method selected

9. **Fill Address - City**
   - Enter: `San Francisco`

   ✅ **Verify**: City field accepts input

10. **Fill Address - State**
    - Select: `California`

    ✅ **Verify**: State dropdown works

11. **Fill Address - ZIP**
    - Enter: `94102`

    ✅ **Verify**: ZIP field accepts input

12. **Enter Card Number**
    - Click in Stripe card element
    - Enter: `4242 4242 4242 4242`

    ✅ **Verify**:
    - Card number formats as you type
    - No error messages
    - Expiration field becomes active

13. **Enter Expiration**
    - Enter: `12/25`

    ✅ **Verify**: Expiration formats correctly (MM/YY)

14. **Enter CVC**
    - Enter: `123`

    ✅ **Verify**: CVC field accepts 3 digits

15. **Submit Form**
    - Click "Update" button

    ✅ **Verify**:
    - Button shows loading spinner
    - Button disabled during processing
    - Button text changes to spinner

16. **Wait for Processing**
    - Wait 2-5 seconds

    ✅ **Verify** (in Console):
    - No JavaScript errors
    - Network request to `/api/stripe/create-setup-intent` succeeds (200)
    - Network request to `/api/stripe/update-payment-method` succeeds (200)

17. **Modal Closes**
    - Modal should close automatically

    ✅ **Verify**:
    - Modal closes
    - Returned to Settings → Billing tab

18. **Payment Method Displayed**
    - Check payment method section

    ✅ **Verify**:
    - "Visa •••• 4242" displayed
    - "Expires 12/2025" displayed
    - "Update payment method" button still available

19. **Verify in Stripe Dashboard**
    - Open: `https://dashboard.stripe.com/test/customers`
    - Search for test user email
    - Click customer

    ✅ **Verify**:
    - Customer has payment method attached
    - Default payment method is set
    - Card details match: Visa •••• 4242

20. **Verify SetupIntent**
    - In Stripe Dashboard: Payments → SetupIntents
    - Find recent SetupIntent

    ✅ **Verify**:
    - Status: `Succeeded`
    - Payment method attached
    - Customer ID matches

**Expected Result**: ✅ Payment method successfully added

---

## Test Flow 2: Update Existing Payment Method

**Objective**: Verify a user can update their existing payment method

**Prerequisites**: User with existing payment method

### Steps

1. **Login and Navigate to Billing**
   - Login as user with existing payment method
   - Navigate to Settings → Billing

   ✅ **Verify**: Existing payment method displayed (e.g., "Visa •••• 4242")

2. **Open Payment Modal**
   - Click "Update payment method"

   ✅ **Verify**:
   - Modal opens
   - Shows "Use Visa •••• 4242"
   - Shows "Expires XX/XXXX"
   - "Change" button visible
   - Payment Element NOT visible yet

3. **Enter Edit Mode**
   - Click "Change" button

   ✅ **Verify**:
   - "Change" button disappears
   - Link logo appears (if using Link)
   - Menu button (three dots) appears
    - "New payment method" button appears
   - "Log out of Link" button appears (if applicable)

4. **Add New Payment Method**
   - Click "New payment method" button

   ✅ **Verify**:
   - Payment Element appears
   - "New payment method" button hides
   - "Use a saved payment method" button appears below Payment Element
   - Existing card option remains visible above

5. **Fill New Card Details**
   - Enter card: `5555 5555 5555 4444` (Mastercard)
   - Enter expiration: `01/26`
   - Enter CVC: `456`
   - Fill address fields (same as before)

   ✅ **Verify**: All fields accept input

6. **Submit Update**
   - Click "Update" button

   ✅ **Verify**:
   - Loading spinner appears
   - Processing occurs
   - Modal closes

7. **Verify Update**
   - Check payment method section

   ✅ **Verify**:
   - OLD card no longer shown (Visa ••••4242)
   - NEW card displayed: "Mastercard •••• 4444"
   - "Expires 1/2026" shown

8. **Verify in Stripe Dashboard**
   - Check customer's payment methods

   ✅ **Verify**:
   - New Mastercard is default payment method
   - Old Visa may still be attached but not default

**Expected Result**: ✅ Payment method successfully updated

---

## Test Flow 3: 3D Secure Authentication

**Objective**: Verify 3D Secure authentication flow works inline

**Prerequisites**: User account (with or without existing payment method)

### Steps

1. **Open Payment Modal**
   - Navigate to Settings → Billing
   - Click "Update payment method"
   - Click "Change" (if existing method) then "New payment method"

2. **Enter 3DS Test Card**
   - Card: `4000 0027 6000 3184`
   - Expiration: `12/25`
   - CVC: `123`
   - Fill address fields

   ✅ **Verify**: Card number accepted

3. **Submit Form**
   - Click "Update" button

   ✅ **Verify**:
   - Loading spinner appears
   - Processing starts

4. **3D Secure Modal Appears**
   - Wait 2-3 seconds
   - 3D Secure authentication iframe appears **inside** the payment modal

   ✅ **Verify**:
   - 3DS modal appears inline (no page redirect)
   - Test authentication page loads
   - "Complete" or "Fail" buttons visible

5. **Complete Authentication**
   - Click "Complete" button in 3DS iframe

   ✅ **Verify**:
   - 3DS iframe closes
   - Processing continues

6. **Payment Method Saved**
   - Modal closes automatically

   ✅ **Verify**:
   - Payment modal closes
   - New payment method appears in settings
   - Card shows: "Visa •••• 3184"

7. **Verify in Console**
   - Check browser console

   ✅ **Verify**:
   - No errors
   - `redirect: 'if_required'` kept user in modal
   - SetupIntent confirmed successfully

**Expected Result**: ✅ 3D Secure handled inline without page redirect

---

## Test Flow 4: Validation Errors

**Objective**: Verify form validation works correctly

**Prerequisites**: Any user account

### Steps

1. **Open Payment Modal**
   - Navigate to Settings → Billing
   - Open payment modal

2. **Test Empty Name**
   - Leave name field empty
   - Fill other fields
   - Click "Update"

   ✅ **Verify**:
   - Error message appears: "This field is incomplete."
   - Red border on name field
   - Form does not submit

3. **Fix Name, Test Empty Address**
   - Enter name: `Test User`
   - Leave address line 1 empty
   - Click "Update"

   ✅ **Verify**:
   - Error message appears under address field
   - Red border on address field
   - Form does not submit

4. **Fix Address, Test Empty City**
   - Enter address
   - Leave city empty (if Card payment method selected)
   - Click "Update"

   ✅ **Verify**:
   - Error message appears under city field
   - Form does not submit

5. **Fix City, Test Empty State**
   - Enter city
   - Leave state as "Select"
   - Click "Update"

   ✅ **Verify**:
   - Error message appears under state field
   - Form does not submit

6. **Fix State, Test Empty ZIP**
   - Select state
   - Leave ZIP empty
   - Click "Update"

   ✅ **Verify**:
   - Error message appears under ZIP field
   - Form does not submit

7. **Fix ZIP, Test Invalid Card**
   - Enter ZIP: `94102`
   - Enter invalid card: `1234 1234 1234 1234`
   - Click "Update"

   ✅ **Verify**:
   - Stripe shows inline error: "Your card number is invalid."
   - Form does not submit

8. **Enter Valid Data**
   - Enter valid card: `4242 4242 4242 4242`
   - Click "Update"

   ✅ **Verify**:
   - All errors clear
   - Form submits successfully

**Expected Result**: ✅ All validation errors work correctly

---

## Test Flow 5: Card Decline Handling

**Objective**: Verify declined cards show appropriate errors

**Prerequisites**: Any user account

### Steps

1. **Open Payment Modal**

2. **Test Generic Decline**
   - Card: `4000 0000 0000 0002`
   - Fill other fields
   - Click "Update"

   ✅ **Verify**:
   - Error message: "Your card was declined."
   - Modal remains open
   - Can retry with different card

3. **Test Insufficient Funds**
   - Card: `4000 0000 0000 9995`
   - Click "Update"

   ✅ **Verify**:
   - Error message: "Your card has insufficient funds."

4. **Test Lost Card**
   - Card: `4000 0000 0000 9987`
   - Click "Update"

   ✅ **Verify**:
   - Error message indicates card is lost/stolen

5. **Recover with Valid Card**
   - Card: `4242 4242 4242 4242`
   - Click "Update"

   ✅ **Verify**:
   - Error clears
   - Payment method saves successfully

**Expected Result**: ✅ Decline errors handled gracefully

---

## Test Flow 6: Link Payment Method

**Objective**: Test Stripe Link payment method (if available)

**Prerequisites**: User with Link account or willing to create one

### Steps

1. **Open Payment Modal**
   - Navigate to Settings → Billing
   - Open payment modal

2. **Click Link Tab**
   - In Payment Element, click "Link" tab

   ✅ **Verify**:
   - Link tab active
   - Email/phone input appears

3. **Enter Link Email**
   - Enter email previously used with Link
   - OR enter new email to create Link account

   ✅ **Verify**:
   - Email accepted
   - SMS code request sent (for new accounts)

4. **Verify Additional Fields**
   - Observe address fields

   ✅ **Verify**:
   - Additional address fields (City, State, ZIP) HIDE
   - Only Address Line 1 remains (Link provides billing details)

5. **Complete Link Authentication**
   - Enter SMS code (if creating new account)

   ✅ **Verify**:
   - Link authentication succeeds
   - Payment method pre-fills

6. **Save Payment Method**
   - Click "Update"

   ✅ **Verify**:
   - Payment method saves
   - Link payment method appears in settings

**Expected Result**: ✅ Link payment method works correctly

---

## Test Flow 7: Cancel and Modal Behavior

**Objective**: Verify modal can be safely canceled at any time

**Prerequisites**: Any user account

### Steps

1. **Cancel Before Entry**
   - Open payment modal
   - Click "Cancel" immediately

   ✅ **Verify**:
   - Modal closes
   - No payment method created
   - No API calls made

2. **Cancel During Entry**
   - Open payment modal
   - Fill partial information
   - Click "Cancel"

   ✅ **Verify**:
   - Modal closes
   - Data not saved
   - No payment method created

3. **Close with Escape**
   - Open payment modal
   - Press Escape key

   ✅ **Verify**:
   - Modal closes

4. **Close with Overlay Click**
   - Open payment modal
   - Click dark overlay outside modal

   ✅ **Verify**:
   - Modal closes

5. **Re-Open After Cancel**
   - Open payment modal again

   ✅ **Verify**:
   - Modal opens fresh
   - Previous partial data not retained
   - Stripe Element re-initializes

**Expected Result**: ✅ Modal can be safely canceled

---

## Test Flow 8: Mobile Responsiveness

**Objective**: Verify payment modal works on mobile devices

**Prerequisites**: Mobile device or Chrome DevTools device emulation

### Steps

1. **Enable Mobile Emulation**
   - Open Chrome DevTools (F12)
   - Toggle device toolbar (Ctrl+Shift+M)
   - Select: iPhone 12 Pro or similar

2. **Open Payment Modal**
   - Navigate to Settings → Billing
   - Click "Update payment method"

   ✅ **Verify**:
   - Modal is full-width on mobile
   - All fields are accessible
   - Buttons not cut off
   - Scrollable if content overflows

3. **Test Touch Interactions**
   - Tap name field
   - Tap card number field
   - Tap dropdown selects

   ✅ **Verify**:
   - Touch targets are large enough
   - Dropdowns work on mobile
   - No layout shifts when keyboard appears

4. **Test Form Submission**
   - Fill all fields using mobile keyboard
   - Submit form

   ✅ **Verify**:
   - Form submits successfully
   - Loading state visible
   - Modal closes

5. **Test Other Devices**
   - Test on iPad (768px)
   - Test on Galaxy S20 (360px)

   ✅ **Verify**: Responsive on all sizes

**Expected Result**: ✅ Fully functional on mobile

---

## Test Flow 9: Browser Compatibility

**Objective**: Verify payment modal works across browsers

**Browsers to Test**: Chrome, Firefox, Safari, Edge

### Steps

For each browser:

1. **Open Application**
   - Navigate to `http://localhost:3000`
   - Login

2. **Open Payment Modal**
   - Navigate to Settings → Billing
   - Click "Update payment method"

   ✅ **Verify**:
   - Modal renders correctly
   - Stripe Element loads
   - No console errors

3. **Submit Test Payment**
   - Fill form with test card `4242 4242 4242 4242`
   - Submit

   ✅ **Verify**:
   - Form submits
   - Payment method saves
   - No browser-specific issues

4. **Test 3D Secure**
   - Use card `4000 0027 6000 3184`

   ✅ **Verify**:
   - 3DS modal appears inline
   - Works in all browsers

**Expected Result**: ✅ Works in all major browsers

---

## Test Flow 10: Stripe Dashboard Verification

**Objective**: Verify changes sync correctly with Stripe

**Prerequisites**: Access to Stripe test dashboard

### Steps

1. **Add Payment Method in App**
   - Complete Test Flow 1 or 2

2. **Open Stripe Dashboard**
   - Navigate to: `https://dashboard.stripe.com/test/customers`

3. **Find Customer**
   - Search for test user email

   ✅ **Verify**: Customer exists

4. **Check Payment Methods**
   - Click customer
   - Scroll to "Payment methods" section

   ✅ **Verify**:
   - Payment method listed
   - Correct card brand and last 4
   - Default payment method badge shown
   - Billing details populated

5. **Check invoice_settings**
   - View customer details

   ✅ **Verify**:
   - `default_payment_method` is set
   - Matches payment method ID

6. **Check SetupIntents**
   - Navigate to: Payments → SetupIntents
   - Filter by customer

   ✅ **Verify**:
   - SetupIntent exists
   - Status: `Succeeded`
   - Payment method attached
   - `usage`: `off_session`

7. **Check Events Log**
   - Navigate to: Developers → Events
   - Filter recent events

   ✅ **Verify**:
   - `setup_intent.succeeded` event
   - `payment_method.attached` event
   - `customer.updated` event

**Expected Result**: ✅ All data synced correctly with Stripe

---

## Troubleshooting

### Common Issues

#### Issue: Payment Element doesn't load
**Symptoms**: Empty gray box where card input should be

**Solutions**:
- Check browser console for Stripe.js errors
- Verify `VITE_STRIPE_PUBLIC_KEY` in `.env`
- Check network tab for failed Stripe.js load
- Clear browser cache and reload

#### Issue: 3D Secure redirects instead of showing inline
**Symptoms**: Page navigates away during 3DS

**Solutions**:
- Verify `redirect: 'if_required'` in `confirmSetup` call
- Check that `confirmParams` doesn't include `return_url`
- Test with different 3DS test card

#### Issue: "No Stripe customer found" error
**Symptoms**: Error when opening payment modal

**Solutions**:
- User needs to subscribe first
- Check database for `stripe_customer_id`
- Verify subscription was created correctly

#### Issue: Payment method doesn't appear after saving
**Symptoms**: Modal closes but no card shown

**Solutions**:
- Check network tab for failed API calls
- Verify backend updated `invoice_settings.default_payment_method`
- Check Stripe Dashboard for payment method attachment
- Refresh settings page

### Console Error Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `Stripe.js not loaded` | Stripe.js script failed | Check CDN, network connection |
| `Invalid API key` | Wrong Stripe key in env | Verify `.env` has correct test key |
| `Payment method not found` | PM ID doesn't exist | Payment method detached or deleted |
| `Customer not found` | Customer ID invalid | Recreate subscription |

---

## Test Card Reference

### Success Cards (No 3DS)

```
Visa:       4242 4242 4242 4242
Mastercard: 5555 5555 5555 4444
Amex:       3782 822463 10005
Discover:   6011 1111 1111 1117
```

### 3D Secure Cards

```
Visa (3DS2):       4000 0027 6000 3184
Mastercard (3DS2): 4000 0025 0000 3155
```

### Decline Cards

```
Generic Decline:     4000 0000 0000 0002
Insufficient Funds:  4000 0000 0000 9995
Lost Card:           4000 0000 0000 9987
Stolen Card:         4000 0000 0000 9979
Expired Card:        4000 0000 0000 0069
Incorrect CVC:       4000 0000 0000 0127
Processing Error:    4000 0000 0000 0119
```

### Test Data

```
Expiration: Any future date (e.g., 12/25)
CVC:        Any 3 digits (e.g., 123)
ZIP:        Any valid ZIP (e.g., 94102, 10001)
```

---

## Test Completion Checklist

After completing manual testing, verify:

- [ ] All 10 test flows passed
- [ ] No console errors
- [ ] Payment methods sync with Stripe Dashboard
- [ ] Mobile responsive
- [ ] Works in Chrome, Firefox, Safari
- [ ] 3D Secure works inline
- [ ] Validation errors display correctly
- [ ] Card declines handled gracefully
- [ ] Modal can be canceled safely
- [ ] Existing payment methods can be updated

**Tester**: ___________________________
**Date**: ___________________________
**Environment**: [ ] Dev [ ] Staging [ ] Production
**Result**: [ ] Pass [ ] Fail

**Notes**:

---

## Related Documentation

- [Testing Checklist](./PAYMENT_ELEMENT_TESTING.md) - Comprehensive testing checklist
- [Backend Tests](../backend/tests/test_stripe_payment_element.py) - Automated API tests
- [Stripe Setup](./stripe_setup.md) - Stripe configuration guide
- [Stripe Docs](https://stripe.com/docs/payments/payment-element) - Official Stripe Payment Element documentation
