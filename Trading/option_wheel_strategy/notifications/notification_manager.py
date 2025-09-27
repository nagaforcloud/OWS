"""
Notification manager for the Option Wheel Strategy.
"""
import requests
import logging
from typing import Optional

from ..config.config import OptionWheelConfig


class NotificationManager:
    """Handles sending notifications for important events."""
    
    def __init__(self, config: OptionWheelConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def send_notification(self, title: str, message: str, priority: str = "info") -> None:
        """Send notification via webhook or other means."""
        if not self.config.enable_notifications:
            return
            
        try:
            if self.config.notification_webhook_url:
                payload = {
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                }
                response = requests.post(
                    self.config.notification_webhook_url,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
                self.logger.info(f"Notification sent: {title}")
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")