#!/bin/bash

# Development script that runs both Vite and backend server

# Create necessary directories
mkdir -p docs

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "Error: backend directory not found"
    exit 1
fi

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo "Error: frontend directory not found"
    exit 1
fi

echo "Starting Chat with Stats in development mode..."
echo "Make sure you have set your ANTHROPIC_API_KEY in .env"
echo ""

# Function to kill background processes on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up trap to cleanup on script exit
trap cleanup INT TERM EXIT

# Start the backend server in background
echo "Starting backend server on port 8000..."
cd backend && uv run uvicorn app:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Give backend a moment to start
sleep 2

# Start the Vite dev server in background
echo "Starting Vite dev server on port 3000..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=================================="
echo "Development servers are running:"
echo "Frontend (Vite): http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "=================================="
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for background processes
wait