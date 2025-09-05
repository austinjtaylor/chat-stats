import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration settings for the Sports Stats Chat System"""

    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"

    # SQL Database settings
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./db/sports_stats.db")

    # Query settings
    MAX_RESULTS: int = 10  # Maximum results to return per query
    DEFAULT_TOP_RESULTS_LIMIT: int = 3  # Default limit for "best/top" queries
    DEFAULT_DECIMAL_PLACES: int = 1  # Default decimal places for formatting
    MAX_HISTORY: int = 5  # Number of conversation messages to remember
    MAX_TOOL_ROUNDS: int = 3  # Maximum sequential tool calling rounds per query

    # Data import settings
    BATCH_SIZE: int = 1000  # Batch size for bulk imports

    # Cache settings
    ENABLE_CACHE: bool = True
    CACHE_TTL: int = 300  # Cache time-to-live in seconds


config = Config()


# Validate configuration
def validate_config():
    """Validate configuration settings to prevent common issues"""
    if config.MAX_RESULTS <= 0:
        raise ValueError(f"MAX_RESULTS must be positive, got {config.MAX_RESULTS}")

    if config.MAX_TOOL_ROUNDS <= 0:
        raise ValueError(
            f"MAX_TOOL_ROUNDS must be positive, got {config.MAX_TOOL_ROUNDS}"
        )

    if config.MAX_HISTORY < 0:
        raise ValueError(f"MAX_HISTORY must be non-negative, got {config.MAX_HISTORY}")

    if not config.ANTHROPIC_API_KEY:
        print("WARNING: ANTHROPIC_API_KEY is not set. AI features will not work.")
        print(
            "Please set your ANTHROPIC_API_KEY in the .env file to enable AI responses."
        )
    elif config.ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
        print("WARNING: ANTHROPIC_API_KEY appears to be a placeholder value.")
        print("Please set your actual API key in the .env file to enable AI responses.")


# Run validation on import
validate_config()
