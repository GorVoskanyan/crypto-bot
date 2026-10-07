import requests
import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from autotrade.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)

class TelegramNotificationProvider(NotificationProvider):
    """
    Sends notifications and listens for interactive commands via Telegram Bot API.
    """

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = str(chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.command_handlers: Dict[str, Callable] = {}
        self.last_update_id = 0
        self.polling_task: Optional[asyncio.Task] = None

    def send(self, message: str):
        if not self.token or not self.chat_id:
            logger.warning("Telegram token or chat_id not configured. Notification skipped.")
            return

        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)
            response.raise_for_status()
            logger.debug(f"Notification sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    def register_command(self, command: str, handler: Callable):
        """Registers a command callback (e.g., /status, /balance, /closeall)."""
        clean_cmd = command.strip().lower()
        if not clean_cmd.startswith('/'):
            clean_cmd = f"/{clean_cmd}"
        self.command_handlers[clean_cmd] = handler

    async def poll_updates_loop(self):
        """Asynchronously polls Telegram for user commands."""
        if not self.token:
            return

        logger.info("📱 Telegram Command Listener started...")
        while True:
            try:
                # Use asyncio.to_thread for blocking requests.get call
                url = f"{self.api_url}/getUpdates?offset={self.last_update_id + 1}&timeout=10"
                resp = await asyncio.to_thread(requests.get, url, timeout=12)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('ok') and data.get('result'):
                        for update in data['result']:
                            self.last_update_id = update['update_id']
                            message = update.get('message', {})
                            text = message.get('text', '').strip()
                            sender_chat_id = str(message.get('chat', {}).get('id', ''))

                            # Security: Only process commands from authorized chat_id
                            if self.chat_id and sender_chat_id != self.chat_id:
                                continue

                            if text.startswith('/'):
                                cmd = text.split()[0].lower()
                                if cmd in self.command_handlers:
                                    logger.info(f"📱 Received Telegram Command: {cmd}")
                                    reply = await self.command_handlers[cmd]()
                                    if reply:
                                        self.send(reply)
                                else:
                                    self.send(f"❓ Unknown command: {cmd}\nAvailable commands: {', '.join(self.command_handlers.keys())}")
            except Exception as e:
                logger.debug(f"Telegram polling exception: {e}")

            await asyncio.sleep(3)

    def start_command_listener(self):
        """Starts background updates polling task."""
        if self.token and self.chat_id and not self.polling_task:
            self.polling_task = asyncio.create_task(self.poll_updates_loop())
