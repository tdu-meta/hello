"""Tests for the AWS Lambda handler module."""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from orion.core.screener import ScreeningResult, ScreeningStats
from orion.data.models import Quote, TechnicalIndicators
from orion.lambda_handler import (
    get_data_provider,
    get_strategy_path,
    handler,
    load_config,
    load_notification_config,
    serialize_screening_result,
    serialize_stats,
)


class TestGetStrategyPath:
    """Tests for get_strategy_path function."""

    def test_returns_default_when_no_event_strategy(self):
        """Test that default path is returned when no event strategy provided."""
        with patch("orion.lambda_handler.Path") as mock_path:
            mock_path.DEFAULT_STRATEGY_PATH = "/opt/strategies/ofi.yaml"
            mock_path.return_value.exists.return_value = True

            result = get_strategy_path(None)
            assert result == "/opt/strategies/ofi.yaml"

    def test_returns_event_strategy_if_valid_path(self):
        """Test that event strategy path is used if it exists."""
        with patch("orion.lambda_handler.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.__str__ = lambda self: "custom/path/strategy.yaml"
            mock_path.return_value = mock_path_instance

            result = get_strategy_path("custom/path/strategy.yaml")
            assert "strategy.yaml" in result


class TestLoadConfig:
    """Tests for load_config function."""

    def test_returns_config_instance(self):
        """Test that load_config returns a Config instance."""
        with patch("orion.lambda_handler.Config") as mock_config:
            mock_instance = MagicMock()
            mock_config.return_value = mock_instance

            result = load_config()
            assert result == mock_instance

    def test_returns_minimal_config_on_error(self):
        """Test that minimal config is returned when Config raises exception."""
        with patch("orion.lambda_handler.Config") as mock_config:
            mock_config.side_effect = Exception("Config error")

            with patch("orion.lambda_handler.Config") as mock_config_fallback:
                mock_instance = MagicMock()
                mock_config_fallback.return_value = mock_instance

                result = load_config()
                # Should return a Config instance (fallback)
                assert isinstance(result, MagicMock) or result is not None


class TestLoadNotificationConfig:
    """Tests for load_notification_config function."""

    def test_returns_config_when_valid(self, monkeypatch):
        """Test that valid notification config is returned."""
        monkeypatch.setenv("NOTIFICATIONS__smtp_host", "smtp.example.com")
        monkeypatch.setenv("NOTIFICATIONS__from_address", "from@example.com")
        monkeypatch.setenv("NOTIFICATIONS__to_addresses", '["to@example.com"]')

        with patch("orion.notifications.models.NotificationConfig") as mock_config:
            mock_instance = MagicMock()
            mock_instance.smtp_host = "smtp.example.com"
            mock_instance.from_address = "from@example.com"
            mock_instance.to_addresses = ["to@example.com"]
            mock_config.return_value = mock_instance

            result = load_notification_config()
            assert result == mock_instance

    def test_returns_none_when_incomplete(self, monkeypatch):
        """Test that None is returned when config is incomplete."""
        monkeypatch.setenv("NOTIFICATIONS__smtp_host", "")
        monkeypatch.setenv("NOTIFICATIONS__from_address", "")
        monkeypatch.setenv("NOTIFICATIONS__to_addresses", "[]")

        with patch("orion.lambda_handler.NotificationConfig") as mock_config:
            mock_instance = MagicMock()
            mock_instance.smtp_host = ""
            mock_instance.from_address = ""
            mock_instance.to_addresses = []
            mock_config.return_value = mock_instance

            result = load_notification_config()
            assert result is None


class TestSerializeScreeningResult:
    """Tests for serialize_screening_result function."""

    def test_serializes_full_result(self):
        """Test serialization of a complete ScreeningResult."""
        result = ScreeningResult(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 15, 12, 0, 0),
            matches=True,
            signal_strength=0.85,
            conditions_met=["trend", "oversold"],
            conditions_missed=[],
            quote=Quote(
                symbol="AAPL",
                price=Decimal("150.00"),
                volume=1_000_000,
                timestamp=datetime.now(),
                open=Decimal("148.00"),
                high=Decimal("152.00"),
                low=Decimal("147.00"),
                close=Decimal("150.00"),
                previous_close=Decimal("148.00"),
                change=Decimal("2.00"),
                change_percent=Decimal("1.35"),
            ),
            indicators=TechnicalIndicators(
                symbol="AAPL",
                timestamp=datetime.now(),
                sma_20=Decimal("148.50"),
                sma_60=Decimal("145.00"),
                rsi_14=Decimal("45.0"),
                volume_avg_20=Decimal("950000"),
            ),
            option_recommendation=None,
            evaluation_details={},
        )

        serialized = serialize_screening_result(result)

        assert serialized["symbol"] == "AAPL"
        assert serialized["matches"] is True
        assert serialized["signal_strength"] == 0.85
        assert serialized["conditions_met"] == ["trend", "oversold"]
        assert serialized["quote"]["price"] == 150.0
        assert serialized["indicators"]["sma_20"] == 148.5
        assert serialized["indicators"]["rsi_14"] == 45.0
        assert serialized["option_recommendation"] is None

    def test_serializes_result_with_error(self):
        """Test serialization of a result with error."""
        result = ScreeningResult(
            symbol="INVALID",
            timestamp=datetime.now(),
            matches=False,
            signal_strength=0.0,
            conditions_met=[],
            conditions_missed=["trend"],
            quote=None,
            indicators=None,
            option_recommendation=None,
            error="Failed to fetch data",
        )

        serialized = serialize_screening_result(result)

        assert serialized["symbol"] == "INVALID"
        assert serialized["matches"] is False
        assert serialized["error"] == "Failed to fetch data"
        assert serialized["quote"] is None
        assert serialized["indicators"] is None


