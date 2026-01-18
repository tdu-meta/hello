"""Tests for the notifications module."""

from datetime import datetime
from decimal import Decimal

import pytest
from orion.core.screener import ScreeningResult
from orion.data.models import Quote, TechnicalIndicators
from orion.notifications.models import NotificationConfig
from orion.notifications.service import NotificationService
from orion.strategies.models import OptionRecommendation


@pytest.fixture
def notification_config():
    """Create a notification config for testing."""
    return NotificationConfig(
        enabled=False,  # Disabled for unit tests
        smtp_host="localhost",
        smtp_port=587,
        smtp_user="test@example.com",
        smtp_password="password",
        from_address="orion@example.com",
        to_addresses=["recipient@example.com"],
    )


@pytest.fixture
def screening_result_with_match():
    """Create a screening result with a match for testing."""
    quote = Quote(
        symbol="AAPL",
        price=Decimal("150.00"),
        volume=1_000_000,
        timestamp=datetime.now(),
        open=Decimal("148.00"),
        high=Decimal("152.00"),
        low=Decimal("147.00"),
        close=Decimal("150.00"),
        previous_close=Decimal("147.00"),
        change=Decimal("3.00"),
        change_percent=2.04,
    )

    option_rec = OptionRecommendation(
        symbol="AAPL240119P00150000",
        underlying_symbol="AAPL",
        strike=150.0,
        expiration=datetime.now().date(),
        option_type="put",
        bid=2.50,
        ask=2.60,
        mid_price=2.55,
        premium_yield=0.15,
        volume=500,
        open_interest=1000,
        implied_volatility=0.25,
        delta=-0.45,
        reason="15% annualized yield at the money",
    )

    return ScreeningResult(
        symbol="AAPL",
        timestamp=datetime.now(),
        matches=True,
        signal_strength=0.85,
        conditions_met=["trend", "oversold", "bounce"],
        conditions_missed=[],
        quote=quote,
        indicators=TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime.now(),
            sma_20=152.0,
            sma_60=148.0,
            rsi_14=65.0,
            volume_avg_20=1_200_000,
        ),
        option_recommendation=option_rec,
    )


