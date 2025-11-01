#!/bin/bash

###############################################################################
# Payment Element API Smoke Test Script
#
# Quick smoke tests for Stripe Payment Element endpoints.
# Tests basic connectivity and authentication requirements.
#
# Usage:
#   ./scripts/test_payment_element.sh [options]
#
# Options:
#   -h, --help        Show this help message
#   -u, --url URL     API base URL (default: http://localhost:8000)
#   -t, --token TOKEN Auth token for authenticated requests
#   -v, --verbose     Verbose output
#
# Examples:
#   ./scripts/test_payment_element.sh
#   ./scripts/test_payment_element.sh --url https://api.example.com
#   ./scripts/test_payment_element.sh --token "your-jwt-token"
#
###############################################################################

set -e  # Exit on error

# Default configuration
API_URL="${API_URL:-http://localhost:8000}"
AUTH_TOKEN=""
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo ""
    echo "========================================================================"
    echo " $1"
    echo "========================================================================"
}

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
    TESTS_RUN=$((TESTS_RUN + 1))
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

show_help() {
    grep '^#' "$0" | tail -n +3 | sed '$d' | cut -c 3-
    exit 0
}

###############################################################################
# Test Functions
###############################################################################

test_api_health() {
    print_test "API Health Check"

    response=$(curl -s -w "\n%{http_code}" "$API_URL/api" 2>&1)
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        print_success "API is reachable (HTTP $http_code)"
        print_info "Response: $body"
        return 0
    else
        print_error "API health check failed (HTTP $http_code)"
        print_info "Response: $body"
        return 1
    fi
}

test_create_setup_intent_no_auth() {
    print_test "Create SetupIntent without authentication"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/stripe/create-setup-intent" \
        -H "Content-Type: application/json" 2>&1)
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    # Should be rejected (401, 403, or 422 depending on auth implementation)
    if [[ "$http_code" =~ ^(401|403|422)$ ]]; then
        print_success "Correctly rejected unauthenticated request (HTTP $http_code)"
        print_info "Response: $body"
        return 0
    else
        print_error "Should reject unauthenticated request (got HTTP $http_code)"
        print_info "Response: $body"
        return 1
    fi
}

test_create_setup_intent_with_auth() {
    print_test "Create SetupIntent with authentication"

    if [ -z "$AUTH_TOKEN" ]; then
        print_warning "Skipped (no auth token provided)"
        return 0
    fi

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/stripe/create-setup-intent" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" 2>&1)
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    print_info "HTTP Code: $http_code"
    print_info "Response: $body"

    # Could be 200 (success) or 400 (no customer) depending on user state
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q "client_secret"; then
            print_success "SetupIntent created successfully"
            print_info "Response contains client_secret"
            return 0
        else
            print_error "Response missing client_secret"
            return 1
        fi
    elif [ "$http_code" = "400" ]; then
        if echo "$body" | grep -q "No Stripe customer found"; then
            print_success "Correctly returned error for user without Stripe customer (HTTP 400)"
            return 0
        else
            print_error "Unexpected 400 error: $body"
            return 1
        fi
    else
        print_error "Unexpected HTTP code: $http_code"
        return 1
    fi
}

test_update_payment_method_no_auth() {
    print_test "Update payment method without authentication"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/stripe/update-payment-method" \
        -H "Content-Type: application/json" \
        -d '{"payment_method_id": "pm_test123"}' 2>&1)
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    # Should be rejected
    if [[ "$http_code" =~ ^(401|403|422)$ ]]; then
        print_success "Correctly rejected unauthenticated request (HTTP $http_code)"
        print_info "Response: $body"
        return 0
    else
        print_error "Should reject unauthenticated request (got HTTP $http_code)"
        print_info "Response: $body"
        return 1
    fi
}