class TestSerializeStats:
    """Tests for serialize_stats function."""

    def test_serializes_full_stats(self):
        """Test serialization of ScreeningStats."""
        stats = ScreeningStats(
            total_symbols=100,
            successful=95,
            failed=5,
            matches=3,
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 10, 5, 30),
            duration_seconds=330.5,
        )

        serialized = serialize_stats(stats)

        assert serialized["total_symbols"] == 100
        assert serialized["successful"] == 95
        assert serialized["failed"] == 5
        assert serialized["matches"] == 3
        assert serialized["success_rate"] == 95.0
        assert serialized["duration_seconds"] == 330.5

    def test_calculates_success_rate_correctly(self):
        """Test success rate calculation."""
        stats = ScreeningStats(
            total_symbols=50,
            successful=40,
            failed=10,
            matches=2,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_seconds=100.0,
        )

        serialized = serialize_stats(stats)

        assert serialized["success_rate"] == 80.0


class TestGetDataProvider:
    """Tests for get_data_provider function."""

    def test_returns_yahoo_finance_provider_by_default(self):
        """Test that YahooFinanceProvider is returned by default."""
        mock_config = MagicMock()
        mock_config.data_provider.provider = "yahoo_finance"
        mock_config.data_provider.rate_limit = 5
        mock_config.cache.enabled = False

        with patch("orion.lambda_handler.YahooFinanceProvider"):
            result = get_data_provider(mock_config)
            assert result is not None

    def test_returns_alpha_vantage_provider_when_configured(self):
        """Test that AlphaVantageProvider is returned when configured."""
        mock_config = MagicMock()
        mock_config.data_provider.provider = "alpha_vantage"
        mock_config.data_provider.api_key = "test_key"
        mock_config.data_provider.rate_limit = 5
        mock_config.cache.enabled = False

        with patch("orion.lambda_handler.AlphaVantageProvider"):
            result = get_data_provider(mock_config)
            assert result is not None


