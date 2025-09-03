# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This application is a full-stack web application that enables users to ask natural language questions about sports statistics and receive intelligent, data-driven responses. It uses direct SQL queries against a structured sports database, with Claude AI determining which queries to execute based on user questions.

## Plan & Review

### Before starting work
- Always in plan mode to make a plan
- After get the plan, make sure you Write the plan to .claude/tasks|/TASK_NAME. md.
- The plan should be a detailed implementation plan and the reasoning behind them, as well as tasks broken down.
- If the task require external knowledge or certain package, also research to get latest knowledge (Use Task tool for research)
- Don't over plan it, always think MVP.
- Once you write the plan, firstly ask me to review it. Do not continue until I approve the plan.

### While implementing
- You should update the plan as you work.
- After you complete tasks in the plan, you should update and append detailed descriptions of the changes you made, so following tasks can be easily hand over to other engineers.

## Git Commit Protocol

When the user says "commit" or "add and commit", automatically:

1. **Stage relevant files**: Use `git add` to stage the key modified files (avoid staging cache files, temp files)
2. **Show staged changes**: Display what files will be committed with `git diff --cached --name-only`  
3. **Create clean commit message**: Write descriptive commit message WITHOUT Claude authoring information
4. **Execute commit**: Run the git commit command

### Commit Message Format
- Use clear, descriptive titles
- Include bullet points for major changes
- Add test results if applicable  
- **NEVER include**: "🤖 Generated with Claude Code" or "Co-Authored-By: Claude"

## Development Commands

### Running the Application
```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Database Setup
```bash
# Initialize database with schema and synthetic UFA data (for development/testing)
uv run python scripts/database_setup.py init
uv run python scripts/database_setup.py generate

# Full database reset (development/testing)
uv run python scripts/database_setup.py reset

# The database will be created at ./db/sports_stats.db
```

### UFA API Data Import (Production Data)
```bash
# Import complete historical UFA data (recommended for production)
uv run python scripts/ufa_data_manager.py import-api-parallel

# Import specific years only (sequential)
uv run python scripts/ufa_data_manager.py import-api 2024 2025

# Import with parallel processing and custom worker count
uv run python scripts/ufa_data_manager.py import-api-parallel --workers 4 2022 2023

# Complete missing imports (games and season stats)
uv run python scripts/ufa_data_manager.py complete-missing
```

**Note**: See `docs/ufa_api_documentation.txt` for complete UFA API reference.

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest backend/tests/test_ai_generator.py

# Run with verbose output
uv run pytest -v

# Run specific test by name
uv run pytest -k "test_name"
```

### Dependencies
```bash
# Install all dependencies
uv sync

# Add new dependency
uv add package_name

# Add development dependency
uv add --group dev package_name
```

### Code Quality
```bash
# Run all quality checks (format, lint, type check)
./scripts/quality.sh

# Quick format code
./scripts/format.sh

# Individual tools
uv run black .                 # Format code
uv run black --check .         # Check formatting
uv run ruff check .            # Lint code
uv run ruff check --fix .      # Fix linting issues
uv run mypy .                  # Type checking

# Quality script options
./scripts/quality.sh --help    # Show all options
./scripts/quality.sh --format  # Only format
./scripts/quality.sh --lint    # Only lint
./scripts/quality.sh --type    # Only type check
```

### Environment Setup
Create `.env` file in root with:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_PATH=./db/sports_stats.db
```

## Architecture Overview

This is a **Sports Statistics Chat System** that uses SQL database queries with Claude AI function calling to answer questions about player stats, team performance, and game results.

### Core System Components

1. **SQL Database** → **Claude Function Calling** → **Natural Language Response**
2. Direct SQL queries against structured sports data (no embeddings/vectors)
3. Claude AI uses tool calling to execute specific SQL queries based on user questions

### Backend Architecture (`/backend/`)

**Main Orchestrator:**
- `stats_chat_system.py` - Central coordinator connecting all components
- `app.py` - FastAPI web server with sports statistics endpoints

**Core Components:**
- `sql_database.py` - SQLAlchemy database connection and query execution
- `stats_processor.py` - Data ingestion and ETL for sports statistics
- `stats_tools.py` - Claude tool definitions for SQL queries (replaces search_tools.py)
- `ai_generator.py` - Anthropic Claude API integration with SQL function calling
- `session_manager.py` - Maintains conversation history per user session

**Data Models:**
- `models.py` - Pydantic models for Player, Team, Game, PlayerGameStats, PlayerSeasonStats, TeamSeasonStats
- `database_schema.sql` - Complete SQL schema for sports statistics

### Database Schema

The system uses SQLite with the following main tables:
- **teams** - Team information (name, city, division, conference)
- **players** - Player details (name, position, team, physical stats)
- **games** - Game records (date, teams, scores, venue)
- **player_game_stats** - Individual player performance per game
- **player_season_stats** - Aggregated season statistics per player
- **team_season_stats** - Team performance and standings

### Claude Tool Integration

The system provides Claude with 7 SQL-based tools:
- `get_player_stats` - Retrieve player statistics (season/game/career)
- `get_team_stats` - Team performance and roster information
- `get_game_results` - Game scores and box scores
- `get_league_leaders` - Top performers by statistical category
- `compare_players` - Head-to-head player comparisons
- `search_players` - Find players by name/team/position
- `get_standings` - League standings and playoff picture

Claude autonomously decides which tools to use based on the user's question.

### Query Processing Flow

1. **User Query** → Frontend sends POST to `/api/query`
2. **Session Management** → Retrieve conversation history for context
3. **AI Generation** → Claude receives query + history + SQL tool definitions
4. **Tool Execution** → Claude calls appropriate SQL functions
5. **Database Query** → SQL executed against sports statistics database
6. **Response Synthesis** → Claude formats results into natural language
7. **Session Update** → Store query/response for future context

### API Endpoints

- `POST /api/query` - Process natural language queries about sports stats
- `GET /api/stats` - Get summary statistics (players, teams, games, leaders)
- `GET /api/players/search?q={name}` - Search for players
- `GET /api/teams/search?q={name}` - Search for teams
- `GET /api/games/recent` - Get recent game results
- `GET /api/database/info` - Get database schema information
- `POST /api/data/import` - Import sports data from files

### Configuration

Key settings in `backend/config.py`:
- `DATABASE_PATH: "./db/sports_stats.db"` - SQLite database location
- `MAX_RESULTS: 10` - Maximum results per query
- `MAX_HISTORY: 5` - Conversation messages remembered per session
- `MAX_TOOL_ROUNDS: 3` - Maximum sequential tool calls
- `ANTHROPIC_MODEL: "claude-3-haiku-20240307"` - Claude model version

### Frontend (`/frontend/`)

HTML/CSS/JavaScript chat interface that:
- Displays league statistics and top scorers
- Sends queries to `/api/query` endpoint with session management
- Renders responses with data visualizations
- Provides suggested questions for sports queries

### Data Storage

- **SQLite Database** (`./db/sports_stats.db`) - All sports statistics
- **Session Memory** - In-memory conversation history (ephemeral)
- **Sample Data** (`/data/sample_stats.json`) - Reference data for testing

## Development Notes

- Always use `uv` to manage dependencies and run Python code (not pip directly)
- Test files use pytest framework
- Use `scripts/database_setup.py` for development/testing data and `scripts/ufa_data_manager.py` for production UFA data
- The system uses direct SQL queries instead of vector embeddings for accuracy
- Claude function calling provides precise statistics without hallucination