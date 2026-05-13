import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Application configuration.
    """
    EXCHANGE_ID = os.getenv("EXCHANGE_ID", "binance")
    API_KEY = os.getenv("EXCHANGE_API_KEY")
    SECRET = os.getenv("EXCHANGE_SECRET")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENV = os.getenv("ENV", "development")
    # Set to True if using Testnet keys, False for Real account
    USE_TESTNET = os.getenv("USE_TESTNET", "true").lower() == "true"

    # Risk Management
    RISK_PERCENT_PER_TRADE = float(os.getenv("RISK_PERCENT_PER_TRADE", "0.01"))  # 1% risk per trade
    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.02"))        # 2% stop loss
    TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.04"))    # 4% take profit

    # Notifications
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

config = Config()
