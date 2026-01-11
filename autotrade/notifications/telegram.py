import requests
import logging
from typing import Optional
from autotrade.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)

class TelegramNotificationProvider(NotificationProvider):
    """
    Sends notifications via Telegram Bot API.
    """

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send(self, message: str):
        """
        Sends a message to the configured Telegram chat.
        """
        if not self.token or not self.chat_id:
            logger.warning("Telegram token or chat_id not configured. Notification skipped.")
            return

        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.debug(f"Notification sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
