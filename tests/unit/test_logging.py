"""
Tests for logging infrastructure.
"""

import json

import structlog
from orion.utils.logging import get_logger, setup_logging


class TestLoggingSetup:
    """Tests for logging setup and configuration."""

    def test_setup_logging_default(self, capsys):
        """Test logging setup with default parameters."""
        setup_logging()
        logger = structlog.get_logger()

        logger.info("test_message", key="value")

        captured = capsys.readouterr()
        assert "test_message" in captured.out

    def test_setup_logging_json_format(self, capsys):
        """Test logging outputs JSON format."""
        setup_logging(level="INFO", format_type="json")
        logger = structlog.get_logger()

        logger.info("json_test", test_key="test_value")

        captured = capsys.readouterr()
        # Should be valid JSON
        log_line = captured.out.strip()
        log_data = json.loads(log_line)

        assert log_data["event"] == "json_test"
        assert log_data["test_key"] == "test_value"
        assert log_data["level"] == "info"
        assert log_data["app"] == "orion"
        assert "timestamp" in log_data

    def test_setup_logging_text_format(self, capsys):
        """Test logging outputs human-readable text format."""
        setup_logging(level="INFO", format_type="text")
        logger = structlog.get_logger()

        logger.info("text_test", key="value")

        captured = capsys.readouterr()
        assert "text_test" in captured.out
        # Text format includes the key-value pair (may have ANSI color codes)
        assert "key" in captured.out and "value" in captured.out

    def test_log_level_filtering(self, capsys):
        """Test that debug logs are filtered when level=INFO."""
        setup_logging(level="INFO", format_type="json")
        logger = structlog.get_logger()

        logger.debug("debug_message")
        logger.info("info_message")

        captured = capsys.readouterr()

        # Debug should not appear
        assert "debug_message" not in captured.out
        # Info should appear
        assert "info_message" in captured.out

    def test_log_level_debug_shows_all(self, capsys):
        """Test that DEBUG level shows all log messages."""
        setup_logging(level="DEBUG", format_type="json")
        logger = structlog.get_logger()

        logger.debug("debug_message")
        logger.info("info_message")

        captured = capsys.readouterr()

        # Both should appear
        assert "debug_message" in captured.out
        assert "info_message" in captured.out


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_without_name(self, capsys):
        """Test getting logger without specific name."""
        setup_logging(level="INFO", format_type="json")
        logger = get_logger()

        logger.info("test_event")

        captured = capsys.readouterr()
        log_data = json.loads(captured.out.strip())
        assert log_data["event"] == "test_event"

    def test_get_logger_with_name(self, capsys):
        """Test getting logger with specific name."""
        setup_logging(level="INFO", format_type="json")
        logger = get_logger("test_module")

        logger.info("named_event")

        captured = capsys.readouterr()
        assert "named_event" in captured.out

    def test_get_logger_with_initial_context(self, capsys):
        """Test logger with initial bound context."""
        setup_logging(level="INFO", format_type="json")
        logger = get_logger("test_module", component="screener", request_id="12345")

        logger.info("context_test")

        captured = capsys.readouterr()
        log_data = json.loads(captured.out.strip())

        assert log_data["component"] == "screener"
        assert log_data["request_id"] == "12345"
        assert log_data["event"] == "context_test"

    def test_structured_context_preserved(self, capsys):
        """Test that structured context is preserved across log calls."""
        setup_logging(level="INFO", format_type="json")
        logger = get_logger(component="test")

        logger.info("first_event", action="start")
        logger.info("second_event", action="end")

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")

        # Both log lines should have the component context
        for line in lines:
            log_data = json.loads(line)
            assert log_data["component"] == "test"

    def test_logger_bind_adds_context(self, capsys):
        """Test that bind() adds persistent context."""
        setup_logging(level="INFO", format_type="json")
        logger = get_logger()

        # Bind additional context
        logger = logger.bind(user_id="user123", session_id="session456")

        logger.info("bound_event")

        captured = capsys.readouterr()
        log_data = json.loads(captured.out.strip())

        assert log_data["user_id"] == "user123"
        assert log_data["session_id"] == "session456"

    def test_different_log_levels(self, capsys):
        """Test different log levels produce correct output."""
        setup_logging(level="DEBUG", format_type="json")
        logger = get_logger()

        logger.debug("debug_event")
        logger.info("info_event")
        logger.warning("warning_event")
        logger.error("error_event")

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")

        levels = []
        for line in lines:
            log_data = json.loads(line)
            levels.append(log_data["level"])

        assert "debug" in levels
        assert "info" in levels
        assert "warning" in levels
        assert "error" in levels

    def test_app_context_always_present(self, capsys):
        """Test that 'app' context is always added."""
        setup_logging(level="INFO", format_type="json")
        logger = get_logger()

        logger.info("app_context_test")

        captured = capsys.readouterr()
        log_data = json.loads(captured.out.strip())

        assert log_data["app"] == "orion"

    def test_timestamp_always_present(self, capsys):
        """Test that timestamp is always included."""
        setup_logging(level="INFO", format_type="json")
        logger = get_logger()

        logger.info("timestamp_test")

        captured = capsys.readouterr()
        log_data = json.loads(captured.out.strip())

        assert "timestamp" in log_data
        # Check ISO format (should contain 'T' and 'Z')
        assert "T" in log_data["timestamp"]
