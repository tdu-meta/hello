"""Notification service module."""

from orion.notifications.models import NotificationConfig
from orion.notifications.service import NotificationService

__all__ = ["NotificationService", "NotificationConfig"]
