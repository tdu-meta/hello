"""
Structured logging setup for Orion using structlog.

This module provides JSON-formatted structured logging with context support
for better observability and debugging.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger


def add_app_context(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add application context to log events.

    Args:
        logger: The wrapped logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary

    Returns:
        Modified event dictionary with app context
    """
    event_dict["app"] = "orion"
    return event_dict


def setup_logging(level: str = "INFO", format_type: str = "json") -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Output format - 'json' for JSON or 'text' for human-readable

    Example:
        >>> setup_logging(level="DEBUG", format_type="text")
        >>> logger = structlog.get_logger()
        >>> logger.info("application_started", version="1.0.0")
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Choose processors based on format type
    if format_type == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            add_app_context,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None, **initial_values: Any) -> Any:  # type: ignore[misc]
    """
    Get a configured logger instance.

    Args:
        name: Optional logger name (typically module name)
        **initial_values: Initial context values to bind to the logger

    Returns:
        Configured BoundLogger instance

    Example:
        >>> logger = get_logger(__name__, component="screener")
        >>> logger.info("screening_started", symbols_count=500)
    """
    logger = structlog.get_logger(name)

    if initial_values:
        logger = logger.bind(**initial_values)

    return logger


# Create a default logger for the package
logger = get_logger("orion")
