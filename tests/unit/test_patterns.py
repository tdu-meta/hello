"""
Unit tests for the PatternDetector class.

Tests chart pattern detection including bounce patterns and volume confirmation.
"""

from datetime import datetime, timedelta

import pytest
from orion.analysis.patterns import BouncePatternResult, PatternDetector
from orion.data.models import OHLCV


class TestPatternDetector:
    """Test suite for PatternDetector."""

    @pytest.fixture
    def detector(self) -> PatternDetector:
        """Create a PatternDetector instance for testing."""
        return PatternDetector()

    @pytest.fixture
    def base_time(self) -> datetime:
        """Base time for test data generation."""
        return datetime(2024, 1, 1)

    @pytest.fixture
    def bounce_pattern_ohlcv(self, base_time: datetime) -> list[OHLCV]:
        """Create OHLCV data exhibiting a bounce pattern (higher high, higher low)."""
        data = []

        # Previous period: lower high and lower low
        for i in range(5):
            data.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=100.0,
                    high=102.0 - i * 0.1,  # Declining highs
                    low=98.0 - i * 0.1,  # Declining lows
                    close=100.5,
                    volume=1000000,
                )
            )

        # Current bar: higher high and higher low
        data.append(
            OHLCV(
                timestamp=base_time + timedelta(days=5),
                open=100.0,
                high=103.0,  # Higher than previous high of ~101.5
                low=99.0,  # Higher than previous low of ~97.5
                close=102.0,
                volume=1000000,
            )
        )

        return data

    @pytest.fixture
    def no_bounce_pattern_ohlcv(self, base_time: datetime) -> list[OHLCV]:
        """Create OHLCV data without a bounce pattern."""
        data = []

        # Previous period
        for i in range(5):
            data.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=100.0,
                    high=102.0,
                    low=98.0,
                    close=100.5,
                    volume=1000000,
                )
            )

        # Current bar: lower high (not a bounce)
        data.append(
            OHLCV(
                timestamp=base_time + timedelta(days=5),
                open=100.0,
                high=101.0,  # Lower than previous high of 102
                low=98.5,  # Higher low, but need BOTH higher
                close=100.0,
                volume=1000000,
            )
        )

        return data

    @pytest.fixture
    def volume_spike_ohlcv(self, base_time: datetime) -> list[OHLCV]:
        """Create OHLCV data with volume spike."""
        data = []

        # Previous bars with normal volume
        for i in range(20):
            data.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000000,  # Normal volume
                )
            )

        # Current bar with volume spike
        data.append(
            OHLCV(
                timestamp=base_time + timedelta(days=20),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1500000,  # 1.5x normal volume - above 1.2 threshold
            )
        )

        return data

    @pytest.fixture
    def normal_volume_ohlcv(self, base_time: datetime) -> list[OHLCV]:
        """Create OHLCV data without volume spike."""
        data = []

        for i in range(21):
            data.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000000,  # Consistent volume
                )
            )

        return data

    def test_detect_bounce_true(
        self, detector: PatternDetector, bounce_pattern_ohlcv: list[OHLCV]
    ) -> None:
        """Test bounce detection with valid bounce pattern."""
        result = detector.detect_bounce(bounce_pattern_ohlcv)
        assert result is True

    def test_detect_bounce_false(
        self, detector: PatternDetector, no_bounce_pattern_ohlcv: list[OHLCV]
    ) -> None:
        """Test bounce detection when no bounce pattern exists."""
        result = detector.detect_bounce(no_bounce_pattern_ohlcv)
        assert result is False

    def test_detect_bounce_detailed(
        self, detector: PatternDetector, bounce_pattern_ohlcv: list[OHLCV]
    ) -> None:
        """Test detailed bounce detection returns complete result."""
        result = detector.detect_bounce_detailed(bounce_pattern_ohlcv)

        assert isinstance(result, BouncePatternResult)
        assert result.is_bounce is True
        assert result.previous_high is not None
        assert result.previous_low is not None
        assert result.current_high is not None
        assert result.current_low is not None
        assert result.lookback_used > 0

    def test_detect_bounce_with_custom_lookback(
        self, detector: PatternDetector, base_time: datetime
    ) -> None:
        """Test bounce detection with custom lookback period."""
        data = [
            OHLCV(
                timestamp=base_time + timedelta(days=i),
                open=100.0,
                high=100.0 + i,
                low=99.0,
                close=100.5,
                volume=1000000,
            )
            for i in range(10)
        ]

        # Current bar higher than all in lookback
        data.append(
            OHLCV(
                timestamp=base_time + timedelta(days=10),
                open=100.0,
                high=115.0,  # Higher than lookback period
                low=100.0,  # Higher low
                close=105.0,
                volume=1000000,
            )
        )

        result = detector.detect_bounce(data, lookback=3)
        assert result is True

    def test_detect_bounce_adjusts_lookback_for_short_data(
        self, detector: PatternDetector, base_time: datetime
    ) -> None:
        """Test that lookback is adjusted when data is shorter than requested."""
        data = [
            OHLCV(
                timestamp=base_time + timedelta(days=i),
                open=100.0,
                high=100.0 + i * 0.1,
                low=99.0,
                close=100.5,
                volume=1000000,
            )
            for i in range(3)  # Only 3 bars
        ]

        # Request lookback of 10, but only 2 bars available
        result = detector.detect_bounce_detailed(data, lookback=10)
        assert result.lookback_used <= 2

    def test_detect_bounce_with_insufficient_data_raises_error(
        self, detector: PatternDetector, base_time: datetime
    ) -> None:
        """Test that insufficient data (less than 2 bars) raises ValueError."""
        data = [
            OHLCV(
                timestamp=base_time,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000000,
            )
        ]

        with pytest.raises(ValueError, match="at least 2|insufficient"):
            detector.detect_bounce(data)

    def test_confirm_volume_with_spike(
        self, detector: PatternDetector, volume_spike_ohlcv: list[OHLCV]
    ) -> None:
        """Test volume confirmation with volume spike."""
        result = detector.confirm_volume(volume_spike_ohlcv, threshold=1.2)
        assert result is True

    def test_confirm_volume_without_spike(
        self, detector: PatternDetector, normal_volume_ohlcv: list[OHLCV]
    ) -> None:
        """Test volume confirmation without volume spike."""
        result = detector.confirm_volume(normal_volume_ohlcv, threshold=1.2)
        assert result is False

    def test_confirm_volume_with_custom_threshold(
        self, detector: PatternDetector, volume_spike_ohlcv: list[OHLCV]
    ) -> None:
        """Test volume confirmation with custom threshold."""
        # 1.5x volume, but threshold is 2.0x
        result = detector.confirm_volume(volume_spike_ohlcv, threshold=2.0)
        assert result is False

    def test_confirm_volume_with_custom_period(
        self, detector: PatternDetector, base_time: datetime
    ) -> None:
        """Test volume confirmation with custom averaging period."""
        data = []

        # 10 days of low volume
        for i in range(10):
            data.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=500000,
                )
            )

        # 10 days of high volume
        for i in range(10):
            data.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=10 + i),
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=2000000,
                )
            )

        # Current day with spike vs recent 10-day average
        data.append(
            OHLCV(
                timestamp=base_time + timedelta(days=20),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=4000000,  # 2x recent average
            )
        )

        result = detector.confirm_volume(data, threshold=1.5, period=10)
        assert result is True

    def test_confirm_volume_with_empty_list_raises_error(self, detector: PatternDetector) -> None:
        """Test that empty OHLCV list raises ValueError."""
        with pytest.raises(ValueError, match="empty|Cannot confirm"):
            detector.confirm_volume([])

    def test_detect_bounce_with_volume(
        self, detector: PatternDetector, bounce_pattern_ohlcv: list[OHLCV]
    ) -> None:
        """Test combined bounce and volume detection."""
        # Bounce pattern exists but no volume spike
        result = detector.detect_bounce_with_volume(bounce_pattern_ohlcv)
        assert result is False  # No volume spike

    def test_detect_bounce_with_volume_both_true(
        self, detector: PatternDetector, base_time: datetime
    ) -> None:
        """Test combined detection when both conditions are met."""
        data = []

        # Previous period
        for i in range(5):
            data.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=100.0,
                    high=102.0,
                    low=98.0,
                    close=100.5,
                    volume=1000000,
                )
            )

        # Current bar with both bounce and volume spike
        data.append(
            OHLCV(
                timestamp=base_time + timedelta(days=5),
                open=100.0,
                high=105.0,  # Higher high
                low=99.0,  # Higher low
                close=103.0,
                volume=2000000,  # 2x volume
            )
        )

        result = detector.detect_bounce_with_volume(data, volume_threshold=1.2)
        assert result is True

    def test_default_values(self, detector: PatternDetector) -> None:
        """Test that default values are set correctly."""
        assert detector._default_lookback == 5
        assert detector._default_volume_threshold == 1.2

    def test_custom_defaults(self, base_time: datetime) -> None:
        """Test PatternDetector with custom default values."""
        detector = PatternDetector(default_lookback=10, default_volume_threshold=1.5)

        data = [
            OHLCV(
                timestamp=base_time + timedelta(days=i),
                open=100.0,
                high=100.0 + i,
                low=99.0,
                close=100.5,
                volume=1000000,
            )
            for i in range(12)
        ]

        # Add current bar
        data.append(
            OHLCV(
                timestamp=base_time + timedelta(days=12),
                open=100.0,
                high=120.0,
                low=100.0,
                close=105.0,
                volume=2000000,
            )
        )

        # Should use default lookback of 10
        result = detector.detect_bounce(data)
        assert result is True

    def test_bounce_result_attributes(
        self, detector: PatternDetector, bounce_pattern_ohlcv: list[OHLCV]
    ) -> None:
        """Test that BouncePatternResult has all expected attributes."""
        result = detector.detect_bounce_detailed(bounce_pattern_ohlcv)

        # Verify current high > previous high
        assert result.current_high > result.previous_high

        # Verify current low > previous low
        assert result.current_low > result.previous_low

    def test_equal_highs_and_lows_not_bounce(
        self, detector: PatternDetector, base_time: datetime
    ) -> None:
        """Test that equal highs/lows don't trigger bounce (need strictly higher)."""
        data = []

        # Previous period
        for i in range(5):
            data.append(
                OHLCV(
                    timestamp=base_time + timedelta(days=i),
                    open=100.0,
                    high=102.0,
                    low=98.0,
                    close=100.5,
                    volume=1000000,
                )
            )

        # Current bar with equal high and low (not a bounce)
        data.append(
            OHLCV(
                timestamp=base_time + timedelta(days=5),
                open=100.0,
                high=102.0,  # Equal to previous high
                low=98.0,  # Equal to previous low
                close=100.5,
                volume=1000000,
            )
        )

        result = detector.detect_bounce(data)
        assert result is False