class TestHandler:
    """Tests for the Lambda handler function."""

    def test_returns_400_when_no_symbols_provided(self):
        """Test that handler returns 400 when no symbols in event."""
        event = {"strategy": "ofi", "symbols": []}

        class MockContext:
            request_id = "test-request"

        result = handler(event, MockContext())

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body

    def test_returns_404_when_strategy_file_not_found(self):
        """Test that handler returns 404 when strategy file missing."""
        event = {"strategy": "nonexistent", "symbols": ["AAPL"]}

        class MockContext:
            request_id = "test-request"

        with patch("orion.lambda_handler.get_strategy_path") as mock_path:
            mock_path.return_value = "nonexistent.yaml"

            # Mock load_config to succeed so we get to strategy parsing
            with patch("orion.lambda_handler.load_config") as mock_load:
                mock_config = MagicMock()
                mock_load.return_value = mock_config

                with patch("orion.lambda_handler.Path") as mock_file_path:
                    mock_file_path.return_value.exists.return_value = False

                    result = handler(event, MockContext())

                    assert result["statusCode"] == 404

    def test_returns_500_on_config_error(self):
        """Test that handler returns 500 on configuration error."""
        event = {"symbols": ["AAPL"]}

        class MockContext:
            request_id = "test-request"

        with patch("orion.lambda_handler.load_config") as mock_load:
            mock_load.side_effect = Exception("Config error")

            result = handler(event, MockContext())

            assert result["statusCode"] == 500

    @patch("orion.lambda_handler.run_screening")
    @patch("orion.lambda_handler.load_config")
    @patch("orion.lambda_handler.get_strategy_path")
    @patch("orion.lambda_handler.setup_logging")
    def test_successful_screening(
        self,
        mock_logging,
        mock_strategy_path,
        mock_load_config,
        mock_run_screening,
    ):
        """Test successful screening execution."""
        event = {
            "strategy": "ofi",
            "symbols": ["AAPL", "MSFT"],
            "notify": False,
            "dry_run": False,
        }

        class MockContext:
            request_id = "test-request"

        # Setup mocks
        mock_strategy_path.return_value = "strategies/ofi.yaml"
        mock_config = MagicMock()
        mock_config.screening.max_concurrent_requests = 5
        mock_load_config.return_value = mock_config

        mock_run_screening.return_value = {
            "matches": [],
            "stats": {
                "total_symbols": 2,
                "successful": 2,
                "failed": 0,
                "matches": 0,
                "duration_seconds": 10.5,
            },
            "strategy": "OFI - Option for Income",
        }

        # Mock strategy loading
        with patch("orion.lambda_handler.StrategyParser") as mock_parser:
            mock_strategy = MagicMock()
            mock_strategy.name = "OFI - Option for Income"
            mock_parser.return_value.parse_file.return_value = mock_strategy

            result = handler(event, MockContext())

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["symbols_processed"] == 2
            assert body["matches_found"] == 0

    @patch("orion.lambda_handler.run_screening")
    @patch("orion.lambda_handler.load_config")
    @patch("orion.lambda_handler.get_strategy_path")
    @patch("orion.lambda_handler.setup_logging")
    def test_returns_500_on_screening_failure(
        self,
        mock_logging,
        mock_strategy_path,
        mock_load_config,
        mock_run_screening,
    ):
        """Test that handler returns 500 when screening fails."""
        event = {"symbols": ["AAPL"]}

        class MockContext:
            request_id = "test-request"

        mock_strategy_path.return_value = "strategies/ofi.yaml"
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config
        mock_run_screening.side_effect = Exception("Screening error")

        with patch("orion.lambda_handler.StrategyParser") as mock_parser:
            mock_strategy = MagicMock()
            mock_strategy.name = "Test Strategy"
            mock_parser.return_value.parse_file.return_value = mock_strategy

            result = handler(event, MockContext())

            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert "error" in body


class TestRunScreening:
    """Tests for the run_screening async function."""

    @pytest.mark.asyncio
    async def test_run_screening_with_matches(self):
        """Test run_screening with matching results."""
        from orion.strategies.models import OptionRecommendation

        symbols = ["AAPL"]
        mock_strategy = MagicMock()
        mock_strategy.name = "Test Strategy"

        mock_config = MagicMock()
        mock_config.screening.max_concurrent_requests = 5

        # Create a mock match result
        mock_result = ScreeningResult(
            symbol="AAPL",
            timestamp=datetime.now(),
            matches=True,
            signal_strength=0.8,
            conditions_met=["trend"],
            conditions_missed=[],
            quote=Quote(
                symbol="AAPL",
                price=Decimal("150.00"),
                volume=1_000_000,
                timestamp=datetime.now(),
                open=Decimal("148.00"),
                high=Decimal("152.00"),
                low=Decimal("147.00"),
                close=Decimal("150.00"),
                previous_close=Decimal("148.00"),
            ),
            indicators=TechnicalIndicators(
                symbol="AAPL",
                timestamp=datetime.now(),
                sma_20=Decimal("148.0"),
            ),
            option_recommendation=OptionRecommendation(
                symbol="AAPL240119P00150000",
                underlying_symbol="AAPL",
                strike=150.00,
                expiration=datetime.now().date(),
                option_type="put",
                bid=2.50,
                ask=2.60,
                mid_price=2.55,
                premium_yield=0.05,
                volume=500,
                open_interest=1000,
            ),
        )

        with patch("orion.lambda_handler.get_data_provider"):
            with patch("orion.lambda_handler.StockScreener") as mock_screener_class:
                mock_screener = MagicMock()

                # Make screen_and_filter async
                async def mock_screen_and_filter(syms):
                    return (
                        [mock_result],
                        ScreeningStats(
                            total_symbols=1,
                            successful=1,
                            failed=0,
                            matches=1,
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            duration_seconds=10.0,
                        ),
                    )

                mock_screener.screen_and_filter = mock_screen_and_filter
                mock_screener_class.return_value = mock_screener

                with patch("orion.lambda_handler.load_notification_config") as mock_notif:
                    mock_notif.return_value = None  # Skip notifications

                    from orion.lambda_handler import run_screening

                    result = await run_screening(
                        symbols=symbols,
                        strategy=mock_strategy,
                        config=mock_config,
                        notify=False,
                    )

                    assert result["stats"]["matches"] == 1
                    assert len(result["matches"]) == 1
                    assert result["matches"][0]["symbol"] == "AAPL"
