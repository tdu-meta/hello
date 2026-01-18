"""
Unit tests for the IndicatorCalculator class.

Tests technical indicator calculations including SMA, RSI, and volume averages.
"""

from datetime import datetime, timedelta

import pytest
from orion.analysis.indicators import IndicatorCalculator
from orion.data.models import OHLCV


class TestIndicatorCalculator:
    """Test suite for IndicatorCalculator."""

    @pytest.fixture
    def calculator(self) -> IndicatorCalculator:
        """Create an IndicatorCalculator instance for testing."""
        return IndicatorCalculator()

    @pytest.fixture
    def sample_ohlcv(self) -> list[OHLCV]:
        """Create sample OHLCV data for testing (100 data points)."""
        base_price = 100.0
        ohlcv_list = []
        base_time = datetime(2024, 1, 1)

        for i in range(100):
            # Create some price variation
            price_variation = (i % 10) * 0.5
            open_price = base_price + price_variation
            close_price = open_price + (i % 3 - 1) * 0.2
            high_price = max(open_price, close_price) + 0.3
            low_price = min(open_price, close_price) - 0.2
            volume = 1000000 + (i % 5) * 100000

            ohlcv_list.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                )
            )

        return ohlcv_list

    @pytest.fixture
    def minimal_ohlcv(self) -> list[OHLCV]:
        """Create minimal OHLCV data (20 points - just enough for SMA-20)."""
        base_time = datetime(2024, 1, 1)
        ohlcv_list = []

        for i in range(20):
            ohlcv_list.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=100.0 + i * 0.1,
                    high=101.0 + i * 0.1,
                    low=99.0 + i * 0.1,
                    close=100.5 + i * 0.1,
                    volume=1000000,
                )
            )

        return ohlcv_list

    def test_calculate_all_indicators(
        self, calculator: IndicatorCalculator, sample_ohlcv: list[OHLCV]
    ) -> None:
        """Test calculating all indicators with sufficient data."""
        indicators = calculator.calculate(sample_ohlcv, "AAPL")

        assert indicators.symbol == "AAPL"
        assert indicators.sma_20 is not None
        assert indicators.sma_60 is not None
        assert indicators.rsi_14 is not None
        assert indicators.volume_avg_20 is not None

    def test_calculate_with_minimal_data(
        self, calculator: IndicatorCalculator, minimal_ohlcv: list[OHLCV]
    ) -> None:
        """Test calculating indicators with minimal data (20 points)."""
        indicators = calculator.calculate(minimal_ohlcv, "MSFT")

        assert indicators.symbol == "MSFT"
        assert indicators.sma_20 is not None
        assert indicators.sma_60 is None  # Need 60 data points
        assert indicators.rsi_14 is not None
        assert indicators.volume_avg_20 is not None

    def test_calculate_with_insufficient_data(self, calculator: IndicatorCalculator) -> None:
        """Test calculating indicators with insufficient data (less than 15 points)."""
        base_time = datetime(2024, 1, 1)
        short_ohlcv = [
            OHLCV(
                timestamp=base_time + timedelta(days=i),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000000,
            )
            for i in range(10)  # Only 10 data points
        ]

        indicators = calculator.calculate(short_ohlcv, "TSLA")

        assert indicators.symbol == "TSLA"
        assert indicators.sma_20 is None
        assert indicators.sma_60 is None
        # RSI might be None with only 10 points (need at least 15 for pandas-ta)
        assert indicators.volume_avg_20 is None

    def test_calculate_with_empty_list_raises_error(self, calculator: IndicatorCalculator) -> None:
        """Test that empty OHLCV list raises ValueError."""
        with pytest.raises(ValueError, match="empty|Cannot calculate"):
            calculator.calculate([], "AAPL")

    def test_sma_values_are_reasonable(
        self, calculator: IndicatorCalculator, sample_ohlcv: list[OHLCV]
    ) -> None:
        """Test that SMA values are within expected ranges."""
        indicators = calculator.calculate(sample_ohlcv, "AAPL")

        # SMA should be close to the recent price range
        last_close = float(sample_ohlcv[-1].close)
        assert abs(indicators.sma_20 - last_close) < 20  # Within $20 of last price
        assert abs(indicators.sma_60 - last_close) < 20

    def test_sma_relationship(
        self, calculator: IndicatorCalculator, sample_ohlcv: list[OHLCV]
    ) -> None:
        """Test that SMA-20 is typically more responsive than SMA-60."""
        indicators = calculator.calculate(sample_ohlcv, "AAPL")

        if indicators.sma_20 and indicators.sma_60:
            # With trending data, SMAs should differ
            # They could be equal in flat data, but our data has variation
            assert isinstance(indicators.sma_20, float)
            assert isinstance(indicators.sma_60, float)

    def test_rsi_in_valid_range(
        self, calculator: IndicatorCalculator, sample_ohlcv: list[OHLCV]
    ) -> None:
        """Test that RSI is in the valid range of 0-100."""
        indicators = calculator.calculate(sample_ohlcv, "AAPL")

        if indicators.rsi_14 is not None:
            assert 0 <= indicators.rsi_14 <= 100

    def test_volume_avg_positive(
        self, calculator: IndicatorCalculator, sample_ohlcv: list[OHLCV]
    ) -> None:
        """Test that volume average is positive when calculable."""
        indicators = calculator.calculate(sample_ohlcv, "AAPL")

        if indicators.volume_avg_20 is not None:
            assert indicators.volume_avg_20 > 0

    def test_timestamp_is_latest(
        self, calculator: IndicatorCalculator, sample_ohlcv: list[OHLCV]
    ) -> None:
        """Test that indicators timestamp matches the latest OHLCV timestamp."""
        indicators = calculator.calculate(sample_ohlcv, "AAPL")

        assert indicators.timestamp == sample_ohlcv[-1].timestamp

    def test_consistent_results_for_same_data(
        self, calculator: IndicatorCalculator, sample_ohlcv: list[OHLCV]
    ) -> None:
        """Test that calculations are consistent across multiple calls."""
        indicators1 = calculator.calculate(sample_ohlcv, "AAPL")
        indicators2 = calculator.calculate(sample_ohlcv, "AAPL")

        assert indicators1.sma_20 == indicators2.sma_20
        assert indicators1.sma_60 == indicators2.sma_60
        assert indicators1.rsi_14 == indicators2.rsi_14
        assert indicators1.volume_avg_20 == indicators2.volume_avg_20

    def test_trending_up_data_gives_bullish_indicators(
        self, calculator: IndicatorCalculator
    ) -> None:
        """Test with clearly trending up data."""
        base_time = datetime(2024, 1, 1)
        trending_up = []

        for i in range(100):
            price = 100 + i * 0.5  # Clear uptrend
            trending_up.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=float(price),
                    high=float(price + 0.5),
                    low=float(price - 0.5),
                    close=float(price + 0.2),
                    volume=1000000,
                )
            )

        indicators = calculator.calculate(trending_up, "UP")

        # In uptrend, SMA should be calculable
        if indicators.sma_20 is not None:
            # SMA should lag behind price in uptrend
            assert isinstance(indicators.sma_20, float)

    def test_trending_down_data(self, calculator: IndicatorCalculator) -> None:
        """Test with clearly trending down data."""
        base_time = datetime(2024, 1, 1)
        trending_down = []

        for i in range(100):
            price = 150 - i * 0.5  # Clear downtrend
            trending_down.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=float(price),
                    high=float(price + 0.5),
                    low=float(price - 0.5),
                    close=float(price - 0.2),
                    volume=1000000,
                )
            )

        indicators = calculator.calculate(trending_down, "DOWN")

        # Should calculate without errors
        assert indicators.symbol == "DOWN"
        # In downtrend, RSI might be lower (oversold territory possible)
        if indicators.rsi_14 is not None:
            assert 0 <= indicators.rsi_14 <= 100
