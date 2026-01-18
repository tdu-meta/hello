"""Strategy engine module for Orion.

This module provides the strategy parsing, evaluation, and option analysis
functionality for identifying trading opportunities based on defined strategies.
"""

from orion.strategies.evaluator import RuleEvaluator
from orion.strategies.models import (
    Condition,
    EvaluationResult,
    OptionRecommendation,
    OptionScreening,
    StockCriteria,
    Strategy,
)
from orion.strategies.option_analyzer import OptionAnalyzer
from orion.strategies.parser import StrategyParseError, StrategyParser

__all__ = [
    # Models
    "Condition",
    "EvaluationResult",
    "OptionRecommendation",
    "OptionScreening",
    "Strategy",
    "StockCriteria",
    # Parser
    "StrategyParser",
    "StrategyParseError",
    # Evaluator
    "RuleEvaluator",
    # Analyzer
    "OptionAnalyzer",
]
