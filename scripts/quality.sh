#!/bin/bash

# Code Quality Tools Script
# Run various code quality checks and formatting

set -e

echo "🔧 Running code quality checks..."

# Change to project root
cd "$(dirname "$0")/.."

# Function to run a command with a header
run_check() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    shift
    "$@"
}

# Parse command line arguments
FORMAT=false
CHECK=false
LINT=false
TYPE=false
TEST=false
CRITICAL=false
ALL=false

if [ $# -eq 0 ]; then
    ALL=true
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--format)
            FORMAT=true
            shift
            ;;
        -c|--check)
            CHECK=true
            shift
            ;;
        -l|--lint)
            LINT=true
            shift
            ;;
        -t|--type)
            TYPE=true
            shift
            ;;
        --test)
            TEST=true
            shift
            ;;
        --critical)
            CRITICAL=true
            shift
            ;;
        -a|--all)
            ALL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -f, --format    Run black formatter"
            echo "  -c, --check     Check formatting with black"
            echo "  -l, --lint      Run ruff linter"
            echo "  -t, --type      Run mypy type checker"
            echo "  --test          Run all tests"
            echo "  --critical      Run critical query tests only"
            echo "  -a, --all       Run all checks (default)"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Run black formatter
if [ "$FORMAT" = true ] || [ "$ALL" = true ]; then
    run_check "Formatting code with black" uv run black .
fi

# Check formatting
if [ "$CHECK" = true ] || [ "$ALL" = true ]; then
    run_check "Checking code formatting" uv run black --check .
fi

# Run ruff linter
if [ "$LINT" = true ] || [ "$ALL" = true ]; then
    run_check "Linting with ruff" uv run ruff check .
fi

# Run mypy type checker
if [ "$TYPE" = true ] || [ "$ALL" = true ]; then
    run_check "Type checking with mypy" uv run mypy .
fi

# Run all tests
if [ "$TEST" = true ] || [ "$ALL" = true ]; then
    run_check "Running all tests" uv run pytest backend/tests/ -v
fi

# Run critical query tests (always run these - they're essential)
if [ "$CRITICAL" = true ] || [ "$ALL" = true ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚨 Running CRITICAL query tests (must pass)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Run critical tests and capture exit code
    if uv run pytest backend/tests/test_critical_queries.py -v; then
        echo "✅ Critical query tests passed!"
    else
        echo ""
        echo "❌ CRITICAL QUERY TESTS FAILED!"
        echo "These tests ensure that essential queries work correctly."
        echo "The build cannot proceed until these tests pass."
        exit 1
    fi
fi

echo ""
echo "✅ Code quality checks completed!"