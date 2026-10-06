# AutoTrade-Jules: Algorithmic Trading Bot

## Project Overview
This is a modular trading bot built in Python for Binance Futures. It automates technical analysis strategies using CCXT, WebSocket streaming, and dynamic strategy selection (Adaptive Strategy Engine).

## Tech Stack
- **Language:** Python 3.11+
- **Package Manager:** `uv` (Fast Python package installer)
- **Key Libraries:** `ccxt`, `pandas`, `pandas_ta`, `python-binance`, `pydantic`, `python-dotenv`
- **Infrastructure:** Docker & Docker Compose support, designed to run asynchronously as a background service.

## Strategies Available
1. **Adaptive Strategy Selector (`adaptive` - Default):** Dynamically analyzes market regime (trending via ADX, volatile/ranging via Bollinger Bandwidth) for any coin and delegates execution to the optimal sub-strategy.
2. **Confluence Strategy (`confluence`):** Combines Bollinger Bands, RSI, MACD, Volume MA, and ATR dynamic Stop Loss/Take Profit.
3. **EMA Trend Ribbon (`ema_trend`):** Follows trends using EMA Ribbon (9, 21, 50, 200) with ADX trend intensity filter.
4. **Scalping Strategy (`scalping`):** High-frequency scalping using RSI and orderbook imbalance.
5. **SMA Crossover (`sma`):** Golden Cross / Death Cross moving average crossover.

## Quick Start with `uv`

```bash
# Install dependencies using uv (ultra fast)
uv pip install --system -r requirements.txt

# Run backtest tool
python backtest.py --strategy adaptive --symbol BTC/USDT --timeframe 5m

# Run trading bot
python main.py
```

## Running with Docker / Docker Compose

```bash
# 1. Copy environment template and fill in API credentials
cp .env.example .env

# 2. Build and start the trading bot in background
docker compose up -d --build

# 3. View live logs
docker compose logs -f

# 4. Stop the bot
docker compose down
```

## Guidelines for Jules (AI Agent)
- Follow PEP 8 coding standards.
- Write modular code: logic, API interaction, and configuration should be separate.
- Every new feature must include basic docstrings.
- **Safety First:** Never hardcode API keys. Use `.env` files.
