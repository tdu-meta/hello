"""
Chart pattern detection for OFI trading signals.

This module provides the PatternDetector class for identifying chart patterns
such as Higher High + Higher Low (bounce) and volume confirmation.
"""

from dataclasses import dataclass

from orion.data.models import OHLCV
from orion.utils.logging import get_logger

logger = get_logger(__name__, component="PatternDetector")


@dataclass
class BouncePatternResult:
    """Result of bounce pattern detection."""

    is_bounce: bool
    """Whether a higher high + higher low pattern was detected."""

    previous_high: float | None = None
    """The previous high in the lookback period."""

    previous_low: float | None = None
    """The previous low in the lookback period."""

    current_high: float | None = None
    """The current high."""

    current_low: float | None = None
    """The current low."""

    lookback_used: int = 0
    """The lookback period used for detection."""


class PatternDetector:
    """
    Detect chart patterns for OFI entry signals.

    This detector identifies patterns like bounce formations (higher high +
    higher low) and volume confirmation, which are key entry signals in the
    Option for Income strategy.

    Example:
        >>> detector = PatternDetector()
        >>> is_bounce = detector.detect_bounce(ohlcv_list, lookback=5)
        >>> has_volume = detector.confirm_volume(ohlcv_list, threshold=1.2)
    """

    def __init__(
        self,
        default_lookback: int = 5,
        default_volume_threshold: float = 1.2,
    ) -> None:
        """
        Initialize the PatternDetector.

        Args:
            default_lookback: Default lookback period for pattern detection
            default_volume_threshold: Default volume multiplier threshold
        """
        self._default_lookback = default_lookback
        self._default_volume_threshold = default_volume_threshold
        self._logger = logger

    def detect_bounce(
        self,
        ohlcv_list: list[OHLCV],
        lookback: int | None = None,
    ) -> bool:
        """
        Detect Higher High + Higher Low bounce pattern.

        A bounce pattern is identified when:
        1. The current high exceeds a previous high within lookback period
        2. The current low exceeds that previous low
        3. This indicates bullish momentum with higher support

        Args:
            ohlcv_list: List of OHLCV objects, sorted chronologically
            lookback: Number of bars to look back for previous high/low
                     (defaults to instance default_lookback)

        Returns:
            True if bounce pattern is detected, False otherwise

        Raises:
            ValueError: If ohlcv_list has fewer than 2 elements

        Example:
            >>> detector = PatternDetector()
            >>> is_bouncing = detector.detect_bounce(ohlcv_list, lookback=5)
        """
        result = self.detect_bounce_detailed(ohlcv_list, lookback)
        return result.is_bounce

    def detect_bounce_detailed(
        self,
        ohlcv_list: list[OHLCV],
        lookback: int | None = None,
    ) -> BouncePatternResult:
        """
        Detect bounce pattern with detailed results.

        This is an extended version of detect_bounce that returns additional
        information about the detected pattern.

        Args:
            ohlcv_list: List of OHLCV objects, sorted chronologically
            lookback: Number of bars to look back for previous high/low

        Returns:
            BouncePatternResult with detection status and price details
        """
        lookback = lookback if lookback is not None else self._default_lookback

        if len(ohlcv_list) < 2:
            self._logger.warning("insufficient_data_for_bounce_detection", count=len(ohlcv_list))
            raise ValueError("Need at least 2 OHLCV bars to detect bounce pattern")

        if len(ohlcv_list) < lookback + 1:
            self._logger.debug(
                "adjusting_lookback",
                requested=lookback,
                adjusted=len(ohlcv_list) - 1,
            )
            lookback = len(ohlcv_list) - 1

        current = ohlcv_list[-1]
        lookback_bars = ohlcv_list[-lookback - 1 : -1]

        # Find previous high and low in lookback period
        previous_high = max(float(bar.high) for bar in lookback_bars)
        previous_low = min(float(bar.low) for bar in lookback_bars)

        current_high = float(current.high)
        current_low = float(current.low)

        # Check for higher high AND higher low
        is_bounce = current_high > previous_high and current_low > previous_low

        self._logger.debug(
            "bounce_detection_complete",
            is_bounce=is_bounce,
            previous_high=previous_high,
            previous_low=previous_low,
            current_high=current_high,
            current_low=current_low,
            lookback=lookback,
        )

        return BouncePatternResult(
            is_bounce=is_bounce,
            previous_high=previous_high,
            previous_low=previous_low,
            current_high=current_high,
            current_low=current_low,
            lookback_used=lookback,
        )

    def confirm_volume(
        self,
        ohlcv_list: list[OHLCV],
        threshold: float | None = None,
        period: int = 20,
    ) -> bool:
        """
        Detect volume spike as confirmation of trading activity.

        Volume confirmation is identified when current volume exceeds the
        average volume by the specified threshold multiplier.

        Args:
            ohlcv_list: List of OHLCV objects, sorted chronologically
            threshold: Volume multiplier threshold (e.g., 1.2 = 20% above average)
                      (defaults to instance default_volume_threshold)
            period: Period for calculating average volume

        Returns:
            True if volume spike is detected (current > threshold * avg), False otherwise

        Raises:
            ValueError: If ohlcv_list is empty

        Example:
            >>> detector = PatternDetector()
            >>> has_volume = detector.confirm_volume(ohlcv_list, threshold=1.2)
        """
        threshold = threshold if threshold is not None else self._default_volume_threshold

        if not ohlcv_list:
            self._logger.warning("empty_ohlcv_list_for_volume_confirmation")
            raise ValueError("Cannot confirm volume with empty OHLCV list")

        if len(ohlcv_list) < period:
            self._logger.debug(
                "insufficient_data_for_volume_avg",
                available=len(ohlcv_list),
                required=period,
            )
            # Use available data
            period = len(ohlcv_list) - 1

        current_volume = ohlcv_list[-1].volume
        period_bars = (
            ohlcv_list[-period - 1 : -1] if len(ohlcv_list) > period + 1 else ohlcv_list[:-1]
        )

        avg_volume = sum(bar.volume for bar in period_bars) / len(period_bars)

        # Avoid division by zero
        if avg_volume == 0:
            self._logger.warning("zero_average_volume")
            return False

        volume_ratio = current_volume / avg_volume
        is_confirmed = volume_ratio >= threshold

        self._logger.debug(
            "volume_confirmation_complete",
            current_volume=current_volume,
            avg_volume=avg_volume,
            volume_ratio=volume_ratio,
            threshold=threshold,
            is_confirmed=is_confirmed,
        )

        return is_confirmed

    def detect_bounce_with_volume(
        self,
        ohlcv_list: list[OHLCV],
        lookback: int | None = None,
        volume_threshold: float | None = None,
    ) -> bool:
        """
        Detect bounce pattern with volume confirmation.

        This combines both bounce pattern detection and volume confirmation
        for a stronger signal. Both conditions must be true.

        Args:
            ohlcv_list: List of OHLCV objects, sorted chronologically
            lookback: Lookback period for bounce detection
            volume_threshold: Volume multiplier threshold

        Returns:
            True if both bounce pattern and volume confirmation are detected
        """
        has_bounce = self.detect_bounce(ohlcv_list, lookback)
        has_volume = self.confirm_volume(ohlcv_list, volume_threshold)

        result = has_bounce and has_volume

        self._logger.debug(
            "combined_bounce_volume_detection",
            has_bounce=has_bounce,
            has_volume=has_volume,
            combined_signal=result,
        )

        return result
