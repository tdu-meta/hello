"""Notification configuration models."""

from dataclasses import dataclass


@dataclass
class NotificationConfig:
    """Configuration for email notifications.

    Attributes:
        enabled: Whether notifications are enabled
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port
        smtp_user: SMTP username
        smtp_password: SMTP password
        smtp_use_tls: Whether to use STARTTLS
        from_address: Sender email address
        to_addresses: List of recipient email addresses
    """

    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    from_address: str = "orion@example.com"
    to_addresses: list[str] = frozenset()  # type: ignore[assignment]
    subject_prefix: str = "🎯 OFI Signal"

    def __post_init__(self) -> None:
        """Convert to_addresses to list if needed."""
        if isinstance(self.to_addresses, frozenset):
            object.__setattr__(self, "to_addresses", list(self.to_addresses))

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "NotificationConfig":
        """Create NotificationConfig from environment variables.

        Args:
            env: Dictionary of environment variables (defaults to os.environ)

        Returns:
            NotificationConfig with values from environment
        """
        import os

        if env is None:
            env = dict(os.environ)

        enabled = env.get("NOTIFICATIONS_ENABLED", "false").lower() == "true"

        to_addresses_str = env.get("NOTIFICATION_TO", "")
        to_addresses = (
            [a.strip() for a in to_addresses_str.split(",") if a.strip()]
            if to_addresses_str
            else []
        )

        return cls(
            enabled=enabled,
            smtp_host=env.get("SMTP_HOST", "localhost"),
            smtp_port=int(env.get("SMTP_PORT", "587")),
            smtp_user=env.get("SMTP_USER", ""),
            smtp_password=env.get("SMTP_PASSWORD", ""),
            smtp_use_tls=env.get("SMTP_USE_TLS", "true").lower() == "true",
            from_address=env.get("NOTIFICATION_FROM", "orion@example.com"),
            to_addresses=to_addresses,
            subject_prefix=env.get("NOTIFICATION_SUBJECT_PREFIX", "🎯 OFI Signal"),
        )

    def is_valid(self) -> bool:
        """Check if the configuration is valid for sending notifications.

        Returns:
            True if all required fields are present
        """
        if not self.enabled:
            return False
        if not self.smtp_host:
            return False
        if not self.from_address:
            return False
        if not self.to_addresses:
            return False
        return True
