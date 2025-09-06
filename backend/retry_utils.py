"""
Retry utilities for handling API rate limits with exponential backoff.
Ensures backward compatibility by transparently handling rate limit errors.
"""

import time
import random
from functools import wraps
from typing import Callable, Any, Optional
import anthropic


class RateLimitRetry:
    """
    Decorator for handling Anthropic rate limit errors with exponential backoff.
    
    This decorator will automatically retry requests that fail due to rate limits,
    using exponential backoff with jitter to avoid thundering herd problems.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 4)
        base_delay: Initial delay in seconds (default: 2.0)
        max_delay: Maximum delay in seconds (default: 32.0)
        jitter_factor: Jitter factor (0-1) to randomize delays (default: 0.1)
    """
    
    def __init__(
        self, 
        max_retries: int = 4, 
        base_delay: float = 2.0, 
        max_delay: float = 32.0,
        jitter_factor: float = 0.1
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception: Optional[Exception] = None
            
            for attempt in range(self.max_retries + 1):
                try:
                    # Try to execute the function
                    return func(*args, **kwargs)
                    
                except anthropic.RateLimitError as e:
                    # Handle rate limit errors specifically
                    last_exception = e
                    
                    # If we've exhausted retries, raise the exception
                    if attempt == self.max_retries:
                        print(f"Rate limit retry exhausted after {self.max_retries} attempts")
                        raise
                    
                    # Calculate exponential backoff delay
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0, delay * self.jitter_factor)
                    total_delay = delay + jitter
                    
                    print(f"Rate limit hit, retrying in {total_delay:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(total_delay)
                    
                except Exception:
                    # Don't retry other types of exceptions - preserve original behavior
                    raise
            
            # This should never be reached, but handle it gracefully
            if last_exception:
                raise last_exception
            
        return wrapper


def with_rate_limit_retry(
    func: Optional[Callable] = None,
    max_retries: int = 4,
    base_delay: float = 2.0,
    max_delay: float = 32.0
) -> Callable:
    """
    Convenience function to apply rate limit retry with custom parameters.
    
    Can be used as a decorator with or without arguments:
    
    @with_rate_limit_retry
    def my_function():
        pass
    
    @with_rate_limit_retry(max_retries=5, base_delay=3.0)
    def my_function():
        pass
    """
    def decorator(f: Callable) -> Callable:
        return RateLimitRetry(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay
        )(f)
    
    if func is None:
        # Called with arguments
        return decorator
    else:
        # Called without arguments
        return decorator(func)