from autotrade.notifications.telegram import TelegramNotificationProvider
from autotrade.config import config
import os

def main():
    print("=== Test Notification ===")

    # Allow override via env vars for this script if not in config
    token = config.TELEGRAM_TOKEN or os.getenv("TEST_TELEGRAM_TOKEN")
    chat_id = config.TELEGRAM_CHAT_ID or os.getenv("TEST_TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Error: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set.")
        print("Set them in .env or environment variables.")
        return

    print(f"Sending test message to chat {chat_id}...")

    provider = TelegramNotificationProvider(token, chat_id)
    provider.send("🔔 This is a test notification from AutoTrade-Jules!")

    print("Done. Check your Telegram.")

if __name__ == "__main__":
    main()
