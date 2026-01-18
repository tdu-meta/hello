"""Strategy parser for loading strategies from YAML files.

This module provides the StrategyParser class for loading and validating
trading strategy definitions from YAML files.
"""

from pathlib import Path
from typing import Any

import yaml
from yaml import YAMLError

from orion.strategies.models import (
    Condition,
    OptionScreening,
    StockCriteria,
    Strategy,
)
from orion.utils.logging import get_logger

logger = get_logger(__name__, component="StrategyParser")


class StrategyParseError(Exception):
    """Exception raised when strategy parsing fails."""

    def __init__(
        self, message: str, file_path: str | None = None, details: dict[str, Any] | None = None
    ):
        """Initialize the parse error.

        Args:
            message: Error message
            file_path: Optional path to the file being parsed
            details: Optional additional details about the error
        """
        self.file_path = file_path
        self.details = details or {}
        full_message = f"Strategy parse error: {message}"
        if file_path:
            full_message += f" (file: {file_path})"
        super().__init__(full_message)


class StrategyParser:
    """Parser for trading strategy YAML files.

    The parser reads YAML files containing strategy definitions and converts
    them into Strategy objects with proper validation.

    Example:
        >>> parser = StrategyParser()
        >>> strategy = parser.parse_file(Path("strategies/ofi.yaml"))
        >>> print(strategy.name)
        'OFI - Option for Income'
    """

    def __init__(self, strategies_dir: str | Path | None = None) -> None:
        """Initialize the StrategyParser.

        Args:
            strategies_dir: Optional base directory for strategy files.
                           If provided, relative paths will be resolved from here.
        """
        self._strategies_dir = Path(strategies_dir) if strategies_dir else None
        self._logger = logger

    def parse_file(self, file_path: str | Path) -> Strategy:
        """Parse a strategy from a YAML file.

        Args:
            file_path: Path to the YAML file. Can be absolute or relative
                      to strategies_dir if one was provided.

        Returns:
            Strategy object with the parsed data

        Raises:
            StrategyParseError: If the file cannot be parsed or validation fails
            FileNotFoundError: If the file does not exist
        """
        path = self._resolve_path(file_path)

        if not path.exists():
            self._logger.error("strategy_file_not_found", path=str(path))
            raise FileNotFoundError(f"Strategy file not found: {path}")

        self._logger.info("parsing_strategy", path=str(path))

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except YAMLError as e:
            self._logger.error("yaml_parse_error", path=str(path), error=str(e))
            raise StrategyParseError(f"Invalid YAML: {e}", file_path=str(path)) from e

        if not data:
            raise StrategyParseError("Empty YAML file", file_path=str(path))

        return self._parse_data(data, file_path=str(path))

    def parse_string(self, yaml_content: str) -> Strategy:
        """Parse a strategy from a YAML string.

        Args:
            yaml_content: YAML content as a string

        Returns:
            Strategy object with the parsed data

        Raises:
            StrategyParseError: If the YAML cannot be parsed or validation fails
        """
        try:
            data = yaml.safe_load(yaml_content)
        except YAMLError as e:
            self._logger.error("yaml_parse_error", error=str(e))
            raise StrategyParseError(f"Invalid YAML: {e}") from e

        if not data:
            raise StrategyParseError("Empty YAML content")

        return self._parse_data(data)

    def _resolve_path(self, file_path: str | Path) -> Path:
        """Resolve a file path relative to strategies_dir if set."""
        path = Path(file_path)

        if not path.is_absolute() and self._strategies_dir:
            path = self._strategies_dir / path

        return path

    def _parse_data(self, data: dict[str, Any], file_path: str | None = None) -> Strategy:
        """Parse strategy data from a dictionary.

        Args:
            data: Dictionary containing strategy data
            file_path: Optional file path for error reporting

        Returns:
            Strategy object

        Raises:
            StrategyParseError: If required fields are missing or invalid
        """
        # Validate required top-level fields
        required_fields = ["name", "version", "description", "entry_conditions"]
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            raise StrategyParseError(
                f"Missing required fields: {', '.join(missing_fields)}",
                file_path=file_path,
                details={"missing_fields": missing_fields},
            )

        # Parse stock criteria
        stock_criteria = self._parse_stock_criteria(
            data.get("stock_criteria", {}), file_path=file_path
        )

        # Parse entry conditions
        entry_conditions = self._parse_entry_conditions(
            data.get("entry_conditions", []), file_path=file_path
        )

        # Parse option screening
        option_screening = self._parse_option_screening(
            data.get("option_screening", {}), file_path=file_path
        )

        # Create strategy
        try:
            strategy = Strategy(
                name=data["name"],
                version=data["version"],
                description=data["description"],
                stock_criteria=stock_criteria,
                entry_conditions=entry_conditions,
                option_screening=option_screening,
                tags=data.get("tags", []),
            )
        except (ValueError, TypeError) as e:
            raise StrategyParseError(
                f"Failed to create Strategy object: {e}",
                file_path=file_path,
            ) from e

        self._logger.info(
            "strategy_parsed",
            name=strategy.name,
            version=strategy.version,
            conditions_count=len(entry_conditions),
        )

        return strategy

    def _parse_stock_criteria(self, data: dict[str, Any], file_path: str | None) -> StockCriteria:
        """Parse stock criteria from data dictionary."""
        return StockCriteria(
            min_revenue=data.get("min_revenue"),
            min_market_cap=data.get("min_market_cap"),
            max_market_cap=data.get("max_market_cap"),
            min_price=data.get("min_price"),
            max_price=data.get("max_price"),
            exchanges=data.get("exchanges", []),
            sectors=data.get("sectors", []),
            exclude_sectors=data.get("exclude_sectors", []),
        )

    def _parse_entry_conditions(
        self, data: list[dict[str, Any]], file_path: str | None
    ) -> list[Condition]:
        """Parse entry conditions from data list."""
        conditions = []

        for i, cond_data in enumerate(data):
            if not isinstance(cond_data, dict):
                raise StrategyParseError(
                    f"Entry condition {i} must be a dictionary",
                    file_path=file_path,
                    details={"condition_index": i, "condition_type": type(cond_data).__name__},
                )

            if "type" not in cond_data:
                raise StrategyParseError(
                    f"Entry condition {i} missing required field 'type'",
                    file_path=file_path,
                    details={"condition_index": i},
                )

            if "rule" not in cond_data:
                raise StrategyParseError(
                    f"Entry condition {i} missing required field 'rule'",
                    file_path=file_path,
                    details={"condition_index": i, "condition_type": cond_data.get("type")},
                )

            condition = Condition(
                type=cond_data["type"],
                rule=cond_data["rule"],
                parameters=cond_data.get("parameters", {}),
                description=cond_data.get("description", ""),
                weight=cond_data.get("weight", 1.0),
            )
            conditions.append(condition)

        if not conditions:
            raise StrategyParseError(
                "Strategy must have at least one entry condition",
                file_path=file_path,
            )

        return conditions

    def _parse_option_screening(
        self, data: dict[str, Any], file_path: str | None
    ) -> OptionScreening:
        """Parse option screening parameters from data dictionary."""
        return OptionScreening(
            min_premium_yield=data.get("min_premium_yield", 0.02),
            target_dte=data.get("target_dte", 30),
            min_dte=data.get("min_dte", 7),
            max_dte=data.get("max_dte", 60),
            tolerance=data.get("tolerance", 0.05),
            min_volume=data.get("min_volume", 100),
            min_open_interest=data.get("min_open_interest", 500),
        )

    def load_all_from_directory(self, directory: str | Path) -> dict[str, Strategy]:
        """Load all strategy YAML files from a directory.

        Args:
            directory: Directory containing YAML files

        Returns:
            Dictionary mapping strategy names to Strategy objects

        Raises:
            StrategyParseError: If any file fails to parse
        """
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise StrategyParseError(f"Not a directory: {directory}")

        strategies = {}

        for yaml_file in dir_path.glob("*.yaml"):
            try:
                strategy = self.parse_file(yaml_file)
                strategies[strategy.name] = strategy
            except StrategyParseError as e:
                self._logger.warning("failed_to_parse_strategy", file=str(yaml_file), error=str(e))
                # Continue loading other strategies

        self._logger.info(
            "loaded_strategies_from_directory",
            directory=str(dir_path),
            count=len(strategies),
        )

        return strategies
