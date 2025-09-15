#!/bin/bash

# Create necessary directories
mkdir -p docs

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "Error: backend directory not found"
    exit 1
fi

# Check for development mode flag
if [ "$1" = "--dev" ] || [ "$1" = "-d" ]; then
    echo "Starting in development mode with Vite..."
    ./run-dev.sh
    exit 0
fi

echo "Starting Chat with Stats..."
echo "Make sure you have set your ANTHROPIC_API_KEY in .env"
echo ""
echo "Note: To run with Vite dev server, use: ./run.sh --dev"

# Change to backend directory and start the server
cd backend && uv run uvicorn app:app --reload --port 8000