class TestNotificationConfig:
    """Tests for NotificationConfig."""

    def test_create_config(self):
        """Test creating a notification config."""
        config = NotificationConfig(
            enabled=True,
            smtp_host="smtp.example.com",
            smtp_port=587,
            from_address="orion@example.com",
            to_addresses=["user@example.com"],
        )
        assert config.enabled is True
        assert config.smtp_host == "smtp.example.com"
        assert config.smtp_port == 587
        assert len(config.to_addresses) == 1

    def test_config_from_env(self, monkeypatch):
        """Test creating config from environment variables."""
        monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_USER", "user@example.com")
        monkeypatch.setenv("SMTP_PASSWORD", "secret")
        monkeypatch.setenv("NOTIFICATION_FROM", "orion@example.com")
        monkeypatch.setenv("NOTIFICATION_TO", "recipient1@example.com,recipient2@example.com")
        monkeypatch.setenv("NOTIFICATION_SUBJECT_PREFIX", "🎯 Signal")

        config = NotificationConfig.from_env()

        assert config.enabled is True
        assert config.smtp_host == "smtp.example.com"
        assert config.smtp_port == 587
        assert config.smtp_user == "user@example.com"
        assert config.smtp_password == "secret"
        assert config.from_address == "orion@example.com"
        assert config.to_addresses == ["recipient1@example.com", "recipient2@example.com"]
        assert config.subject_prefix == "🎯 Signal"

    def test_config_from_env_defaults(self, monkeypatch):
        """Test creating config from environment with defaults."""
        # Clear relevant env vars
        for key in [
            "NOTIFICATIONS_ENABLED",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "NOTIFICATION_FROM",
            "NOTIFICATION_TO",
            "NOTIFICATION_SUBJECT_PREFIX",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = NotificationConfig.from_env()

        assert config.enabled is False
        assert config.smtp_host == "localhost"
        assert config.smtp_port == 587
        assert config.from_address == "orion@example.com"
        assert config.to_addresses == []

    def test_config_is_valid(self):
        """Test config validation."""
        # Valid config
        config = NotificationConfig(
            enabled=True,
            smtp_host="smtp.example.com",
            from_address="orion@example.com",
            to_addresses=["user@example.com"],
        )
        assert config.is_valid() is True

        # Disabled
        config2 = NotificationConfig(
            enabled=False,
            smtp_host="smtp.example.com",
            from_address="orion@example.com",
            to_addresses=["user@example.com"],
        )
        assert config2.is_valid() is False

        # Missing host
        config3 = NotificationConfig(
            enabled=True,
            smtp_host="",
            from_address="orion@example.com",
            to_addresses=["user@example.com"],
        )
        assert config3.is_valid() is False

        # Missing from address
        config4 = NotificationConfig(
            enabled=True,
            smtp_host="smtp.example.com",
            from_address="",
            to_addresses=["user@example.com"],
        )
        assert config4.is_valid() is False

        # No recipients
        config5 = NotificationConfig(
            enabled=True,
            smtp_host="smtp.example.com",
            from_address="orion@example.com",
            to_addresses=[],
        )
        assert config5.is_valid() is False


class TestNotificationService:
    """Tests for NotificationService."""

    def test_service_initialization(self, notification_config):
        """Test service initialization."""
        service = NotificationService(notification_config)
        assert service.config == notification_config

    def test_service_is_enabled(self, notification_config):
        """Test is_enabled check."""
        # Disabled config
        config = NotificationConfig(enabled=False)
        service = NotificationService(config)
        assert service.is_enabled() is False

        # Enabled but invalid config
        config2 = NotificationConfig(
            enabled=True,
            from_address="orion@example.com",
            to_addresses=["user@example.com"],
            smtp_host="",  # Missing
        )
        service2 = NotificationService(config2)
        assert service2.is_enabled() is False

        # Valid config
        config3 = NotificationConfig(
            enabled=True,
            from_address="orion@example.com",
            to_addresses=["user@example.com"],
            smtp_host="smtp.example.com",
        )
        service3 = NotificationService(config3)
        assert service3.is_enabled() is True

    @pytest.mark.asyncio
    async def test_send_alert_when_disabled(self, notification_config, screening_result_with_match):
        """Test sending alert when notifications are disabled."""
        service = NotificationService(notification_config)

        result = await service.send_alert(screening_result_with_match)

        assert result is False  # Should return False when disabled

    @pytest.mark.asyncio
    async def test_send_alert_for_non_match(self, notification_config):
        """Test that alerts are not sent for non-matching results."""
        service = NotificationService(notification_config)

        non_match = ScreeningResult(
            symbol="AAPL",
            timestamp=datetime.now(),
            matches=False,  # No match
            signal_strength=0.3,
            conditions_met=[],
            conditions_missed=["trend", "oversold"],
            quote=None,
            indicators=None,
            option_recommendation=None,
        )

        result = await service.send_alert(non_match)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_batch_alerts_empty(self, notification_config):
        """Test sending batch alerts with empty results."""
        service = NotificationService(notification_config)

        count = await service.send_batch_alerts([])

        assert count == 0

    @pytest.mark.asyncio
    async def test_send_batch_alerts_no_matches(self, notification_config):
        """Test sending batch alerts with no matches."""
        service = NotificationService(notification_config)

        non_match = ScreeningResult(
            symbol="AAPL",
            timestamp=datetime.now(),
            matches=False,
            signal_strength=0.3,
            conditions_met=[],
            conditions_missed=["trend"],
            quote=None,
            indicators=None,
            option_recommendation=None,
        )

        count = await service.send_batch_alerts([non_match])

        assert count == 0

    def test_build_html_body(self, notification_config, screening_result_with_match):
        """Test HTML email body generation."""
        service = NotificationService(notification_config)
        html = service._build_html_body(screening_result_with_match)

        assert "AAPL" in html
        assert "85%" in html  # signal strength
        assert "trend" in html
        assert "oversold" in html
        assert "bounce" in html
        assert "15%" in html  # yield
        assert "$150.00" in html  # strike

    def test_build_plain_text_body(self, notification_config, screening_result_with_match):
        """Test plain text email body generation."""
        service = NotificationService(notification_config)
        text = service._build_plain_text_body(screening_result_with_match)

        assert "AAPL" in text
        assert "85%" in text
        assert "trend" in text
        assert "oversold" in text
        assert "bounce" in text

    def test_build_summary_html(self, notification_config, screening_result_with_match):
        """Test summary HTML generation."""
        service = NotificationService(notification_config)

        # Create multiple results
        results = [screening_result_with_match]
        for symbol in ["MSFT", "GOOGL"]:
            result = ScreeningResult(
                symbol=symbol,
                timestamp=datetime.now(),
                matches=True,
                signal_strength=0.75,
                conditions_met=["trend"],
                conditions_missed=[],
                quote=screening_result_with_match.quote,
                indicators=None,
                option_recommendation=None,
            )
            results.append(result)

        html = service._build_summary_html(results)

        assert "3 New Matches" in html
        assert "AAPL" in html
        assert "MSFT" in html
        assert "GOOGL" in html

    def test_strength_color(self, notification_config):
        """Test signal strength color mapping."""
        service = NotificationService(notification_config)

        assert service._strength_color(0.9) == "10b981"  # Green
        assert service._strength_color(0.6) == "f59e0b"  # Orange
        assert service._strength_color(0.3) == "ef4444"  # Red

    def test_build_email_message(self, notification_config, screening_result_with_match):
        """Test email message building."""
        service = NotificationService(notification_config)
        message = service._build_email_message(screening_result_with_match)

        assert message["From"] == "orion@example.com"
        assert message["To"] == "recipient@example.com"
        assert "AAPL" in message["Subject"]
        assert message.is_multipart()

    def test_build_summary_email(self, notification_config, screening_result_with_match):
        """Test summary email message building."""
        service = NotificationService(notification_config)
        results = [screening_result_with_match]

        message = service._build_summary_email(results)

        assert message["From"] == "orion@example.com"
        assert message["To"] == "recipient@example.com"
        assert "1 New Matches" in message["Subject"]
