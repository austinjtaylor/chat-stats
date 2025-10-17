import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


@dataclass
class Config:
    """Configuration settings for the Sports Stats Chat System"""

    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"

    # Database settings (PostgreSQL via Supabase - REQUIRED)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Supabase settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # Stripe settings
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

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

    # Rate limit handling settings
    RATE_LIMIT_MAX_RETRIES: int = 4  # Maximum number of retry attempts
    RATE_LIMIT_BASE_DELAY: float = 2.0  # Initial delay in seconds
    RATE_LIMIT_MAX_DELAY: float = 32.0  # Maximum delay in seconds
    ENABLE_RATE_LIMIT_RETRY: bool = True  # Enable automatic retry on rate limits

    # Token optimization settings
    OPTIMIZE_SYSTEM_PROMPT: bool = True  # Use optimized shorter system prompt
    MAX_PROMPT_TOKENS: int = 5000  # Target maximum tokens for system prompt


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

    # Anthropic API validation
    if not config.ANTHROPIC_API_KEY:
        print("WARNING: ANTHROPIC_API_KEY is not set. AI features will not work.")
        print(
            "Please set your ANTHROPIC_API_KEY in the .env file to enable AI responses."
        )
    elif config.ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
        print("WARNING: ANTHROPIC_API_KEY appears to be a placeholder value.")
        print("Please set your actual API key in the .env file to enable AI responses.")

    # Database validation - DATABASE_URL is required
    if not config.DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is required. Please set it in your .env file.\n"
            "Get your connection string from Supabase: Settings → Database → Connection String → URI"
        )

    print("✅ Using PostgreSQL database (Supabase)")

    # Validate Supabase configuration
    if not config.SUPABASE_URL:
        print("⚠️  WARNING: SUPABASE_URL is not set (required for authentication)")
    if not config.SUPABASE_SERVICE_KEY:
        print("⚠️  WARNING: SUPABASE_SERVICE_KEY is not set (required for authentication)")


# Run validation on import
validate_config()
