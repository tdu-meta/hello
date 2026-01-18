"""Rule evaluator for matching stocks against strategy criteria.

This module provides the RuleEvaluator class for determining whether a stock
matches all entry conditions defined in a trading strategy.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from orion.analysis.indicators import IndicatorCalculator
from orion.analysis.patterns import PatternDetector
from orion.data.models import OHLCV, Quote, TechnicalIndicators
from orion.strategies.models import Condition, EvaluationResult, Strategy
from orion.utils.logging import get_logger

logger = get_logger(__name__, component="RuleEvaluator")


class RuleEvaluator:
    """Evaluate stocks against trading strategy entry conditions.

    The evaluator checks whether a stock meets all conditions defined in a
    strategy, tracking which conditions were met and calculating an overall
    signal strength based on condition weights.

    Example:
        >>> evaluator = RuleEvaluator(ofi_strategy)
        >>> result = await evaluator.evaluate("AAPL", quote, historical, indicators)
        >>> print(result.matches, result.signal_strength)
    """

    def __init__(self, strategy: Strategy) -> None:
        """Initialize the RuleEvaluator.

        Args:
            strategy: The strategy to evaluate against
        """
        self.strategy = strategy
        self.indicator_calc = IndicatorCalculator()
        self.pattern_detector = PatternDetector()
        self._logger = logger

    async def evaluate(
        self,
        symbol: str,
        quote: Quote,
        historical: list[OHLCV],
        indicators: TechnicalIndicators,
    ) -> EvaluationResult:
        """Evaluate if a symbol matches all strategy entry conditions.

        Args:
            symbol: Stock symbol to evaluate
            quote: Current quote data
            historical: Historical OHLCV data for pattern detection
            indicators: Pre-calculated technical indicators

        Returns:
            EvaluationResult with match status, conditions met/missed, and signal strength
        """
        timestamp = datetime.now()

        conditions_met: list[str] = []
        conditions_missed: list[str] = []
        total_weight = 0.0
        score = 0.0
        details: dict[str, Any] = {}

        for condition in self.strategy.entry_conditions:
            weight = condition.weight
            total_weight += weight

            try:
                condition_result = self._evaluate_condition(
                    condition, symbol, quote, historical, indicators
                )

                if condition_result.matches:
                    conditions_met.append(condition.type)
                    score += weight
                    details[condition.type] = {
                        "status": "met",
                        "value": condition_result.value,
                        "rule": condition.rule,
                    }
                else:
                    conditions_missed.append(condition.type)
                    details[condition.type] = {
                        "status": "missed",
                        "value": condition_result.value,
                        "rule": condition.rule,
                        "reason": condition_result.reason,
                    }
            except Exception as e:
                self._logger.error(
                    "condition_evaluation_error",
                    symbol=symbol,
                    condition_type=condition.type,
                    error=str(e),
                )
                conditions_missed.append(condition.type)
                details[condition.type] = {
                    "status": "error",
                    "error": str(e),
                }

        # All conditions must be met for a match
        matches = len(conditions_met) == len(self.strategy.entry_conditions)

        # Calculate signal strength
        signal_strength = score / total_weight if total_weight > 0 else 0.0

        self._logger.info(
            "evaluation_complete",
            symbol=symbol,
            strategy=self.strategy.name,
            matches=matches,
            conditions_met=len(conditions_met),
            total_conditions=len(self.strategy.entry_conditions),
            signal_strength=signal_strength,
        )

        return EvaluationResult(
            symbol=symbol,
            strategy_name=self.strategy.name,
            timestamp=timestamp,
            matches=matches,
            conditions_met=conditions_met,
            conditions_missed=conditions_missed,
            signal_strength=signal_strength,
            details=details,
        )

    def _evaluate_condition(
        self,
        condition: Condition,
        symbol: str,
        quote: Quote,
        historical: list[OHLCV],
        indicators: TechnicalIndicators,
    ) -> "ConditionResult":
        """Evaluate a single condition.

        Args:
            condition: The condition to evaluate
            symbol: Stock symbol
            quote: Current quote data
            historical: Historical OHLCV data
            indicators: Technical indicators

        Returns:
            ConditionResult with match status, value, and optional reason
        """
        # Trend condition: SMA_20 > SMA_60 (bullish trend)
        if condition.type == "trend":
            return self._check_trend(condition, indicators)

        # Oversold condition: RSI < 30 (or within lookback period)
        elif condition.type == "oversold":
            return self._check_oversold(condition, indicators, historical)

        # Bounce condition: Higher high + higher low pattern
        elif condition.type == "bounce":
            return self._check_bounce(condition, historical)

        # Price condition: Price-based checks
        elif condition.type == "price":
            return self._check_price(condition, quote)

        # Volume condition: Volume-based checks
        elif condition.type == "volume":
            return self._check_volume(condition, quote, historical)

        else:
            self._logger.warning("unknown_condition_type", condition_type=condition.type)
            return ConditionResult(
                matches=False,
                value=None,
                reason=f"Unknown condition type: {condition.type}",
            )

    def _check_trend(
        self, condition: Condition, indicators: TechnicalIndicators
    ) -> "ConditionResult":
        """Check trend condition (SMA_20 > SMA_60 for bullish).

        Args:
            condition: The trend condition to check
            indicators: Technical indicators containing SMA values

        Returns:
            ConditionResult with match status
        """
        if condition.rule == "sma_20 > sma_60":
            sma_20 = indicators.sma_20 or 0
            sma_60 = indicators.sma_60 or 0
            matches = sma_20 > sma_60

            return ConditionResult(
                matches=matches,
                value={"sma_20": sma_20, "sma_60": sma_60},
                reason=f"SMA-20 ({sma_20:.2f}) not > SMA-60 ({sma_60:.2f})"
                if not matches
                else None,
            )

        # Check for bullish trend using helper method
        elif condition.rule == "is_bullish":
            matches = indicators.is_bullish_trend()
            return ConditionResult(
                matches=matches,
                value={"is_bullish": matches},
                reason="Not showing bullish trend" if not matches else None,
            )

        return ConditionResult(
            matches=False,
            value=None,
            reason=f"Unknown trend rule: {condition.rule}",
        )

    def _check_oversold(
        self,
        condition: Condition,
        indicators: TechnicalIndicators,
        historical: list[OHLCV],
    ) -> "ConditionResult":
        """Check oversold condition (RSI < 30).

        Can check either current RSI or if RSI was below threshold within
        a lookback period.

        Args:
            condition: The oversold condition to check
            indicators: Technical indicators containing RSI
            historical: Historical data for lookback checks

        Returns:
            ConditionResult with match status
        """
        lookback_days = condition.parameters.get("lookback_days", 0)
        threshold = condition.parameters.get("threshold", 30.0)

        if condition.rule == "rsi < threshold":
            # Check if current RSI is below threshold
            if indicators.rsi_14 is not None:
                matches = indicators.rsi_14 < threshold
                return ConditionResult(
                    matches=matches,
                    value={"rsi": indicators.rsi_14, "threshold": threshold},
                    reason=f"RSI ({indicators.rsi_14:.2f}) not < {threshold}"
                    if not matches
                    else None,
                )
            return ConditionResult(
                matches=False,
                value={"rsi": None},
                reason="RSI not available",
            )

        # Check if RSI was below threshold within lookback period
        elif condition.rule == "rsi_was_below":
            if not historical or len(historical) < 15:
                return ConditionResult(
                    matches=False,
                    value={"data_points": len(historical) if historical else 0},
                    reason="Insufficient historical data for RSI lookback",
                )

            lookback = (
                min(lookback_days, len(historical) - 15)
                if lookback_days > 0
                else len(historical) - 15
            )

            for i in range(len(historical) - 15, max(len(historical) - 15 - lookback - 1, 0), -1):
                try:
                    subset = historical[: i + 1]
                    if len(subset) >= 15:
                        temp_indicators = self.indicator_calc.calculate(subset, "lookback")
                        if (
                            temp_indicators.rsi_14 is not None
                            and temp_indicators.rsi_14 < threshold
                        ):
                            return ConditionResult(
                                matches=True,
                                value={"rsi_found": temp_indicators.rsi_14, "threshold": threshold},
                            )
                except Exception:
                    continue

            return ConditionResult(
                matches=False,
                value={"threshold": threshold, "lookback_days": lookback},
                reason=f"RSI was never below {threshold} in lookback period",
            )

        # Check using helper method
        elif condition.rule == "is_oversold":
            matches = indicators.is_oversold(threshold)
            return ConditionResult(
                matches=matches,
                value={"rsi": indicators.rsi_14, "threshold": threshold},
                reason=f"RSI ({indicators.rsi_14}) not oversold (< {threshold})"
                if not matches
                else None,
            )

        return ConditionResult(
            matches=False,
            value=None,
            reason=f"Unknown oversold rule: {condition.rule}",
        )

    def _check_bounce(self, condition: Condition, historical: list[OHLCV]) -> "ConditionResult":
        """Check bounce pattern condition (higher high + higher low).

        Args:
            condition: The bounce condition to check
            historical: Historical OHLCV data for pattern detection

        Returns:
            ConditionResult with match status
        """
        if not historical or len(historical) < 2:
            return ConditionResult(
                matches=False,
                value={"data_points": len(historical) if historical else 0},
                reason="Insufficient data for bounce detection",
            )

        lookback = condition.parameters.get("lookback", 5)
        volume_confirmation = condition.parameters.get("volume_confirmation", False)

        if condition.rule == "higher_high_higher_low":
            if volume_confirmation:
                matches = self.pattern_detector.detect_bounce_with_volume(
                    historical,
                    lookback=lookback,
                    volume_threshold=condition.parameters.get("volume_threshold", 1.2),
                )
                reason = (
                    "Bounce pattern with volume confirmation not detected" if not matches else None
                )
            else:
                matches = self.pattern_detector.detect_bounce(historical, lookback=lookback)
                reason = "Bounce pattern not detected" if not matches else None

            return ConditionResult(
                matches=matches,
                value={"lookback": lookback, "volume_confirmation": volume_confirmation},
                reason=reason,
            )

        return ConditionResult(
            matches=False,
            value=None,
            reason=f"Unknown bounce rule: {condition.rule}",
        )

    def _check_price(self, condition: Condition, quote: Quote) -> "ConditionResult":
        """Check price-based condition.

        Args:
            condition: The price condition to check
            quote: Current quote data

        Returns:
            ConditionResult with match status
        """
        price = float(quote.price)

        if condition.rule == "min_price":
            min_price = condition.parameters.get("value", 0)
            matches = price >= min_price
            return ConditionResult(
                matches=matches,
                value={"price": price, "min_price": min_price},
                reason=f"Price ({price:.2f}) below minimum ({min_price})" if not matches else None,
            )

        elif condition.rule == "max_price":
            max_price = condition.parameters.get("value", float("inf"))
            matches = price <= max_price
            return ConditionResult(
                matches=matches,
                value={"price": price, "max_price": max_price},
                reason=f"Price ({price:.2f}) above maximum ({max_price})" if not matches else None,
            )

        return ConditionResult(
            matches=False,
            value=None,
            reason=f"Unknown price rule: {condition.rule}",
        )

    def _check_volume(
        self,
        condition: Condition,
        quote: Quote,
        historical: list[OHLCV],
    ) -> "ConditionResult":
        """Check volume-based condition.

        Args:
            condition: The volume condition to check
            quote: Current quote data
            historical: Historical OHLCV data

        Returns:
            ConditionResult with match status
        """
        if condition.rule == "min_volume":
            min_volume = condition.parameters.get("value", 0)
            matches = quote.volume >= min_volume
            return ConditionResult(
                matches=matches,
                value={"volume": quote.volume, "min_volume": min_volume},
                reason=f"Volume ({quote.volume}) below minimum ({min_volume})"
                if not matches
                else None,
            )

        elif condition.rule == "volume_spike":
            threshold = condition.parameters.get("threshold", 1.2)
            try:
                matches = self.pattern_detector.confirm_volume(historical, threshold=threshold)
                return ConditionResult(
                    matches=matches,
                    value={"threshold": threshold},
                    reason=f"Volume spike not detected (threshold: {threshold})"
                    if not matches
                    else None,
                )
            except Exception as e:
                return ConditionResult(
                    matches=False,
                    value=None,
                    reason=f"Volume check failed: {e}",
                )

        return ConditionResult(
            matches=False,
            value=None,
            reason=f"Unknown volume rule: {condition.rule}",
        )


@dataclass
class ConditionResult:
    """Result of evaluating a single condition.

    Attributes:
        matches: Whether the condition was met
        value: The value(s) checked (for logging/debugging)
        reason: Human-readable reason if condition was not met
    """

    matches: bool
    value: Any
    reason: str | None = None
