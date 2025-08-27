# Talk to Stats - Sports Statistics Chat System

A natural language sports statistics query system that uses SQL database queries with Claude AI function calling to answer questions about player stats, team performance, and game results.

## Overview

This application is a full-stack web application that enables users to ask natural language questions about sports statistics and receive intelligent, data-driven responses. It uses direct SQL queries against a structured sports database, with Claude AI determining which queries to execute based on user questions.

**Key Features:**
- Natural language queries about sports statistics
- Direct SQL queries for accurate data retrieval (no embeddings/vectors)
- Claude AI function calling for intelligent query selection
- Real-time player stats, team performance, and game results
- Web-based chat interface with conversation history
- Comprehensive sports database with players, teams, games, and statistics

## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   DATABASE_PATH=./db/sports_stats.db
   ```

4. **Initialize the database**
   ```bash
   uv run python scripts/setup_database.py
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Usage Examples

Ask natural language questions about sports statistics:

- "Who are the top scorers this season?"
- "How did the Lakers perform against the Warriors?"
- "Compare LeBron James and Kevin Durant's stats"
- "What are the current standings in the Western Conference?"
- "Show me rookie statistics for this season"

## Architecture

**Core System Flow:**
1. **User Query** → Natural language question about sports
2. **Claude AI** → Determines appropriate SQL queries to execute
3. **Database** → Direct SQL queries against structured sports data
4. **Response** → Natural language summary with statistics

**Key Components:**
- **SQL Database** (SQLite) - Player, team, and game statistics
- **Claude AI Integration** - Function calling for intelligent query selection
- **FastAPI Backend** - REST API with sports statistics endpoints
- **Web Frontend** - Chat interface for natural language queries
- **Session Management** - Conversation history per user

## API Endpoints

- `POST /api/query` - Process natural language sports queries
- `GET /api/stats` - Get summary statistics
- `GET /api/players/search?q={name}` - Search for players
- `GET /api/teams/search?q={name}` - Search for teams
- `GET /api/games/recent` - Get recent game results

## Development

See `CLAUDE.md` for detailed development commands including testing, code quality checks, and database management.