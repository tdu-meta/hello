"""
Unit tests for StrategyParser.

Tests for loading and validating strategy YAML files.
"""

from pathlib import Path

import pytest
from orion.strategies.models import Strategy
from orion.strategies.parser import StrategyParseError, StrategyParser


class TestStrategyParser:
    """Test suite for StrategyParser."""

    @pytest.fixture
    def parser(self) -> StrategyParser:
        """Create a StrategyParser instance for testing."""
        return StrategyParser()

    @pytest.fixture
    def valid_yaml_content(self) -> str:
        """Create valid YAML content for testing."""
        return """
name: "Test Strategy"
version: "1.0.0"
description: "A test strategy for unit testing"

stock_criteria:
  min_revenue: 1000000000
  min_market_cap: 500000000
  min_price: 10.0

entry_conditions:
  - type: trend
    rule: sma_20 > sma_60
    description: "Bullish trend"
    weight: 1.0
    parameters: {}

  - type: oversold
    rule: rsi < 30
    description: "Oversold condition"
    weight: 1.0
    parameters:
      threshold: 30

option_screening:
  min_premium_yield: 0.02
  target_dte: 30
  min_dte: 7
  max_dte: 60
  tolerance: 0.05
  min_volume: 100
  min_open_interest: 500

tags:
  - test
  - income
"""

    @pytest.fixture
    def invalid_yaml_content(self) -> str:
        """Create invalid YAML content for testing."""
        return """
name: "Invalid Strategy"
version: "1.0.0"
description: "Missing required fields"

# No entry_conditions - this should fail
"""

    def test_parse_string_valid(self, parser: StrategyParser, valid_yaml_content: str) -> None:
        """Test parsing valid YAML from string."""
        strategy = parser.parse_string(valid_yaml_content)
        assert isinstance(strategy, Strategy)
        assert strategy.name == "Test Strategy"
        assert strategy.version == "1.0.0"
        assert strategy.description == "A test strategy for unit testing"
        assert len(strategy.entry_conditions) == 2
        assert strategy.tags == ["test", "income"]

    def test_parse_string_missing_name(self, parser: StrategyParser) -> None:
        """Test that missing name raises StrategyParseError."""
        yaml_content = """
version: "1.0.0"
description: "No name"
entry_conditions:
  - type: trend
    rule: sma_20 > sma_60
option_screening:
  min_premium_yield: 0.02
"""
        with pytest.raises(StrategyParseError, match="name"):
            parser.parse_string(yaml_content)

    def test_parse_string_missing_conditions(self, parser: StrategyParser) -> None:
        """Test that missing entry_conditions raises StrategyParseError."""
        yaml_content = """
name: "Test"
version: "1.0.0"
description: "No conditions"
option_screening:
  min_premium_yield: 0.02
"""
        with pytest.raises(StrategyParseError, match="entry_conditions"):
            parser.parse_string(yaml_content)

    def test_parse_string_invalid_yaml(self, parser: StrategyParser) -> None:
        """Test that invalid YAML raises StrategyParseError."""
        yaml_content = """
name: "Test"
version: "1.0.0"
description: "Invalid YAML"
  this is: [broken
"""
        with pytest.raises(StrategyParseError, match="YAML"):
            parser.parse_string(yaml_content)

    def test_parse_string_empty_conditions(self, parser: StrategyParser) -> None:
        """Test that empty entry_conditions list raises error."""
        yaml_content = """
name: "Test"
version: "1.0.0"
description: "Empty conditions"
entry_conditions: []
option_screening:
  min_premium_yield: 0.02
"""
        with pytest.raises(StrategyParseError, match="at least one"):
            parser.parse_string(yaml_content)

    def test_parse_file_not_found(self, parser: StrategyParser) -> None:
        """Test that non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/strategy.yaml")

    def test_parse_condition_without_type(self, parser: StrategyParser) -> None:
        """Test that condition without type raises StrategyParseError."""
        yaml_content = """
name: "Test"
version: "1.0.0"
description: "Bad condition"
entry_conditions:
  - rule: sma_20 > sma_60
option_screening:
  min_premium_yield: 0.02
"""
        with pytest.raises(StrategyParseError, match="type"):
            parser.parse_string(yaml_content)

    def test_parse_condition_without_rule(self, parser: StrategyParser) -> None:
        """Test that condition without rule raises StrategyParseError."""
        yaml_content = """
name: "Test"
version: "1.0.0"
description: "Bad condition"
entry_conditions:
  - type: trend
option_screening:
  min_premium_yield: 0.02
"""
        with pytest.raises(StrategyParseError, match="rule"):
            parser.parse_string(yaml_content)

    def test_parse_with_strategies_dir(self, tmp_path: Path) -> None:
        """Test parsing with strategies_dir set for relative paths."""
        # Create a strategy file
        strategy_file = tmp_path / "test_strategy.yaml"
        strategy_file.write_text(
            """
name: "Test Strategy"
version: "1.0.0"
description: "Test"
entry_conditions:
  - type: trend
    rule: sma_20 > sma_60
option_screening:
  min_premium_yield: 0.02
"""
        )

        parser = StrategyParser(strategies_dir=tmp_path)
        strategy = parser.parse_file("test_strategy.yaml")
        assert strategy.name == "Test Strategy"

    def test_parse_real_ofi_strategy(self, parser: StrategyParser) -> None:
        """Test parsing the actual OFI strategy YAML file."""
        ofi_path = Path(__file__).parent.parent.parent.parent / "strategies" / "ofi.yaml"
        if ofi_path.exists():
            strategy = parser.parse_file(ofi_path)
            assert "OFI" in strategy.name
            assert len(strategy.entry_conditions) == 3
            # Check condition types
            condition_types = {c.type for c in strategy.entry_conditions}
            assert "trend" in condition_types
            assert "oversold" in condition_types
            assert "bounce" in condition_types

    def test_parse_stock_criteria_defaults(self, parser: StrategyParser) -> None:
        """Test parsing stock criteria with default values."""
        yaml_content = """
name: "Test"
version: "1.0.0"
description: "Test"
stock_criteria: {}
entry_conditions:
  - type: trend
    rule: sma_20 > sma_60
option_screening:
  min_premium_yield: 0.02
"""
        strategy = parser.parse_string(yaml_content)
        assert strategy.stock_criteria.min_revenue is None
        assert strategy.stock_criteria.min_market_cap is None
        assert strategy.stock_criteria.exchanges == []

    def test_parse_option_screening_defaults(self, parser: StrategyParser) -> None:
        """Test parsing option screening with default values."""
        yaml_content = """
name: "Test"
version: "1.0.0"
description: "Test"
entry_conditions:
  - type: trend
    rule: sma_20 > sma_60
option_screening: {}
"""
        strategy = parser.parse_string(yaml_content)
        assert strategy.option_screening.min_premium_yield == 0.02
        assert strategy.option_screening.target_dte == 30
        assert strategy.option_screening.min_dte == 7
        assert strategy.option_screening.max_dte == 60
