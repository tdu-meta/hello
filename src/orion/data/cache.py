"""Cache manager for market data."""

from collections.abc import Callable
from typing import Any, TypeVar

from cachetools import TTLCache

from ..config import CacheConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CacheManager:
    """Simple in-memory cache manager with TTL support.

    Uses cachetools.TTLCache for automatic expiration.
    Cache keys should be descriptive strings like 'quote:AAPL' or 'historical:MSFT:2024-01-01:2024-12-31'.
    """

    def __init__(self, config: CacheConfig) -> None:
        """Initialize cache manager.

        Args:
            config: Cache configuration
        """
        self.config = config
        self._caches: dict[str, TTLCache[str, Any]] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
        }

        # Create caches for different data types
        self._init_caches()

        logger.info(
            "cache_manager_initialized",
            max_size=config.max_size,
            enabled=config.enabled,
        )

    def _init_caches(self) -> None:
        """Initialize TTL caches for different data types."""
        # Quote cache
        self._caches["quote"] = TTLCache(maxsize=self.config.max_size, ttl=self.config.quote_ttl)

        # Historical data cache
        self._caches["historical"] = TTLCache(
            maxsize=self.config.max_size // 2, ttl=self.config.historical_ttl
        )

        # Option chain cache
        self._caches["options"] = TTLCache(
            maxsize=self.config.max_size // 4, ttl=self.config.option_chain_ttl
        )

        # Company overview cache (fundamentals change slowly)
        self._caches["overview"] = TTLCache(
            maxsize=self.config.max_size // 10, ttl=self.config.historical_ttl
        )

    def _get_cache(self, cache_type: str) -> TTLCache[str, Any]:
        """Get cache for a specific data type."""
        if cache_type not in self._caches:
            # Default cache with 1 hour TTL
            self._caches[cache_type] = TTLCache(maxsize=self.config.max_size, ttl=3600)
        return self._caches[cache_type]

    def _make_key(self, cache_type: str, *parts: str) -> str:
        """Create cache key from parts."""
        return f"{cache_type}:" + ":".join(str(p) for p in parts)

    async def get(self, cache_type: str, key: str) -> Any | None:
        """Get value from cache.

        Args:
            cache_type: Type of cache (quote, historical, options, overview)
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if not self.config.enabled:
            return None

        cache = self._get_cache(cache_type)
        full_key = self._make_key(cache_type, key)

        try:
            value = cache.get(full_key)
            if value is not None:
                self._stats["hits"] += 1
                logger.debug(
                    "cache_hit",
                    cache_type=cache_type,
                    key=key,
                    hits=self._stats["hits"],
                    misses=self._stats["misses"],
                )
                return value
            else:
                self._stats["misses"] += 1
                logger.debug(
                    "cache_miss",
                    cache_type=cache_type,
                    key=key,
                )
                return None
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(
                "cache_get_error",
                cache_type=cache_type,
                key=key,
                error=str(e),
            )
            return None

    async def set(self, cache_type: str, key: str, value: Any) -> None:
        """Set value in cache.

        Args:
            cache_type: Type of cache (quote, historical, options, overview)
            key: Cache key
            value: Value to cache
        """
        if not self.config.enabled:
            return

        cache = self._get_cache(cache_type)
        full_key = self._make_key(cache_type, key)

        try:
            cache[full_key] = value
            logger.debug(
                "cache_set",
                cache_type=cache_type,
                key=key,
            )
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(
                "cache_set_error",
                cache_type=cache_type,
                key=key,
                error=str(e),
            )

    async def get_or_fetch(
        self,
        cache_type: str,
        key: str,
        fetch_fn: Callable[[], Any],
    ) -> Any:
        """Get from cache or fetch if not present.

        Args:
            cache_type: Type of cache
            key: Cache key
            fetch_fn: Async function to call if cache miss

        Returns:
            Cached or freshly fetched value
        """
        # Try cache first
        cached = await self.get(cache_type, key)
        if cached is not None:
            return cached

        # Cache miss - fetch data
        logger.debug(
            "cache_fetch",
            cache_type=cache_type,
            key=key,
        )

        value = await fetch_fn()

        # Store in cache
        await self.set(cache_type, key, value)

        return value

    def invalidate(self, cache_type: str, key: str | None = None) -> None:
        """Invalidate cache entries.

        Args:
            cache_type: Type of cache
            key: Specific key to invalidate (if None, clears entire cache type)
        """
        if not self.config.enabled:
            return

        cache = self._get_cache(cache_type)

        if key is None:
            # Clear entire cache for this type
            cache.clear()
            logger.info(
                "cache_cleared",
                cache_type=cache_type,
            )
        else:
            # Clear specific key
            full_key = self._make_key(cache_type, key)
            cache.pop(full_key, None)
            logger.debug(
                "cache_invalidated",
                cache_type=cache_type,
                key=key,
            )

    def clear_all(self) -> None:
        """Clear all caches."""
        for cache_type, cache in self._caches.items():
            cache.clear()
            logger.info("cache_cleared", cache_type=cache_type)

        # Reset stats
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats (hits, misses, hit_rate, sizes)
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0

        sizes = {cache_type: len(cache) for cache_type, cache in self._caches.items()}

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "cache_sizes": sizes,
        }

    def log_stats(self) -> None:
        """Log current cache statistics."""
        stats = self.get_stats()
        logger.info("cache_stats", **stats)
