"""AWS Lambda handler for Orion stock screening.

This module provides the Lambda entry point for running scheduled stock screenings
in AWS Lambda. It integrates with EventBridge for automated scheduling and supports
configurable symbols, strategies, and notifications.

Event Schema:
    {
        "strategy": "ofi",              # Strategy name or path
        "symbols": ["AAPL", "MSFT"],    # Symbols to screen
        "notify": true,                 # Send notifications for matches
        "dry_run": false                # Skip saving to database
    }

Environment Variables:
    ALPHA_VANTAGE_API_KEY: Required for Alpha Vantage data provider
    DATA_PROVIDER__provider: Data provider (yahoo_finance or alpha_vantage)
    NOTIFICATIONS__*: SMTP configuration for email alerts
    LOG_LEVEL: Logging level (default: INFO)
    MAX_CONCURRENT: Max concurrent screenings (default: 5)
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src directory to path for Lambda imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orion.config import Config
from orion.core.screener import ScreeningResult, ScreeningStats, StockScreener
from orion.data.provider import DataProvider
from orion.data.providers.alpha_vantage import AlphaVantageProvider
from orion.data.providers.yahoo_finance import YahooFinanceProvider
from orion.notifications.models import NotificationConfig
from orion.notifications.service import NotificationService
from orion.strategies.models import Strategy
from orion.strategies.parser import StrategyParser
from orion.utils.logging import get_logger, setup_logging

# Default strategy path in Lambda deployment
DEFAULT_STRATEGY_PATH = "/opt/strategies/ofi.yaml"
LOCAL_STRATEGY_PATH = "strategies/ofi.yaml"


logger = get_logger(__name__, component="LambdaHandler")


def get_strategy_path(event_strategy: str | None) -> str:
    """Resolve strategy path from event or use default.

    Args:
        event_strategy: Strategy name or path from event

    Returns:
        Absolute path to strategy YAML file
    """
    if not event_strategy:
        # Try Lambda deployment path first, then local
        if Path(DEFAULT_STRATEGY_PATH).exists():
            return DEFAULT_STRATEGY_PATH
        return LOCAL_STRATEGY_PATH

    # If it's a path (contains .yaml), use it directly
    if "." in event_strategy:
        if Path(event_strategy).exists():
            return event_strategy
        if Path(f"/opt/strategies/{event_strategy}").exists():
            return f"/opt/strategies/{event_strategy}"

    # Try Lambda and local paths
    for base in ["/opt/strategies", "strategies"]:
        candidate = f"{base}/{event_strategy}.yaml"
        if Path(candidate).exists():
            return candidate

    # Fall back to default
    return DEFAULT_STRATEGY_PATH


def load_config() -> Config:
    """Load configuration from environment variables.

    Returns:
        Validated Config instance
    """
    try:
        return Config()
    except Exception as e:
        logger.error("config_load_failed", error=str(e), error_type=type(e).__name__)
        # Return minimal config for Lambda
        return Config()


def load_notification_config() -> NotificationConfig | None:
    """Load notification configuration from environment.

    Returns:
        NotificationConfig if valid, None otherwise
    """
    try:
        from orion.notifications.models import NotificationConfig as NotifConfig

        config = NotifConfig()
        # Validate required fields
        if not config.smtp_host or not config.from_address or not config.to_addresses:
            logger.warning("incomplete_notification_config", smtp_host=bool(config.smtp_host))
            return None
        return config
    except Exception as e:
        logger.warning("notification_config_load_failed", error=str(e))
        return None


def get_data_provider(config: Config) -> DataProvider:
    """Get data provider instance based on configuration.

    Args:
        config: Application configuration

    Returns:
        DataProvider instance
    """
    provider_name = config.data_provider.provider.lower()

    if provider_name == "alpha_vantage":
        return AlphaVantageProvider(config.data_provider)
    else:
        return YahooFinanceProvider(rate_limit_delay=60.0 / config.data_provider.rate_limit)


def serialize_screening_result(result: ScreeningResult) -> dict[str, Any]:
    """Convert ScreeningResult to JSON-serializable dict.

    Args:
        result: ScreeningResult to serialize

    Returns:
        JSON-serializable dictionary
    """
    return {
        "symbol": result.symbol,
        "timestamp": result.timestamp.isoformat(),
        "matches": result.matches,
        "signal_strength": result.signal_strength,
        "conditions_met": result.conditions_met,
        "conditions_missed": result.conditions_missed,
        "quote": (
            {
                "symbol": result.quote.symbol,
                "price": float(result.quote.price) if result.quote.price else None,
                "change": float(result.quote.change) if result.quote.change else None,
                "change_percent": (
                    float(result.quote.change_percent) if result.quote.change_percent else None
                ),
                "volume": int(result.quote.volume) if result.quote.volume else None,
            }
            if result.quote
            else None
        ),
        "indicators": (
            {
                "sma_20": (
                    float(result.indicators.sma_20)
                    if result.indicators and result.indicators.sma_20
                    else None
                ),
                "sma_60": (
                    float(result.indicators.sma_60)
                    if result.indicators and result.indicators.sma_60
                    else None
                ),
                "rsi_14": (
                    float(result.indicators.rsi_14)
                    if result.indicators and result.indicators.rsi_14
                    else None
                ),
            }
            if result.indicators
            else None
        ),
        "option_recommendation": (
            {
                "symbol": result.option_recommendation.symbol,
                "underlying_symbol": result.option_recommendation.underlying_symbol,
                "strike": result.option_recommendation.strike,
                "expiration": (
                    result.option_recommendation.expiration.isoformat()
                    if hasattr(result.option_recommendation.expiration, "isoformat")
                    else str(result.option_recommendation.expiration)
                ),
                "option_type": result.option_recommendation.option_type,
                "bid": result.option_recommendation.bid,
                "ask": result.option_recommendation.ask,
                "mid_price": result.option_recommendation.mid_price,
                "premium_yield": result.option_recommendation.premium_yield,
                "volume": result.option_recommendation.volume,
                "open_interest": result.option_recommendation.open_interest,
            }
            if result.option_recommendation
            else None
        ),
        "error": result.error,
    }


def serialize_stats(stats: ScreeningStats) -> dict[str, Any]:
    """Convert ScreeningStats to JSON-serializable dict.

    Args:
        stats: ScreeningStats to serialize

    Returns:
        JSON-serializable dictionary
    """
    return {
        "total_symbols": stats.total_symbols,
        "successful": stats.successful,
        "failed": stats.failed,
        "matches": stats.matches,
        "success_rate": round(stats.success_rate, 2),
        "start_time": stats.start_time.isoformat(),
        "end_time": stats.end_time.isoformat(),
        "duration_seconds": round(stats.duration_seconds, 2),
    }


async def run_screening(
    symbols: list[str],
    strategy: Strategy,
    config: Config,
    notify: bool = False,
) -> dict[str, Any]:
    """Run the screening pipeline.

    Args:
        symbols: List of symbols to screen
        strategy: Trading strategy to evaluate
        config: Application configuration
        notify: Whether to send notifications for matches

    Returns:
        Screening results dictionary
    """
    start_time = datetime.now()
    logger.info("screening_start", symbols_count=len(symbols), strategy=strategy.name)

    # Initialize data provider
    provider = get_data_provider(config)

    # Initialize screener
    max_concurrent = config.screening.max_concurrent_requests
    screener = StockScreener(
        provider=provider,
        strategy=strategy,
        max_concurrent=max_concurrent,
    )

    # Run screening
    matches, stats = await screener.screen_and_filter(symbols)

    # Serialize results
    results = {
        "matches": [serialize_screening_result(m) for m in matches],
        "stats": serialize_stats(stats),
        "strategy": strategy.name,
    }

    # Send notifications if enabled and matches found
    if notify and matches:
        notification_config = load_notification_config()
        if notification_config:
            try:
                notification_service = NotificationService(notification_config)
                await notification_service.send_batch_alerts(matches)
                logger.info("notifications_sent", count=len(matches))
                results["notifications_sent"] = str(len(matches))
            except Exception as e:
                logger.error("notification_failed", error=str(e), error_type=type(e).__name__)
                results["notification_error"] = str(e)
        else:
            logger.warning("notifications_skipped", reason="invalid_config")
            results["notifications_skipped"] = "Invalid notification configuration"

    duration = (datetime.now() - start_time).total_seconds()
    logger.info(
        "screening_complete",
        matches_count=len(matches),
        duration_seconds=duration,
        stats=serialize_stats(stats),
    )

    return results


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for stock screening.

    This handler processes screening events from EventBridge or direct invocation.
    It parses the event, loads the strategy, runs screening, and returns results.

    Args:
        event: Lambda event with screening parameters
        context: Lambda context (contains remaining_time, etc.)

    Returns:
        Response dict with statusCode and body

    Example event:
        {
            "strategy": "ofi",
            "symbols": ["AAPL", "MSFT", "GOOGL"],
            "notify": true,
            "dry_run": false
        }
    """
    # Configure logging from environment
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    setup_logging(level=log_level, format_type="json")

    request_id = getattr(context, "request_id", "unknown")
    logger = get_logger(__name__, component="LambdaHandler", request_id=request_id)

    logger.info("lambda_invocation_start", event_keys=list(event.keys()))

    # Parse event
    strategy_name = event.get("strategy")
    symbols = event.get("symbols", [])
    notify = event.get("notify", True)
    dry_run = event.get("dry_run", False)

    # Validate input
    if not symbols:
        logger.warning("no_symbols_provided")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No symbols provided in event"}),
        }

    # Use default symbols if not provided (for scheduled runs)
    if not symbols or (isinstance(symbols, list) and len(symbols) == 0):
        symbols_str = os.environ.get("DEFAULT_SYMBOLS", "")
        symbols = symbols_str.split(",") if symbols_str else []

    if not symbols:
        logger.warning("no_symbols_configured")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No symbols to screen"}),
        }

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        logger.error("config_load_failed", error=str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Configuration error: {str(e)}"}),
        }

    # Load strategy
    try:
        strategy_path = get_strategy_path(strategy_name)
        parser = StrategyParser()
        strategy = parser.parse_file(strategy_path)
        logger.info("strategy_loaded", name=strategy.name, path=strategy_path)
    except FileNotFoundError as e:
        logger.error("strategy_file_not_found", path=strategy_path, error=str(e))
        return {
            "statusCode": 404,
            "body": json.dumps({"error": f"Strategy file not found: {strategy_path}"}),
        }
    except Exception as e:
        logger.error("strategy_load_failed", error=str(e), error_type=type(e).__name__)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Strategy load failed: {str(e)}"}),
        }

    # Run screening (async in sync context)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        results = loop.run_until_complete(
            run_screening(
                symbols=symbols,
                strategy=strategy,
                config=config,
                notify=notify and not dry_run,
            )
        )
    except Exception as e:
        logger.error("screening_failed", error=str(e), error_type=type(e).__name__)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Screening failed: {str(e)}"}),
        }

    # Build response
    response = {
        "statusCode": 200,
        "body": json.dumps(
            {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "strategy": strategy.name,
                "symbols_processed": len(symbols),
                "matches_found": results["stats"]["matches"],
                "duration_seconds": results["stats"]["duration_seconds"],
                "matches": results["matches"] if not dry_run else [],
                "stats": results["stats"],
            }
        ),
    }

    logger.info(
        "lambda_invocation_complete",
        status_code=response["statusCode"],
        matches_found=results["stats"]["matches"],
        duration_seconds=results["stats"]["duration_seconds"],
    )

    return response


# For local testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Lambda handler locally")
    parser.add_argument("--symbols", default="AAPL,MSFT,GOOGL", help="Comma-separated symbols")
    parser.add_argument("--strategy", default="ofi", help="Strategy name or path")
    parser.add_argument("--notify", action="store_true", help="Send notifications")

    args = parser.parse_args()

    test_event = {
        "strategy": args.strategy,
        "symbols": args.symbols.split(","),
        "notify": args.notify,
        "dry_run": False,
    }

    class MockContext:
        request_id = "local-test"

    # Setup logging for local testing
    setup_logging(level="INFO", format_type="text")

    result = handler(test_event, MockContext())
    print(json.dumps(json.loads(result["body"]), indent=2))
