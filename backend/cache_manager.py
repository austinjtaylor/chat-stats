"""
In-memory cache manager for performance optimization.
Provides TTL-based caching with thread-safe operations.
"""

import hashlib
import json
import threading
import time
from typing import Any, Optional


class CacheManager:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache manager.
        
        Args:
            default_ttl: Default time-to-live in seconds
            max_size: Maximum number of cache entries
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        
    def _make_key(self, key: str | dict) -> str:
        """
        Create a cache key from string or dict.
        
        Args:
            key: String key or dict to hash
            
        Returns:
            String cache key
        """
        if isinstance(key, dict):
            # Sort dict keys for consistent hashing
            key_str = json.dumps(key, sort_keys=True)
            return hashlib.md5(key_str.encode()).hexdigest()
        return str(key)
    
    def get(self, key: str | dict) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        cache_key = self._make_key(key)
        
        with self._lock:
            if cache_key in self._cache:
                value, expiry = self._cache[cache_key]
                if time.time() < expiry:
                    self.hits += 1
                    return value
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
            
            self.misses += 1
            return None
    
    def set(self, key: str | dict, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        cache_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        
        with self._lock:
            # Check size limit
            if len(self._cache) >= self.max_size:
                # Remove oldest entries (simple LRU)
                self._evict_oldest()
            
            self._cache[cache_key] = (value, expiry)
    
    def delete(self, key: str | dict) -> bool:
        """
        Delete entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        cache_key = self._make_key(key)
        
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
    
    def _evict_oldest(self) -> None:
        """Evict oldest cache entries to make room."""
        if not self._cache:
            return
            
        # Find and remove expired entries first
        current_time = time.time()
        expired_keys = [
            k for k, (_, expiry) in self._cache.items() 
            if current_time >= expiry
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        # If still over limit, remove oldest entries
        if len(self._cache) >= self.max_size:
            # Remove 10% of oldest entries
            num_to_remove = max(1, self.max_size // 10)
            sorted_keys = sorted(
                self._cache.keys(), 
                key=lambda k: self._cache[k][1]  # Sort by expiry time
            )
            for key in sorted_keys[:num_to_remove]:
                del self._cache[key]
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "entries": len(self._cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "total_requests": total_requests
            }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        removed = 0
        
        with self._lock:
            expired_keys = [
                k for k, (_, expiry) in self._cache.items() 
                if current_time >= expiry
            ]
            
            for key in expired_keys:
                del self._cache[key]
                removed += 1
        
        return removed


# Global cache instance
_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        from config import config
        _cache_instance = CacheManager(
            default_ttl=config.CACHE_TTL,
            max_size=1000
        )
    return _cache_instance


def cache_key_for_query(query: str, params: Optional[dict] = None) -> dict:
    """
    Create a cache key for a SQL query.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        Dict suitable for cache key
    """
    return {
        "type": "query",
        "query": query.strip().lower(),
        "params": params or {}
    }


def cache_key_for_endpoint(endpoint: str, **kwargs) -> dict:
    """
    Create a cache key for an API endpoint.
    
    Args:
        endpoint: Endpoint name
        **kwargs: Additional parameters
        
    Returns:
        Dict suitable for cache key
    """
    return {
        "type": "endpoint",
        "endpoint": endpoint,
        **kwargs
    }