test_update_payment_method_missing_data() {
    print_test "Update payment method with missing payment_method_id"

    if [ -z "$AUTH_TOKEN" ]; then
        print_warning "Skipped (no auth token provided)"
        return 0
    fi

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/stripe/update-payment-method" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{}' 2>&1)
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    # Should return 400 for missing payment_method_id
    if [[ "$http_code" =~ ^(400|422)$ ]]; then
        print_success "Correctly rejected request with missing data (HTTP $http_code)"
        print_info "Response: $body"
        return 0
    else
        print_error "Should reject request with missing data (got HTTP $http_code)"
        print_info "Response: $body"
        return 1
    fi
}

test_get_payment_methods_no_auth() {
    print_test "Get payment methods without authentication"

    response=$(curl -s -w "\n%{http_code}" "$API_URL/api/stripe/payment-methods" 2>&1)
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    # Should be rejected
    if [[ "$http_code" =~ ^(401|403|422)$ ]]; then
        print_success "Correctly rejected unauthenticated request (HTTP $http_code)"
        print_info "Response: $body"
        return 0
    else
        print_error "Should reject unauthenticated request (got HTTP $http_code)"
        print_info "Response: $body"
        return 1
    fi
}

test_get_payment_methods_with_auth() {
    print_test "Get payment methods with authentication"

    if [ -z "$AUTH_TOKEN" ]; then
        print_warning "Skipped (no auth token provided)"
        return 0
    fi

    response=$(curl -s -w "\n%{http_code}" "$API_URL/api/stripe/payment-methods" \
        -H "Authorization: Bearer $AUTH_TOKEN" 2>&1)
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    print_info "HTTP Code: $http_code"
    print_info "Response: $body"

    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q "payment_method"; then
            print_success "Payment methods retrieved successfully"
            return 0
        else
            print_error "Response missing payment_method field"
            return 1
        fi
    else
        print_error "Failed to retrieve payment methods (HTTP $http_code)"
        return 1
    fi
}

test_endpoint_cors() {
    print_test "CORS preflight request"

    response=$(curl -s -w "\n%{http_code}" -X OPTIONS "$API_URL/api/stripe/create-setup-intent" \
        -H "Origin: http://localhost:3000" \
        -H "Access-Control-Request-Method: POST" 2>&1)
    http_code=$(echo "$response" | tail -n 1)

    # CORS preflight should return 200 or 204
    if [[ "$http_code" =~ ^(200|204)$ ]]; then
        print_success "CORS preflight successful (HTTP $http_code)"
        return 0
    else
        print_warning "CORS preflight returned HTTP $http_code (may not be configured)"
        return 0  # Don't fail test, just warn
    fi
}

###############################################################################
# Main Test Suite
###############################################################################

run_all_tests() {
    print_header "Payment Element API Smoke Tests"
    echo "API URL: $API_URL"
    if [ -n "$AUTH_TOKEN" ]; then
        echo "Auth Token: ${AUTH_TOKEN:0:10}...${AUTH_TOKEN: -10}"
    else
        echo "Auth Token: Not provided (some tests will be skipped)"
    fi
    echo ""

    # Run tests
    test_api_health
    echo ""

    print_header "Create SetupIntent Endpoint"
    test_create_setup_intent_no_auth
    test_create_setup_intent_with_auth
    echo ""

    print_header "Update Payment Method Endpoint"
    test_update_payment_method_no_auth
    test_update_payment_method_missing_data
    echo ""

    print_header "Get Payment Methods Endpoint"
    test_get_payment_methods_no_auth
    test_get_payment_methods_with_auth
    echo ""

    print_header "CORS Tests"
    test_endpoint_cors
    echo ""

    # Print summary
    print_header "Test Summary"
    echo "Tests Run:    $TESTS_RUN"
    echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        exit 1
    fi
}

###############################################################################
# Command Line Argument Parsing
###############################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -u|--url)
            API_URL="$2"
            shift 2
            ;;
        -t|--token)
            AUTH_TOKEN="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

###############################################################################
# Run Tests
###############################################################################

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl is not installed${NC}"
    exit 1
fi

# Run the test suite
run_all_tests
