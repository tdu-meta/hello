"""Notification service for sending alerts.

This module provides the NotificationService class for sending email alerts
when screening finds matching trading opportunities.
"""

import asyncio
from email.message import EmailMessage
from smtplib import SMTP, SMTPException

from orion.core.screener import ScreeningResult
from orion.notifications.models import NotificationConfig
from orion.utils.logging import get_logger

logger = get_logger(__name__, component="NotificationService")


class NotificationService:
    """Service for sending email notifications for trading signals.

    The service sends HTML-formatted email alerts when stocks match the
    screening criteria, including all relevant details about the signal
    and recommended option contracts.

    Example:
        >>> config = NotificationConfig.from_env()
        >>> service = NotificationService(config)
        >>> await service.send_alert(screening_result)
    """

    def __init__(self, config: NotificationConfig) -> None:
        """Initialize the NotificationService.

        Args:
            config: Notification configuration
        """
        self.config = config
        self._logger = logger

    def is_enabled(self) -> bool:
        """Check if notifications are enabled and configured.

        Returns:
            True if notifications can be sent
        """
        return self.config.is_valid()

    async def send_alert(self, result: ScreeningResult) -> bool:
        """Send an email alert for a screening result.

        Args:
            result: Screening result to send alert for

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_enabled():
            self._logger.debug(
                "notifications_disabled",
                reason="Configuration not valid or notifications disabled",
            )
            return False

        if not result.matches:
            self._logger.debug(
                "skipping_notification",
                reason="Result does not match strategy",
                symbol=result.symbol,
            )
            return False

        try:
            message = self._build_email_message(result)

            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._send_email_sync, message)

            if success:
                self._logger.info(
                    "notification_sent",
                    symbol=result.symbol,
                    recipients=len(self.config.to_addresses),
                )
            else:
                self._logger.warning(
                    "notification_send_failed",
                    symbol=result.symbol,
                )

            return success

        except Exception as e:
            self._logger.error(
                "notification_error",
                symbol=result.symbol,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def send_batch_alerts(self, results: list[ScreeningResult]) -> int:
        """Send alerts for multiple screening results.

        Args:
            results: List of screening results

        Returns:
            Number of alerts sent successfully
        """
        if not results:
            return 0

        # Filter to matches only
        matches = [r for r in results if r.matches]

        if not matches:
            self._logger.debug("no_matches_to_notify")
            return 0

        # If there's only one match, send individual alerts
        if len(matches) == 1:
            return 1 if await self.send_alert(matches[0]) else 0

        # For multiple matches, send a summary email
        try:
            message = self._build_summary_email(matches)

            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._send_email_sync, message)

            if success:
                self._logger.info(
                    "batch_notification_sent",
                    count=len(matches),
                )
                return len(matches)
            else:
                self._logger.warning("batch_notification_send_failed")
                return 0

        except Exception as e:
            self._logger.error(
                "batch_notification_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    def _build_email_message(self, result: ScreeningResult) -> EmailMessage:
        """Build an email message for a single screening result.

        Args:
            result: Screening result to build message for

        Returns:
            Formatted EmailMessage
        """
        message = EmailMessage()
        message["From"] = self.config.from_address
        message["To"] = ", ".join(self.config.to_addresses)
        message["Subject"] = f"{self.config.subject_prefix}: {result.symbol}"

        message.set_content(self._build_plain_text_body(result), subtype="plain")
        message.add_alternative(self._build_html_body(result), subtype="html")

        return message

    def _build_summary_email(self, results: list[ScreeningResult]) -> EmailMessage:
        """Build a summary email for multiple screening results.

        Args:
            results: List of screening results to build message for

        Returns:
            Formatted EmailMessage
        """
        message = EmailMessage()
        message["From"] = self.config.from_address
        message["To"] = ", ".join(self.config.to_addresses)
        message["Subject"] = f"{self.config.subject_prefix}: {len(results)} New Matches"

        message.set_content(self._build_summary_plain_text(results), subtype="plain")
        message.add_alternative(self._build_summary_html(results), subtype="html")

        return message

    def _build_html_body(self, result: ScreeningResult) -> str:
        """Build HTML email body for a single result.

        Args:
            result: Screening result

        Returns:
            HTML formatted email body
        """
        signal_strength_pct = result.signal_strength * 100

        # Build conditions list HTML
        conditions_html = "<ul>"
        for condition in result.conditions_met:
            conditions_html += f'<li style="color: #10b981;">✓ {condition}</li>'
        for condition in result.conditions_missed:
            conditions_html += f'<li style="color: #ef4444;">✗ {condition}</li>'
        conditions_html += "</ul>"

        # Build option recommendation HTML if available
        option_html = "<p>No option recommendation available.</p>"
        if result.option_recommendation:
            opt = result.option_recommendation
            option_html = f"""
            <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin-top: 15px;">
                <h3 style="margin-top: 0; color: #1f2937;">📊 Option Recommendation</h3>
                <p><strong>Contract:</strong> {opt.symbol}</p>
                <p><strong>Strike:</strong> ${opt.strike:.2f}</p>
                <p><strong>Expiration:</strong> {opt.expiration}</p>
                <p><strong>Mid Price:</strong> ${opt.mid_price:.2f}</p>
                <p><strong>Annualized Yield:</strong> <span style="color: #10b981; font-weight: bold;">{opt.premium_yield:.1%}</span></p>
                <p><strong>Volume:</strong> {opt.volume}</p>
                <p><strong>Open Interest:</strong> {opt.open_interest}</p>
                {f'<p><strong>IV:</strong> {opt.implied_volatility:.1%}</p>' if opt.implied_volatility else ''}
                {f'<p><strong>Delta:</strong> {opt.delta:.3f}</p>' if opt.delta is not None else ''}
                <p style="font-size: 0.9em; color: #6b7280; margin-top: 10px;"><em>{opt.reason}</em></p>
            </div>
            """

        # Build quote HTML if available
        quote_html = ""
        if result.quote:
            q = result.quote
            change_val = float(q.change) if q.change else 0.0
            change_color = "#10b981" if q.change and q.change > 0 else "#ef4444"
            change_symbol = "+" if q.change and q.change > 0 else ""
            change_pct = q.change_percent if q.change_percent is not None else 0.0
            quote_html = f"""
            <div style="margin-bottom: 15px;">
                <p><strong>Current Price:</strong> ${float(q.price):.2f}</p>
                <p><strong>Change:</strong> <span style="color: {change_color};">{change_symbol}{change_val:.2f} ({change_pct:.2f}%)</span></p>
                <p><strong>Volume:</strong> {q.volume:,}</p>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; line-height: 1.6; color: #1f2937; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .signal-strength {{ font-size: 48px; font-weight: bold; }}
                .conditions {{ background-color: #f9fafb; padding: 15px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">{self.config.subject_prefix}</h1>
                    <p style="margin: 5px 0 0 0; font-size: 18px;">{result.symbol}</p>
                </div>

                <div style="text-align: center; margin-bottom: 20px;">
                    <div class="signal-strength" style="color: #{self._strength_color(result.signal_strength)};">{signal_strength_pct:.0f}%</div>
                    <p style="color: #6b7280; margin-top: 5px;">Signal Strength</p>
                </div>

                {quote_html}

                <div class="conditions">
                    <h3 style="margin-top: 0;">Conditions</h3>
                    {conditions_html}
                </div>

                {option_html}

                <p style="font-size: 12px; color: #9ca3af; margin-top: 30px; text-align: center;">
                    Generated by Orion Trading Signals • {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </body>
        </html>
        """

        return html

    def _build_summary_html(self, results: list[ScreeningResult]) -> str:
        """Build HTML email body for multiple results.

        Args:
            results: List of screening results

        Returns:
            HTML formatted email body
        """
        rows_html = ""
        for result in results:
            strength_pct = result.signal_strength * 100
            price = f"${float(result.quote.price):.2f}" if result.quote else "N/A"
            rows_html += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 12px;"><strong>{result.symbol}</strong></td>
                <td style="padding: 12px;">{price}</td>
                <td style="padding: 12px;"><span style="color: #{self._strength_color(result.signal_strength)}; font-weight: bold;">{strength_pct:.0f}%</span></td>
                <td style="padding: 12px;">{", ".join(result.conditions_met)}</td>
                <td style="padding: 12px;">{f"{result.option_recommendation.premium_yield:.1%}" if result.option_recommendation else "N/A"}</td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background-color: #f3f4f6; padding: 12px; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">{self.config.subject_prefix}: {len(results)} New Matches</h1>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Price</th>
                            <th>Signal</th>
                            <th>Conditions Met</th>
                            <th>Yield</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <p style="font-size: 12px; color: #9ca3af; margin-top: 30px; text-align: center;">
                    Generated by Orion Trading Signals
                </p>
            </div>
        </body>
        </html>
        """

        return html

    def _build_plain_text_body(self, result: ScreeningResult) -> str:
        """Build plain text email body.

        Args:
            result: Screening result

        Returns:
            Plain text email body
        """
        lines = [
            f"{self.config.subject_prefix}: {result.symbol}",
            "",
            f"Signal Strength: {result.signal_strength * 100:.0f}%",
            "",
        ]

        if result.quote:
            q = result.quote
            change = float(q.change) if q.change else 0.0
            change_pct = q.change_percent if q.change_percent is not None else 0.0
            lines.extend(
                [
                    f"Current Price: ${float(q.price):.2f}",
                    f"Change: {change:.2f} ({change_pct:.2f}%)",
                    f"Volume: {q.volume:,}",
                    "",
                ]
            )

        lines.append("Conditions Met:")
        for condition in result.conditions_met:
            lines.append(f"  ✓ {condition}")

        if result.conditions_missed:
            lines.append("Conditions Missed:")
            for condition in result.conditions_missed:
                lines.append(f"  ✗ {condition}")

        if result.option_recommendation:
            opt = result.option_recommendation
            lines.extend(
                [
                    "",
                    "Option Recommendation:",
                    f"  Contract: {opt.symbol}",
                    f"  Strike: ${opt.strike:.2f}",
                    f"  Expiration: {opt.expiration}",
                    f"  Mid Price: ${opt.mid_price:.2f}",
                    f"  Annualized Yield: {opt.premium_yield:.1%}",
                    f"  Volume: {opt.volume}",
                    f"  Open Interest: {opt.open_interest}",
                    f"  Reason: {opt.reason}",
                ]
            )

        lines.append(f"\nGenerated: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)

    def _build_summary_plain_text(self, results: list[ScreeningResult]) -> str:
        """Build plain text summary email.

        Args:
            results: List of screening results

        Returns:
            Plain text email body
        """
        lines = [
            f"{self.config.subject_prefix}: {len(results)} New Matches",
            "",
        ]

        for result in results:
            lines.append(f"\n{result.symbol}")
            lines.append(f"  Signal: {result.signal_strength * 100:.0f}%")
            if result.quote:
                lines.append(f"  Price: ${float(result.quote.price):.2f}")
            lines.append(f"  Conditions: {', '.join(result.conditions_met)}")
            if result.option_recommendation:
                lines.append(f"  Yield: {result.option_recommendation.premium_yield:.1%}")

        return "\n".join(lines)

    def _strength_color(self, strength: float) -> str:
        """Get color for signal strength.

        Args:
            strength: Signal strength (0.0 to 1.0)

        Returns:
            Hex color code
        """
        if strength >= 0.8:
            return "10b981"  # Green
        elif strength >= 0.5:
            return "f59e0b"  # Orange
        else:
            return "ef4444"  # Red

    def _send_email_sync(self, message: EmailMessage) -> bool:
        """Send email message synchronously.

        Args:
            message: EmailMessage to send

        Returns:
            True if sent successfully
        """
        try:
            with SMTP(self.config.smtp_host, self.config.smtp_port, timeout=30) as server:
                if self.config.smtp_use_tls:
                    server.starttls()

                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)

                server.send_message(message)

            return True

        except SMTPException as e:
            self._logger.error(
                "smtp_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
        except Exception as e:
            self._logger.error(
                "email_send_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
