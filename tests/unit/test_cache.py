"""Tests for cache manager."""


import pytest
from orion.config import CacheConfig
from orion.data.cache import CacheManager


class TestCacheManager:
    """Tests for CacheManager."""

    @pytest.fixture
    def cache_config(self) -> CacheConfig:
        """Create cache configuration."""
        return CacheConfig(
            enabled=True,
            max_size=100,
            quote_ttl=300,
            option_chain_ttl=900,
            historical_ttl=3600,
        )

    @pytest.fixture
    def cache_manager(self, cache_config: CacheConfig) -> CacheManager:
        """Create cache manager instance."""
        return CacheManager(cache_config)

    async def test_cache_set_and_get(self, cache_manager: CacheManager) -> None:
        """Cache stores and retrieves values."""
        await cache_manager.set("quote", "AAPL", {"price": 150.0})
        value = await cache_manager.get("quote", "AAPL")

        assert value is not None
        assert value["price"] == 150.0

    async def test_cache_miss(self, cache_manager: CacheManager) -> None:
        """Cache returns None on miss."""
        value = await cache_manager.get("quote", "NONEXISTENT")
        assert value is None

    async def test_cache_disabled(self) -> None:
        """Cache returns None when disabled."""
        config = CacheConfig(
            enabled=False,
            max_size=100,
            quote_ttl=300,
            option_chain_ttl=900,
            historical_ttl=3600,
        )
        cache_manager = CacheManager(config)

        await cache_manager.set("quote", "AAPL", {"price": 150.0})
        value = await cache_manager.get("quote", "AAPL")

        assert value is None

    async def test_get_or_fetch_cache_hit(self, cache_manager: CacheManager) -> None:
        """get_or_fetch returns cached value."""
        # Pre-populate cache
        await cache_manager.set("quote", "AAPL", {"price": 150.0})

        # Should return cached value without calling fetch
        fetch_called = False

        async def fetch_fn() -> dict[str, float]:
            nonlocal fetch_called
            fetch_called = True
            return {"price": 200.0}

        value = await cache_manager.get_or_fetch("quote", "AAPL", fetch_fn)

        assert value["price"] == 150.0
        assert not fetch_called

    async def test_get_or_fetch_cache_miss(self, cache_manager: CacheManager) -> None:
        """get_or_fetch fetches and caches on miss."""
        fetch_called = False

        async def fetch_fn() -> dict[str, float]:
            nonlocal fetch_called
            fetch_called = True
            return {"price": 150.0}

        value = await cache_manager.get_or_fetch("quote", "AAPL", fetch_fn)

        assert value["price"] == 150.0
        assert fetch_called

        # Second call should hit cache
        fetch_called = False
        value2 = await cache_manager.get_or_fetch("quote", "AAPL", fetch_fn)
        assert value2["price"] == 150.0
        assert not fetch_called

    async def test_cache_invalidation(self, cache_manager: CacheManager) -> None:
        """Cache invalidation works correctly."""
        await cache_manager.set("quote", "AAPL", {"price": 150.0})
        await cache_manager.set("quote", "MSFT", {"price": 300.0})

        # Invalidate specific key
        cache_manager.invalidate("quote", "AAPL")

        apple = await cache_manager.get("quote", "AAPL")
        msft = await cache_manager.get("quote", "MSFT")

        assert apple is None
        assert msft is not None

    async def test_clear_all(self, cache_manager: CacheManager) -> None:
        """clear_all removes all cache entries."""
        await cache_manager.set("quote", "AAPL", {"price": 150.0})
        await cache_manager.set("historical", "MSFT", {"data": []})

        cache_manager.clear_all()

        apple = await cache_manager.get("quote", "AAPL")
        msft = await cache_manager.get("historical", "MSFT")

        assert apple is None
        assert msft is None

    async def test_cache_stats(self, cache_manager: CacheManager) -> None:
        """Cache statistics are tracked correctly."""
        # Generate some hits and misses
        await cache_manager.set("quote", "AAPL", {"price": 150.0})

        await cache_manager.get("quote", "AAPL")  # Hit
        await cache_manager.get("quote", "MSFT")  # Miss
        await cache_manager.get("quote", "AAPL")  # Hit

        stats = cache_manager.get_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_requests"] == 3
        assert abs(stats["hit_rate"] - 0.667) < 0.01

    async def test_different_cache_types(self, cache_manager: CacheManager) -> None:
        """Different cache types are isolated."""
        await cache_manager.set("quote", "AAPL", {"type": "quote"})
        await cache_manager.set("historical", "AAPL", {"type": "historical"})

        quote = await cache_manager.get("quote", "AAPL")
        historical = await cache_manager.get("historical", "AAPL")

        assert quote["type"] == "quote"
        assert historical["type"] == "historical"

    async def test_clear_specific_cache_type(self, cache_manager: CacheManager) -> None:
        """Clearing specific cache type leaves others intact."""
        await cache_manager.set("quote", "AAPL", {"price": 150.0})
        await cache_manager.set("historical", "AAPL", {"data": []})

        cache_manager.invalidate("quote")  # Clear all quote cache

        quote = await cache_manager.get("quote", "AAPL")
        historical = await cache_manager.get("historical", "AAPL")

        assert quote is None
        assert historical is not None
