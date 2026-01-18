"""
Unit tests for strategy models.

Tests for Condition, Strategy, StockCriteria, OptionScreening, and related models.
"""

from dataclasses import FrozenInstanceError

import pytest
from orion.strategies.models import (
    Condition,
    OptionRecommendation,
    OptionScreening,
    StockCriteria,
    Strategy,
)


class TestCondition:
    """Test suite for Condition model."""

    def test_create_condition_minimal(self) -> None:
        """Test creating a condition with minimal required fields."""
        condition = Condition(type="trend", rule="sma_20 > sma_60")
        assert condition.type == "trend"
        assert condition.rule == "sma_20 > sma_60"
        assert condition.parameters == {}
        assert condition.description == ""
        assert condition.weight == 1.0

    def test_create_condition_full(self) -> None:
        """Test creating a condition with all fields."""
        condition = Condition(
            type="oversold",
            rule="rsi < 30",
            parameters={"threshold": 30, "lookback": 5},
            description="RSI below 30",
            weight=2.0,
        )
        assert condition.type == "oversold"
        assert condition.rule == "rsi < 30"
        assert condition.parameters == {"threshold": 30, "lookback": 5}
        assert condition.description == "RSI below 30"
        assert condition.weight == 2.0

    def test_condition_is_frozen(self) -> None:
        """Test that Condition is immutable (frozen)."""
        condition = Condition(type="trend", rule="sma_20 > sma_60")
        with pytest.raises(FrozenInstanceError):
            condition.type = "oversold"  # type: ignore[misc]


class TestStockCriteria:
    """Test suite for StockCriteria model."""

    def test_create_empty_criteria(self) -> None:
        """Test creating empty stock criteria."""
        criteria = StockCriteria()
        assert criteria.min_revenue is None
        assert criteria.min_market_cap is None
        assert criteria.max_market_cap is None
        assert criteria.min_price is None
        assert criteria.max_price is None
        assert criteria.exchanges == []
        assert criteria.sectors == []
        assert criteria.exclude_sectors == []

    def test_create_full_criteria(self) -> None:
        """Test creating stock criteria with all fields."""
        criteria = StockCriteria(
            min_revenue=1_000_000_000,
            min_market_cap=500_000_000,
            max_market_cap=1_000_000_000_000,
            min_price=10.0,
            max_price=500.0,
            exchanges=["NYSE", "NASDAQ"],
            sectors=["Technology", "Healthcare"],
            exclude_sectors=["Utilities"],
        )
        assert criteria.min_revenue == 1_000_000_000
        assert criteria.min_market_cap == 500_000_000
        assert criteria.max_market_cap == 1_000_000_000_000
        assert criteria.min_price == 10.0
        assert criteria.max_price == 500.0
        assert criteria.exchanges == ["NYSE", "NASDAQ"]
        assert criteria.sectors == ["Technology", "Healthcare"]
        assert criteria.exclude_sectors == ["Utilities"]


class TestOptionScreening:
    """Test suite for OptionScreening model."""

    def test_create_default_screening(self) -> None:
        """Test creating option screening with defaults."""
        screening = OptionScreening()
        assert screening.min_premium_yield == 0.02
        assert screening.target_dte == 30
        assert screening.min_dte == 7
        assert screening.max_dte == 60
        assert screening.tolerance == 0.05
        assert screening.min_volume == 100
        assert screening.min_open_interest == 500

    def test_create_custom_screening(self) -> None:
        """Test creating option screening with custom values."""
        screening = OptionScreening(
            min_premium_yield=0.03,
            target_dte=45,
            min_dte=14,
            max_dte=90,
            tolerance=0.10,
            min_volume=200,
            min_open_interest=1000,
        )
        assert screening.min_premium_yield == 0.03
        assert screening.target_dte == 45
        assert screening.min_dte == 14
        assert screening.max_dte == 90
        assert screening.tolerance == 0.10
        assert screening.min_volume == 200
        assert screening.min_open_interest == 1000


