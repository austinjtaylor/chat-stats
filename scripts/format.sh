#!/bin/bash

# Quick format script
# Formats code and fixes import ordering

set -e

echo "🎨 Formatting code..."

# Change to project root
cd "$(dirname "$0")/.."

# Run black formatter
echo "Running black formatter..."
uv run black .

# Fix imports with ruff
echo "Fixing imports with ruff..."
uv run ruff check --fix --select I .

echo "✅ Code formatting completed!"