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

    # Strategy & Multi-Symbol Settings
    TRADING_SYMBOL = os.getenv("TRADING_SYMBOL", "BTC/USDT")  # Fallback single symbol
    TIMEFRAME = os.getenv("TIMEFRAME", "5m")
    STRATEGY = os.getenv("STRATEGY", "adaptive").lower()  # adaptive, confluence, ema_trend, scalping, sma

    # Dynamic Market Scanner Settings
    ENABLE_SCANNER = os.getenv("ENABLE_SCANNER", "true").lower() == "true"
    TOP_SYMBOLS_COUNT = int(os.getenv("TOP_SYMBOLS_COUNT", "3"))  # Number of volatile coins to trade concurrently
    MIN_24H_VOLUME_USDT = float(os.getenv("MIN_24H_VOLUME_USDT", "10000000.0"))  # $10M min volume filter

    # Risk Management & Protection Limits
    RISK_PERCENT_PER_TRADE = float(os.getenv("RISK_PERCENT_PER_TRADE", "0.01"))  # 1% risk per trade
    MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", "10"))              # 10x max leverage
    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.02"))        # 2% stop loss
    TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.04"))    # 4% take profit
    MAX_DAILY_DRAWDOWN_PCT = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "0.03"))  # 3% max daily drawdown limit
    MAX_FUNDING_RATE = float(os.getenv("MAX_FUNDING_RATE", "0.002"))  # 0.2% max funding rate threshold

    # Notifications & Interactive Telegram Commands
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

config = Config()
