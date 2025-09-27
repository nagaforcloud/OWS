import requests
import json
import logging
from typing import Dict, Any, Optional
from utils.logging_utils import get_logger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = get_logger(__name__)

class NotificationManager:
    """
    Manages sending notifications via multiple channels for trading events
    """
    
    def __init__(self, webhook_url: Optional[str] = None, notification_type: str = "webhook"):
        """
        Initialize the notification manager
        
        Args:
            webhook_url: Optional webhook URL for sending notifications
            notification_type: Type of notifications ("webhook", "telegram", "slack", "email")
        """
        self.webhook_url = webhook_url
        self.notification_type = notification_type.lower()
        self.enabled = bool(webhook_url)
        
        # Additional connection parameters for different channels
        self.telegram_bot_token = None
        self.telegram_chat_id = None
        self.smtp_server = None
        self.smtp_port = None
        self.smtp_username = None
        self.smtp_password = None
        self.sender_email = None
        self.recipient_email = None
        
        if not self.enabled:
            logger.warning("Notifications are disabled - no webhook URL provided")
        
        # Load additional config from environment
        import os
        if self.notification_type == "telegram":
            self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
            self.enabled = self.telegram_bot_token is not None and self.telegram_chat_id is not None
        elif self.notification_type == "email":
            self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
            self.smtp_username = os.getenv('SMTP_USERNAME')
            self.smtp_password = os.getenv('SMTP_PASSWORD')
            self.sender_email = os.getenv('SENDER_EMAIL')
            self.recipient_email = os.getenv('RECIPIENT_EMAIL')
            self.enabled = all([self.smtp_username, self.smtp_password, self.sender_email, self.recipient_email])
    
    def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        """
        Send a notification via the configured channel
        
        Args:
            title: Title of the notification
            message: Content of the notification
            level: Severity level (info, warning, error)
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Skipping notification - not enabled")
            return False
        
        try:
            if self.notification_type == "webhook":
                return self._send_webhook_notification(title, message, level)
            elif self.notification_type == "telegram":
                return self._send_telegram_notification(title, message, level)
            elif self.notification_type == "slack":
                return self._send_slack_notification(title, message, level)
            elif self.notification_type == "email":
                return self._send_email_notification(title, message, level)
            else:
                logger.warning(f"Unsupported notification type: {self.notification_type}")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error sending notification: {str(e)}")
            return False

    def _send_webhook_notification(self, title: str, message: str, level: str) -> bool:
        """Send notification via webhook"""
        if not self.webhook_url:
            logger.error("Webhook URL not configured")
            return False
            
        payload = self._create_payload(title, message, level)
        
        if not payload:
            return False
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Webhook notification sent successfully: {title}")
                return True
            else:
                logger.error(f"Failed to send webhook notification: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending webhook notification: {str(e)}")
            return False

    def _send_telegram_notification(self, title: str, message: str, level: str) -> bool:
        """Send notification via Telegram bot"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.error("Telegram bot token or chat ID not configured")
            return False
            
        try:
            telegram_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            telegram_message = f"<b>{title}</b>\n\n{message}"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': telegram_message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(
                telegram_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Telegram notification sent successfully: {title}")
                return True
            else:
                logger.error(f"Failed to send Telegram notification: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
            return False

    def _send_slack_notification(self, title: str, message: str, level: str) -> bool:
        """Send notification via Slack webhook"""
        if not self.webhook_url:
            logger.error("Slack webhook URL not configured")
            return False
            
        try:
            # Slack webhook payload format
            payload = {
                'text': f"[{level.upper()}] {title}",
                'blocks': [
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': f'*{title}*\n{message}'
                        }
                    }
                ]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack notification sent successfully: {title}")
                return True
            else:
                logger.error(f"Failed to send Slack notification: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            return False

    def _send_email_notification(self, title: str, message: str, level: str) -> bool:
        """Send notification via email"""
        if not all([self.smtp_username, self.smtp_password, self.sender_email, self.recipient_email]):
            logger.error("Email configuration incomplete")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['Subject'] = f"[{level.upper()}] {title}"
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            
            email_body = f"""
            <html>
                <body>
                    <h2>{title}</h2>
                    <p>{message}</p>
                    <hr>
                    <p><small>Options Wheel Strategy Bot Notification</small></p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(email_body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, self.recipient_email, text)
            server.quit()
            
            logger.info(f"Email notification sent successfully: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False

    def _create_payload(self, title: str, message: str, level: str) -> Optional[Dict[str, Any]]:
        """
        Create the appropriate payload based on the webhook URL type
        
        Args:
            title: Title of the notification
            message: Content of the notification
            level: Severity level
            
        Returns:
            Optional[Dict]: Payload dict or None if unsupported
        """
        # Check if it's a Discord webhook
        if self.webhook_url and "discord" in self.webhook_url.lower():
            color_map = {
                "info": 3447003,    # Blue
                "warning": 16763904, # Yellow
                "error": 15548917    # Red
            }
            
            return {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": color_map.get(level, 3447003),
                    "timestamp": self._get_iso_timestamp()
                }]
            }
        
        # Default to a generic format (works for many webhook types)
        return {
            "text": f"[{level.upper()}] {title}: {message}"
        }
    
    def _get_iso_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def notify_order_placed(self, order_id: str, symbol: str, quantity: int, price: float, 
                           transaction_type: str) -> bool:
        """Notify when an order is placed"""
        message = f"Order placed: {transaction_type} {quantity} of {symbol} at {price:.2f}"
        return self.send_notification(f"Order Placed: {order_id}", message, "info")
    
    def notify_order_completed(self, order_id: str, symbol: str, quantity: int, 
                              average_price: float, transaction_type: str) -> bool:
        """Notify when an order is completed"""
        message = f"Order completed: {transaction_type} {quantity} of {symbol} at {average_price:.2f}"
        return self.send_notification(f"Order Completed: {order_id}", message, "info")
    
    def notify_order_cancelled(self, order_id: str, symbol: str) -> bool:
        """Notify when an order is cancelled"""
        message = f"Order cancelled for {symbol}"
        return self.send_notification(f"Order Cancelled: {order_id}", message, "warning")
    
    def notify_position_closed(self, symbol: str, pnl: float) -> bool:
        """Notify when a position is closed"""
        level = "info" if pnl >= 0 else "warning"
        message = f"Position closed for {symbol} with P&L: {pnl:.2f}"
        return self.send_notification("Position Closed", message, level)
    
    def notify_profit_target_hit(self, symbol: str, pnl: float) -> bool:
        """Notify when profit target is hit"""
        message = f"Profit target hit for {symbol}, P&L: {pnl:.2f}"
        return self.send_notification("Profit Target Hit", message, "info")
    
    def notify_stop_loss_hit(self, symbol: str, pnl: float) -> bool:
        """Notify when stop loss is hit"""
        message = f"Stop loss hit for {symbol}, P&L: {pnl:.2f}"
        return self.send_notification("Stop Loss Hit", message, "warning")
    
    def notify_system_event(self, event_type: str, details: str) -> bool:
        """Notify for general system events"""
        return self.send_notification(f"System Event: {event_type}", details, "info")
    
    def notify_error(self, error_type: str, details: str) -> bool:
        """Notify for errors"""
        return self.send_notification(f"Error: {error_type}", details, "error")
    
    def notify_daily_summary(self, trades_count: int, pnl: float, positions_count: int) -> bool:
        """Notify daily trading summary"""
        level = "info" if pnl >= 0 else "warning"
        message = f"Daily Summary: {trades_count} trades, P&L: {pnl:.2f}, {positions_count} positions open"
        return self.send_notification("Daily Summary", message, level)
    
    def notify_risk_limit_breach(self, limit_type: str, current_value: float, threshold: float) -> bool:
        """Notify when a risk limit is breached"""
        message = f"{limit_type} limit breached: Current {current_value:.2f}, Threshold {threshold:.2f}"
        return self.send_notification("Risk Limit Breach", message, "error")


# Example usage
if __name__ == "__main__":
    # Example with a placeholder webhook URL
    nm = NotificationManager(webhook_url="https://example.com/webhook")
    
    # Test various notifications
    nm.notify_order_placed("12345", "TCS", 150, 3450.50, "SELL")
    nm.notify_order_completed("12345", "TCS", 150, 3450.50, "SELL")
    nm.notify_position_closed("TCS", 1500.75)
    nm.notify_profit_target_hit("TCS", 2100.00)
    nm.notify_stop_loss_hit("INFY", -1800.50)
    nm.notify_error("API Error", "KiteConnect API unavailable")
    nm.notify_risk_limit_breach("Daily Loss", 5500.0, 5000.0)