"""
Tests for configuration management.
"""

from pathlib import Path

import pytest
import yaml
from orion.config import (
    CacheConfig,
    Config,
    DataProviderConfig,
    LoggingConfig,
    NotificationConfig,
    ScreeningConfig,
    load_config,
    load_config_from_yaml,
)
from pydantic import ValidationError


class TestDataProviderConfig:
    """Tests for DataProviderConfig."""

    def test_default_values(self, monkeypatch):
        """Test default configuration values."""
        monkeypatch.setenv("DATA_PROVIDER__API_KEY", "test_key")
        config = DataProviderConfig()

        assert config.provider == "alpha_vantage"
        assert config.api_key == "test_key"
        assert config.rate_limit == 5

    def test_from_env(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("DATA_PROVIDER__PROVIDER", "yahoo_finance")
        monkeypatch.setenv("DATA_PROVIDER__API_KEY", "my_api_key")
        monkeypatch.setenv("DATA_PROVIDER__RATE_LIMIT", "10")

        config = DataProviderConfig()

        assert config.provider == "yahoo_finance"
        assert config.api_key == "my_api_key"
        assert config.rate_limit == 10

    def test_missing_required_field_fails(self, monkeypatch):
        """Test that missing required field raises validation error."""
        # Remove API_KEY if set
        monkeypatch.delenv("DATA_PROVIDER__API_KEY", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            DataProviderConfig()

        assert "api_key" in str(exc_info.value).lower()


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_default_values(self):
        """Test default cache configuration."""
        config = CacheConfig()

        assert config.quote_ttl == 300
        assert config.option_chain_ttl == 900
        assert config.historical_ttl == 86400

    def test_from_env(self, monkeypatch):
        """Test loading cache config from environment."""
        monkeypatch.setenv("CACHE__QUOTE_TTL", "600")
        monkeypatch.setenv("CACHE__OPTION_CHAIN_TTL", "1800")
        monkeypatch.setenv("CACHE__HISTORICAL_TTL", "172800")

        config = CacheConfig()

        assert config.quote_ttl == 600
        assert config.option_chain_ttl == 1800
        assert config.historical_ttl == 172800


class TestNotificationConfig:
    """Tests for NotificationConfig."""

    def test_default_values(self, monkeypatch):
        """Test default notification configuration."""
        monkeypatch.setenv("NOTIFICATIONS__SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("NOTIFICATIONS__FROM_ADDRESS", "from@example.com")
        monkeypatch.setenv("NOTIFICATIONS__TO_ADDRESSES", '["to@example.com"]')

        config = NotificationConfig()

        assert config.email_enabled is True
        assert config.smtp_port == 587

    def test_to_addresses_from_json_string(self, monkeypatch):
        """Test parsing to_addresses from JSON string."""
        monkeypatch.setenv("NOTIFICATIONS__SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("NOTIFICATIONS__FROM_ADDRESS", "from@example.com")
        monkeypatch.setenv(
            "NOTIFICATIONS__TO_ADDRESSES", '["user1@example.com", "user2@example.com"]'
        )

        config = NotificationConfig()

        assert config.to_addresses == ["user1@example.com", "user2@example.com"]

    def test_to_addresses_from_list(self, monkeypatch):
        """Test to_addresses when provided as list."""
        monkeypatch.setenv("NOTIFICATIONS__SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("NOTIFICATIONS__FROM_ADDRESS", "from@example.com")

        config = NotificationConfig(to_addresses=["test@example.com"])

        assert config.to_addresses == ["test@example.com"]


class TestScreeningConfig:
    """Tests for ScreeningConfig."""

    def test_default_values(self):
        """Test default screening configuration."""
        config = ScreeningConfig()

        assert config.default_stock_universe == ["SPY_500"]
        assert config.custom_symbols == []
        assert config.max_concurrent_requests == 5

    def test_stock_universe_from_json(self, monkeypatch):
        """Test parsing stock universe from JSON string."""
        monkeypatch.setenv("SCREENING__DEFAULT_STOCK_UNIVERSE", '["SPY_500", "NASDAQ_100"]')

        config = ScreeningConfig()

        assert config.default_stock_universe == ["SPY_500", "NASDAQ_100"]


class TestLoggingConfig:
    """Tests for LoggingConfig."""

    def test_default_values(self):
        """Test default logging configuration."""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert config.format == "json"
        assert config.output == "stdout"

    def test_from_env(self, monkeypatch):
        """Test loading logging config from environment."""
        monkeypatch.setenv("LOGGING__LEVEL", "DEBUG")
        monkeypatch.setenv("LOGGING__FORMAT", "text")

        config = LoggingConfig()

        assert config.level == "DEBUG"
        assert config.format == "text"


class TestConfig:
    """Tests for main Config class."""

    def test_config_from_env(self, monkeypatch):
        """Test loading complete config from environment variables."""
        # Set required fields
        monkeypatch.setenv("DATA_PROVIDER__API_KEY", "test_key")
        monkeypatch.setenv("NOTIFICATIONS__SMTP_HOST", "smtp.test.com")
        monkeypatch.setenv("NOTIFICATIONS__FROM_ADDRESS", "from@test.com")
        monkeypatch.setenv("NOTIFICATIONS__TO_ADDRESSES", '["to@test.com"]')

        config = load_config()

        assert isinstance(config, Config)
        assert config.data_provider.api_key == "test_key"
        assert config.cache.quote_ttl == 300
        assert config.notifications.smtp_host == "smtp.test.com"

    def test_config_from_yaml(self, tmp_path):
        """Test loading config from YAML file."""
        yaml_content = {
            "data_provider": {"provider": "alpha_vantage", "api_key": "yaml_key", "rate_limit": 10},
            "cache": {"quote_ttl": 600, "option_chain_ttl": 1200, "historical_ttl": 43200},
            "notifications": {
                "email_enabled": True,
                "smtp_host": "smtp.yaml.com",
                "smtp_port": 587,
                "from_address": "yaml@test.com",
                "to_addresses": ["recipient@test.com"],
            },
            "screening": {"max_concurrent_requests": 10},
            "logging": {"level": "DEBUG"},
        }

        yaml_file = tmp_path / "config.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        config = load_config_from_yaml(yaml_file)

        assert config.data_provider.api_key == "yaml_key"
        assert config.data_provider.rate_limit == 10
        assert config.cache.quote_ttl == 600
        assert config.notifications.smtp_host == "smtp.yaml.com"
        assert config.screening.max_concurrent_requests == 10
        assert config.logging.level == "DEBUG"

    def test_env_overrides_yaml(self, tmp_path, monkeypatch):
        """Test that environment variables override YAML settings."""
        # Create YAML config with all required fields
        yaml_content = {
            "data_provider": {"provider": "alpha_vantage", "api_key": "yaml_key", "rate_limit": 5},
            "notifications": {
                "smtp_host": "smtp.yaml.com",
                "from_address": "yaml@test.com",
                "to_addresses": ["yaml@test.com"],
            },
            "logging": {"level": "INFO"},
        }

        yaml_file = tmp_path / "config.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        # Load YAML config
        yaml_config = load_config_from_yaml(yaml_file)
        assert yaml_config.data_provider.rate_limit == 5

        # Set environment variables to override
        monkeypatch.setenv("DATA_PROVIDER__API_KEY", "yaml_key")
        monkeypatch.setenv("DATA_PROVIDER__RATE_LIMIT", "15")
        monkeypatch.setenv("NOTIFICATIONS__SMTP_HOST", "smtp.test.com")
        monkeypatch.setenv("NOTIFICATIONS__FROM_ADDRESS", "from@test.com")
        monkeypatch.setenv("NOTIFICATIONS__TO_ADDRESSES", '["to@test.com"]')

        # Environment should override
        env_config = load_config()
        assert env_config.data_provider.rate_limit == 15

    def test_missing_yaml_file_raises_error(self):
        """Test that loading from non-existent YAML raises error."""
        with pytest.raises(FileNotFoundError):
            load_config_from_yaml(Path("/nonexistent/config.yaml"))

    def test_invalid_yaml_structure_raises_error(self, tmp_path):
        """Test that invalid YAML structure raises validation error."""
        yaml_file = tmp_path / "invalid.yaml"
        with open(yaml_file, "w") as f:
            # Missing required fields
            yaml.dump({"data_provider": {"provider": "test"}}, f)

        with pytest.raises(ValidationError):
            load_config_from_yaml(yaml_file)
