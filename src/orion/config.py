"""
Configuration management for Orion using Pydantic Settings.

This module provides type-safe configuration loading from environment variables
and YAML files with validation.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataProviderConfig(BaseSettings):
    """Configuration for data provider (API) settings."""

    provider: str = Field(default="alpha_vantage", description="Data provider name")
    api_key: str = Field(description="API key for data provider")
    rate_limit: int = Field(default=5, description="Requests per minute")

    model_config = SettingsConfigDict(env_prefix="DATA_PROVIDER__")


class CacheConfig(BaseSettings):
    """Configuration for caching strategy."""

    enabled: bool = Field(default=True, description="Enable caching")
    max_size: int = Field(default=1000, description="Maximum cache size")
    quote_ttl: int = Field(default=300, description="Quote cache TTL in seconds")
    option_chain_ttl: int = Field(default=900, description="Option chain cache TTL in seconds")
    historical_ttl: int = Field(default=86400, description="Historical data cache TTL in seconds")

    model_config = SettingsConfigDict(env_prefix="CACHE__")


class NotificationConfig(BaseSettings):
    """Configuration for notification services."""

    email_enabled: bool = Field(default=True, description="Enable email notifications")
    smtp_host: str = Field(description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    from_address: str = Field(description="Email from address")
    to_addresses: list[str] = Field(description="Email recipient addresses")

    model_config = SettingsConfigDict(env_prefix="NOTIFICATIONS__")

    @field_validator("to_addresses", mode="before")
    @classmethod
    def parse_to_addresses(cls, v: Any) -> list[str]:
        """Parse to_addresses from JSON string if needed."""
        if isinstance(v, str):
            import json

            result: list[str] = json.loads(v)
            return result
        return list(v) if v else []


class ScreeningConfig(BaseSettings):
    """Configuration for screening behavior."""

    default_stock_universe: list[str] = Field(
        default=["SPY_500"], description="Default stock universes to screen"
    )
    custom_symbols: list[str] = Field(default_factory=list, description="Custom symbols to screen")
    max_concurrent_requests: int = Field(default=5, description="Max concurrent API requests")

    model_config = SettingsConfigDict(env_prefix="SCREENING__")

    @field_validator("default_stock_universe", mode="before")
    @classmethod
    def parse_stock_universe(cls, v: Any) -> list[str]:
        """Parse stock universe from JSON string if needed."""
        if isinstance(v, str):
            import json

            result: list[str] = json.loads(v)
            return result
        return list(v) if v else []


class LoggingConfig(BaseSettings):
    """Configuration for logging."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="json", description="Log format (json or text)")
    output: str = Field(default="stdout", description="Log output destination")

    model_config = SettingsConfigDict(env_prefix="LOGGING__")


class Config(BaseSettings):
    """Main configuration class that combines all sub-configurations."""

    data_provider: DataProviderConfig = Field(default_factory=DataProviderConfig)  # type: ignore[arg-type]
    cache: CacheConfig = Field(default_factory=CacheConfig)  # type: ignore[arg-type]
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)  # type: ignore[arg-type]
    screening: ScreeningConfig = Field(default_factory=ScreeningConfig)  # type: ignore[arg-type]
    logging: LoggingConfig = Field(default_factory=LoggingConfig)  # type: ignore[arg-type]

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="ignore")


def load_config(env_file: str | None = None) -> Config:
    """
    Load configuration from environment variables and optional .env file.

    Args:
        env_file: Optional path to .env file. If None, uses default .env

    Returns:
        Validated Config instance

    Raises:
        ValidationError: If configuration is invalid
    """
    if env_file:
        return Config(_env_file=env_file)  # type: ignore[call-arg]
    return Config()


def load_config_from_yaml(yaml_file: Path) -> Config:
    """
    Load configuration from YAML file.

    Args:
        yaml_file: Path to YAML configuration file

    Returns:
        Validated Config instance

    Raises:
        FileNotFoundError: If YAML file doesn't exist
        ValidationError: If configuration is invalid
    """
    with open(yaml_file) as f:
        data = yaml.safe_load(f)

    # Convert nested dict to config objects
    return Config(**data)


def merge_configs(yaml_config: Config | None = None, env_config: Config | None = None) -> Config:
    """
    Merge YAML configuration with environment variable configuration.

    Environment variables take precedence over YAML settings.

    Args:
        yaml_config: Configuration loaded from YAML
        env_config: Configuration loaded from environment

    Returns:
        Merged Config instance
    """
    if yaml_config is None and env_config is None:
        return Config()

    if yaml_config is None:
        return env_config or Config()

    if env_config is None:
        return yaml_config

    # Environment variables override YAML
    return env_config