class TestStrategy:
    """Test suite for Strategy model."""

    @pytest.fixture
    def sample_conditions(self) -> list[Condition]:
        """Create sample conditions for testing."""
        return [
            Condition(type="trend", rule="sma_20 > sma_60"),
            Condition(type="oversold", rule="rsi < 30"),
            Condition(type="bounce", rule="higher_high_higher_low"),
        ]

    @pytest.fixture
    def sample_stock_criteria(self) -> StockCriteria:
        """Create sample stock criteria for testing."""
        return StockCriteria(min_revenue=1_000_000_000, min_market_cap=500_000_000)

    @pytest.fixture
    def sample_option_screening(self) -> OptionScreening:
        """Create sample option screening for testing."""
        return OptionScreening(min_premium_yield=0.02)

    def test_create_strategy_valid(
        self,
        sample_conditions: list[Condition],
        sample_stock_criteria: StockCriteria,
        sample_option_screening: OptionScreening,
    ) -> None:
        """Test creating a valid strategy."""
        strategy = Strategy(
            name="Test Strategy",
            version="1.0.0",
            description="A test strategy",
            stock_criteria=sample_stock_criteria,
            entry_conditions=sample_conditions,
            option_screening=sample_option_screening,
        )
        assert strategy.name == "Test Strategy"
        assert strategy.version == "1.0.0"
        assert strategy.description == "A test strategy"
        assert len(strategy.entry_conditions) == 3
        assert strategy.tags == []

    def test_create_strategy_with_tags(
        self,
        sample_conditions: list[Condition],
        sample_stock_criteria: StockCriteria,
        sample_option_screening: OptionScreening,
    ) -> None:
        """Test creating a strategy with tags."""
        strategy = Strategy(
            name="Test Strategy",
            version="1.0.0",
            description="A test strategy",
            stock_criteria=sample_stock_criteria,
            entry_conditions=sample_conditions,
            option_screening=sample_option_screening,
            tags=["income", "puts"],
        )
        assert strategy.tags == ["income", "puts"]

    def test_strategy_empty_name_raises_error(
        self,
        sample_conditions: list[Condition],
        sample_stock_criteria: StockCriteria,
        sample_option_screening: OptionScreening,
    ) -> None:
        """Test that empty strategy name raises error."""
        with pytest.raises(ValueError, match="name"):
            Strategy(
                name="",
                version="1.0.0",
                description="A test strategy",
                stock_criteria=sample_stock_criteria,
                entry_conditions=sample_conditions,
                option_screening=sample_option_screening,
            )

    def test_strategy_empty_version_raises_error(
        self,
        sample_conditions: list[Condition],
        sample_stock_criteria: StockCriteria,
        sample_option_screening: OptionScreening,
    ) -> None:
        """Test that empty version raises error."""
        with pytest.raises(ValueError, match="version"):
            Strategy(
                name="Test Strategy",
                version="",
                description="A test strategy",
                stock_criteria=sample_stock_criteria,
                entry_conditions=sample_conditions,
                option_screening=sample_option_screening,
            )

    def test_strategy_no_conditions_raises_error(
        self,
        sample_stock_criteria: StockCriteria,
        sample_option_screening: OptionScreening,
    ) -> None:
        """Test that strategy with no conditions raises error."""
        with pytest.raises(ValueError, match="at least one entry condition"):
            Strategy(
                name="Test Strategy",
                version="1.0.0",
                description="A test strategy",
                stock_criteria=sample_stock_criteria,
                entry_conditions=[],
                option_screening=sample_option_screening,
            )

    def test_strategy_is_frozen(
        self,
        sample_conditions: list[Condition],
        sample_stock_criteria: StockCriteria,
        sample_option_screening: OptionScreening,
    ) -> None:
        """Test that Strategy is immutable (frozen)."""
        strategy = Strategy(
            name="Test Strategy",
            version="1.0.0",
            description="A test strategy",
            stock_criteria=sample_stock_criteria,
            entry_conditions=sample_conditions,
            option_screening=sample_option_screening,
        )
        with pytest.raises(FrozenInstanceError):
            strategy.name = "New Name"  # type: ignore[misc]


class TestOptionRecommendation:
    """Test suite for OptionRecommendation model."""

    def test_create_recommendation(self) -> None:
        """Test creating an option recommendation."""
        rec = OptionRecommendation(
            symbol="AAPL240119P00150000",
            underlying_symbol="AAPL",
            strike=150.0,
            expiration=None,
            option_type="put",
            bid=2.50,
            ask=2.60,
            mid_price=2.55,
            premium_yield=0.15,
            volume=500,
            open_interest=1000,
            implied_volatility=0.25,
            delta=-0.45,
            reason="Good yield with 30 days to expiration",
        )
        assert rec.symbol == "AAPL240119P00150000"
        assert rec.underlying_symbol == "AAPL"
        assert rec.strike == 150.0
        assert rec.mid_price == 2.55
        assert rec.premium_yield == 0.15
        assert rec.delta == -0.45

    def test_create_recommendation_minimal(self) -> None:
        """Test creating a recommendation with minimal required fields."""
        rec = OptionRecommendation(
            symbol="AAPL240119P00150000",
            underlying_symbol="AAPL",
            strike=150.0,
            expiration=None,
            option_type="put",
            bid=2.50,
            ask=2.60,
            mid_price=2.55,
            premium_yield=0.15,
            volume=500,
            open_interest=1000,
        )
        assert rec.symbol == "AAPL240119P00150000"
        assert rec.implied_volatility is None
        assert rec.delta is None
        assert rec.reason == ""
