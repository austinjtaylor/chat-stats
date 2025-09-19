# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This application is a full-stack web application that enables users to ask natural language questions about sports statistics and receive intelligent, data-driven responses. It uses direct SQL queries against a structured sports database, with Claude AI determining which queries to execute based on user questions.

## Tool usage
- Remember to use the TodoWrite tool more proactively, especially for tasks with multiple steps.

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

#### Development Mode (with hot reloading)
```bash
# Run both backend and frontend with Vite dev server
./run-dev.sh

# This starts:
# - Backend API on http://localhost:8000
# - Frontend with Vite on http://localhost:3000 (with TypeScript compilation)
```

#### Production Mode
```bash
# Backend only (API server)
./run.sh
# Runs on http://localhost:8000

# Build frontend for production
cd frontend
npm install  # First time only
npm run build  # Creates optimized build in dist/

# Preview production build
npm run preview  # Serves on http://localhost:4173
```

#### Manual Start (backend only)
```bash
cd backend && uv run uvicorn app:app --reload --port 8000
```

#### Port Summary
- **Backend API**: Port 8000 (all modes)
- **Frontend Development**: Port 3000 (Vite dev server with TypeScript/hot reload)
- **Frontend Production Preview**: Port 4173 (built files from dist/)
- **Frontend Production**: Can be served from any static file server

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

# Import game events for a specific game (required for possession stats)
python -c "from scripts.ufa_data_manager import UFADataManager; m = UFADataManager(); m._import_game_events_from_api('GAME_ID')"
```

**Important Notes**: 
- All-star games are automatically excluded during import to reduce database size and improve query performance
- See `docs/ufa_api_documentation.txt` for complete UFA API reference

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

### Database Backup & Restore

```bash
# Create database backup with timestamp
uv run python scripts/backup_database.py backup

# Create compressed backup (saves space)
uv run python scripts/backup_database.py backup --compress

# Create backup and keep only 3 most recent backups
uv run python scripts/backup_database.py backup --cleanup 3

# Export database as SQL dump (version-control friendly)
uv run python scripts/backup_database.py dump

# List all available backups
uv run python scripts/backup_database.py list

# Restore from a specific backup
uv run python scripts/backup_database.py restore sports_stats_20240903_142530.db

