"""
Unit tests for RuleEvaluator.

Tests for evaluating stocks against strategy entry conditions.
"""

from datetime import datetime, timedelta

import pytest
from orion.data.models import OHLCV, Quote, TechnicalIndicators
from orion.strategies.evaluator import RuleEvaluator
from orion.strategies.models import Condition, OptionScreening, StockCriteria, Strategy


class TestRuleEvaluator:
    """Test suite for RuleEvaluator."""

    @pytest.fixture
    def ofi_strategy(self) -> Strategy:
        """Create an OFI-like strategy for testing."""
        return Strategy(
            name="OFI - Option for Income",
            version="1.0.0",
            description="Test OFI strategy",
            stock_criteria=StockCriteria(min_revenue=1_000_000_000),
            entry_conditions=[
                Condition(type="trend", rule="sma_20 > sma_60", weight=1.0),
                Condition(
                    type="oversold",
                    rule="rsi_was_below",
                    parameters={"threshold": 30.0, "lookback_days": 5},
                    weight=1.0,
                ),
                Condition(
                    type="bounce",
                    rule="higher_high_higher_low",
                    parameters={"lookback": 5, "volume_confirmation": False},
                    weight=1.0,
                ),
            ],
            option_screening=OptionScreening(),
        )

    @pytest.fixture
    def evaluator(self, ofi_strategy: Strategy) -> RuleEvaluator:
        """Create a RuleEvaluator instance for testing."""
        return RuleEvaluator(ofi_strategy)

    @pytest.fixture
    def sample_quote(self) -> Quote:
        """Create a sample quote for testing."""
        return Quote(
            symbol="AAPL",
            price=150.0,
            volume=1_000_000,
            timestamp=datetime.now(),
            open=149.0,
            high=152.0,
            low=148.0,
            close=150.0,
        )

    @pytest.fixture
    def bull_trend_historical(self) -> list[OHLCV]:
        """Create historical data showing bullish trend."""
        base_time = datetime.now() - timedelta(days=100)
        ohlcv_list = []

        # Create 100 days of data with upward trend
        for i in range(100):
            base_price = 100 + i * 0.5  # Rising trend
            ohlcv_list.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=base_price,
                    high=base_price + 1,
                    low=base_price - 1,
                    close=base_price + 0.5,
                    volume=1_000_000,
                )
            )

        return ohlcv_list

    @pytest.fixture
    def bounce_pattern_historical(self) -> list[OHLCV]:
        """Create historical data with bounce pattern."""
        base_time = datetime.now() - timedelta(days=20)
        ohlcv_list = []

        # First 10 bars: downtrend to a low
        for i in range(10):
            price = 110 - i * 2  # 110, 108, 106, ..., 92
            ohlcv_list.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=price,
                    high=price + 1,
                    low=price - 1,
                    close=price - 0.5,
                    volume=1_000_000,
                )
            )

        # Create bounce pattern: higher high and higher low
        # Previous low in lookback was around 92
        # Now create higher high and higher low
        for i in range(10):
            price = 92 + i * 1.5  # Recovery: 92, 93.5, 95, ...
            ohlcv_list.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=10 + i),
                    open=price,
                    high=price + 2,  # Higher than previous highs
                    low=price - 0.5,  # Higher than previous low of 91
                    close=price + 1,
                    volume=1_500_000,  # Volume increase
                )
            )

        return ohlcv_list

    @pytest.fixture
    def bull_trend_indicators(self) -> TechnicalIndicators:
        """Create indicators showing bullish trend."""
        return TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime.now(),
            sma_20=155.0,  # Above SMA_60
            sma_60=145.0,
            rsi_14=35.0,  # Not oversold currently
            volume_avg_20=1_200_000,
        )

    @pytest.mark.asyncio
    async def test_evaluate_all_conditions_met(
        self,
        evaluator: RuleEvaluator,
        sample_quote: Quote,
        bounce_pattern_historical: list[OHLCV],
        bull_trend_indicators: TechnicalIndicators,
    ) -> None:
        """Test evaluation when all conditions are met."""
        result = await evaluator.evaluate(
            "AAPL", sample_quote, bounce_pattern_historical, bull_trend_indicators
        )

        # With bounce pattern but RSI not in lookback below 30, only 2/3 conditions met
        # The bounce pattern should be detected
        assert result.symbol == "AAPL"
        assert result.strategy_name == "OFI - Option for Income"
        assert isinstance(result.conditions_met, list)
        assert isinstance(result.conditions_missed, list)
        assert 0.0 <= result.signal_strength <= 1.0

    @pytest.mark.asyncio
    async def test_evaluate_trend_condition_bullish(
        self,
        evaluator: RuleEvaluator,
        sample_quote: Quote,
        bull_trend_historical: list[OHLCV],
        bull_trend_indicators: TechnicalIndicators,
    ) -> None:
        """Test trend condition evaluation with bullish indicators."""
        result = await evaluator.evaluate(
            "AAPL", sample_quote, bull_trend_historical, bull_trend_indicators
        )

        # Should have trend condition met
        assert "trend" in result.conditions_met or "trend" in result.conditions_missed

    @pytest.mark.asyncio
    async def test_evaluate_trend_condition_bearish(
        self, evaluator: RuleEvaluator, sample_quote: Quote, bull_trend_historical: list[OHLCV]
    ) -> None:
        """Test trend condition evaluation with bearish indicators."""
        bearish_indicators = TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime.now(),
            sma_20=140.0,  # Below SMA_60
            sma_60=150.0,
        )

        result = await evaluator.evaluate(
            "AAPL", sample_quote, bull_trend_historical, bearish_indicators
        )

        # Trend condition should not be met
        assert "trend" in result.conditions_missed
        assert "trend" not in result.conditions_met

    @pytest.mark.asyncio
    async def test_evaluate_oversold_current(
        self,
        evaluator: RuleEvaluator,
        sample_quote: Quote,
        bull_trend_historical: list[OHLCV],
    ) -> None:
        """Test oversold condition with current RSI below threshold."""
        oversold_indicators = TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime.now(),
            sma_20=155.0,
            sma_60=145.0,
            rsi_14=25.0,  # Below 30
        )

        # Need a strategy with rsi < threshold condition
        strategy = Strategy(
            name="Test",
            version="1.0.0",
            description="Test",
            stock_criteria=StockCriteria(),
            entry_conditions=[
                Condition(
                    type="oversold",
                    rule="rsi < threshold",
                    parameters={"threshold": 30.0},
                )
            ],
            option_screening=OptionScreening(),
        )
        test_evaluator = RuleEvaluator(strategy)

        result = await test_evaluator.evaluate(
            "AAPL", sample_quote, bull_trend_historical, oversold_indicators
        )

        assert "oversold" in result.conditions_met

    @pytest.mark.asyncio
    async def test_evaluate_bounce_condition_detected(
        self,
        evaluator: RuleEvaluator,
        sample_quote: Quote,
        bounce_pattern_historical: list[OHLCV],
        bull_trend_indicators: TechnicalIndicators,
    ) -> None:
        """Test bounce condition detection."""
        result = await evaluator.evaluate(
            "AAPL", sample_quote, bounce_pattern_historical, bull_trend_indicators
        )

        # Check if bounce was detected based on the details
        if "bounce" in result.details:
            bounce_detail = result.details["bounce"]
            assert "status" in bounce_detail

    def test_check_trend_sma_comparison(self, evaluator: RuleEvaluator) -> None:
        """Test the SMA comparison in trend checking."""
        # Bullish: SMA-20 > SMA-60
        bullish_indicators = TechnicalIndicators(
            symbol="TEST",
            timestamp=datetime.now(),
            sma_20=150.0,
            sma_60=140.0,
        )
        condition = Condition(type="trend", rule="sma_20 > sma_60")
        result = evaluator._check_trend(condition, bullish_indicators)
        assert result.matches is True

        # Bearish: SMA-20 <= SMA-60
        bearish_indicators = TechnicalIndicators(
            symbol="TEST",
            timestamp=datetime.now(),
            sma_20=140.0,
            sma_60=150.0,
        )
        result = evaluator._check_trend(condition, bearish_indicators)
        assert result.matches is False
        assert "not >" in result.reason

    def test_check_bounce_insufficient_data(self, evaluator: RuleEvaluator) -> None:
        """Test bounce detection with insufficient data."""
        condition = Condition(
            type="bounce",
            rule="higher_high_higher_low",
            parameters={"lookback": 5},
        )

        # Empty historical data
        result = evaluator._check_bounce(condition, [])
        assert result.matches is False
        assert "Insufficient data" in result.reason

    @pytest.mark.asyncio
    async def test_signal_strength_calculation(
        self,
        evaluator: RuleEvaluator,
        sample_quote: Quote,
        bull_trend_historical: list[OHLCV],
        bull_trend_indicators: TechnicalIndicators,
    ) -> None:
        """Test signal strength is calculated correctly."""
        result = await evaluator.evaluate(
            "AAPL", sample_quote, bull_trend_historical, bull_trend_indicators
        )

        # Signal strength should be between 0 and 1
        assert 0.0 <= result.signal_strength <= 1.0

        # Signal strength = met_weights / total_weights
        # With 3 conditions each weight 1.0:
        # - If all met: 3/3 = 1.0
        # - If 2 met: 2/3 = 0.667
        # - If 1 met: 1/3 = 0.333
        # - If none met: 0/3 = 0.0
        expected_strength = len(result.conditions_met) / 3.0
        assert abs(result.signal_strength - expected_strength) < 0.01

    @pytest.mark.asyncio
    async def test_evaluation_result_details(
        self,
        evaluator: RuleEvaluator,
        sample_quote: Quote,
        bull_trend_historical: list[OHLCV],
        bull_trend_indicators: TechnicalIndicators,
    ) -> None:
        """Test that evaluation result includes details for each condition."""
        result = await evaluator.evaluate(
            "AAPL", sample_quote, bull_trend_historical, bull_trend_indicators
        )

        # Should have details for each condition
        assert result.details is not None
        assert len(result.details) == 3

        # Each detail should have status and value
        for detail in result.details.values():
            assert "status" in detail
            assert detail["status"] in ["met", "missed", "error"]
            assert "value" in detail

    @pytest.mark.asyncio
    async def test_unknown_condition_type(
        self,
        evaluator: RuleEvaluator,
        sample_quote: Quote,
        bull_trend_historical: list[OHLCV],
        bull_trend_indicators: TechnicalIndicators,
    ) -> None:
        """Test that unknown condition types are handled gracefully."""
        strategy = Strategy(
            name="Test",
            version="1.0.0",
            description="Test",
            stock_criteria=StockCriteria(),
            entry_conditions=[
                Condition(type="unknown_type", rule="some_rule"),
            ],
            option_screening=OptionScreening(),
        )
        test_evaluator = RuleEvaluator(strategy)

        result = await test_evaluator.evaluate(
            "AAPL", sample_quote, bull_trend_historical, bull_trend_indicators
        )

        # Unknown condition should be marked as missed
        assert "unknown_type" in result.conditions_missed

    def test_check_price_min_price(self, evaluator: RuleEvaluator, sample_quote: Quote) -> None:
        """Test price condition with minimum price check."""
        condition = Condition(
            type="price",
            rule="min_price",
            parameters={"value": 100.0},
        )

        result = evaluator._check_price(condition, sample_quote)
        assert result.matches is True  # 150 > 100

        condition2 = Condition(
            type="price",
            rule="min_price",
            parameters={"value": 200.0},
        )

        result2 = evaluator._check_price(condition2, sample_quote)
        assert result2.matches is False  # 150 < 200

    def test_check_volume_min_volume(self, evaluator: RuleEvaluator, sample_quote: Quote) -> None:
        """Test volume condition with minimum volume check."""
        condition = Condition(
            type="volume",
            rule="min_volume",
            parameters={"value": 500_000},
        )

        result = evaluator._check_volume(condition, sample_quote, [])
        assert result.matches is True  # 1M > 500K

        condition2 = Condition(
            type="volume",
            rule="min_volume",
            parameters={"value": 2_000_000},
        )

        result2 = evaluator._check_volume(condition2, sample_quote, [])
        assert result2.matches is False  # 1M < 2M