# Clean up old backups (keep 5 most recent)
uv run python scripts/backup_database.py cleanup --keep 5
```

**Backup Strategy:**
- Regular backups are stored in `backups/` directory (excluded from Git)
- Compressed backups save ~70% disk space
- SQL dumps are text files suitable for version control
- Automatic cleanup prevents backup directory bloat
- Restore creates a safety backup of current database before restoring

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

**Organized Directory Structure:**
```
backend/
├── api/               # API routes and handlers
│   ├── routes.py      # Basic API endpoints
│   ├── game.py        # Game-specific endpoints
│   └── player_stats.py # Player statistics endpoints
│
├── core/              # Core business logic
│   ├── chat_system.py # Central coordinator (formerly stats_chat_system.py)
│   ├── ai_generator.py # Anthropic Claude API integration
│   ├── session_manager.py # Conversation history management
│   └── tool_executor.py # Tool execution handler
│
├── tools/             # Claude AI tool definitions
│   ├── manager.py     # Tool manager (formerly stats_tool_manager.py)
│   ├── player.py      # Player statistics tools
│   ├── team.py        # Team statistics tools
│   ├── game.py        # Game results tools
│   └── query.py       # Custom SQL query tools
│
├── data/              # Data processing and database
│   ├── database.py    # SQLAlchemy database connection (formerly sql_database.py)
│   ├── processor.py   # Data ingestion and ETL (formerly stats_processor.py)
│   ├── possession.py  # Possession statistics calculator
│   └── cache.py       # In-memory cache manager
│
├── models/            # Data models
│   ├── db.py          # Database models (formerly models.py)
│   └── api.py         # API request/response models
│
├── utils/             # Utility functions
│   ├── stats.py       # Statistics utilities
│   ├── retry.py       # Rate limit retry logic
│   ├── query.py       # Query helper functions
│   ├── response.py    # Response formatting
│   ├── game.py        # Game details utilities
│   └── ufa_events.py  # UFA event type definitions
│
├── config.py          # Configuration settings
├── middleware.py      # FastAPI middleware
├── prompts.py         # AI system prompts
├── app.py            # Main FastAPI application
└── tests/            # Test suite
```

**Main Components:**
- `core/chat_system.py` - Central coordinator connecting all components
- `app.py` - FastAPI web server with sports statistics endpoints
- `data/database.py` - SQLAlchemy database connection and query execution
- `data/processor.py` - Data ingestion and ETL for sports statistics
- `tools/manager.py` - Claude tool definitions for SQL queries
- `core/ai_generator.py` - Anthropic Claude API integration with SQL function calling
- `core/session_manager.py` - Maintains conversation history per user session
- `models/db.py` - Pydantic models for Player, Team, Game, PlayerGameStats, PlayerSeasonStats, TeamSeasonStats
- `database_schema.sql` - Complete SQL schema for sports statistics

### Database Schema

The system uses SQLite with the following main tables:
- **teams** - Team information (name, city, division, conference)
- **players** - Player details (name, position, team, physical stats)
- **games** - Game records (date, teams, scores, venue)
- **player_game_stats** - Individual player performance per game
- **player_season_stats** - Aggregated season statistics per player
- **team_season_stats** - Team performance and standings
- **game_events** - Play-by-play event data for possession tracking (pull, goal, turnover events)

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

### Data Availability Notes

**Advanced statistics** are only available from certain years:
- **Y** (Total Yards), **TY** (Throwing Yards), **RY** (Receiving Yards) - Available from 2021 onwards
- **HCK** (Hucks Completed), **HCK%** (Huck Percentage) - Available from 2021 onwards  
- **HA** (Hockey Assists) - Available from 2014 onwards
- Basic stats (goals, assists, blocks, +/-, completions, turnovers, etc.) - Available for all years (2012-present)

Note: The player stats page automatically hides columns for statistics that are not available in the selected season.

## Important UFA terminology

### Ultimate Frisbee Attacking Direction Rules

1. **Initial Pull**: The pulling team pulls from their defending endzone to the opposite endzone
   - If Away team pulls from South (0-20) to North (100-120), Home team receives and attacks SOUTH
   - If Away team pulls from North (100-120) to South (0-20), Home team receives and attacks NORTH

2. **After Turnover**: The team gaining possession attacks the OPPOSITE direction from the previous offense
   - If Home was attacking North and turns it over, Away attacks SOUTH
   - If Away was attacking South and turns it over, Home attacks NORTH
   - Teams do NOT continue in the same direction after turnovers

3. **After Goal**: The scoring team pulls from the endzone where they just scored
   - The receiving team attacks back toward that same endzone
   - This switches the attacking directions from the previous point

4. **Field Layout** (0-120 yards):
   - South Endzone: 0-20 yards
   - South Red Zone: 20-40 yards  
   - Midfield: 40-80 yards
   - North Red Zone: 80-100 yards
   - North Endzone: 100-120 yards

5. **Key Concept**: You always attack the endzone you're moving TOWARD, not where you came from, just like in American football

### UFA Possession Statistics Methodology

**Important**: The system calculates UFA-style possession statistics from the `game_events` table. Understanding the methodology is crucial:

#### Key Concepts:
- **Point**: One scoring opportunity, from pull (start) to goal (end)
- **Possession**: Each time a team has control of the disc
- **O-line (Offensive Line)**: The team that receives the pull to start a point
- **D-line (Defensive Line)**: The team that pulls to start a point

#### Statistics Calculated:
- **Hold %**: O-line scores / O-line points (ability to score when starting on offense)
- **O-Line Conversion %**: O-line scores / O-line possessions (efficiency on offense)
- **Break %**: D-line scores / D-line points (ability to score when starting on defense)
- **D-Line Conversion %**: D-line scores / D-line possessions (efficiency after forcing turnovers)

#### Important Implementation Notes:
1. **Game events must be imported**: Possession stats require the `game_events` table to be populated
2. **Duplicate events**: Both teams record events at the same index - the algorithm must handle these duplicates
3. **Event ordering**: At the same index, process goals before pulls to properly separate points
4. **Possession tracking**: A single point can have multiple possessions due to turnovers
5. **Turnover types**:
   - Block (event_type=11): Blocking team gains possession
   - Throwaway/Drop/Stall (event_types=22,20,14): Other team gains possession

#### Example:
If Team A receives the pull (1 O-line possession), throws it away, Team B picks it up (1 D-line possession for Team B), then Team B scores:
- Team A: 0/1 O-line points, 0/1 O-line possessions
- Team B: 1/1 D-line points, 1/1 D-line possessions (a "break")