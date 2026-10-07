# AutoTrade-Jules: Algorithmic Trading Bot

## Project Overview
This is a modular trading bot built in Python for Binance Futures. It automates technical analysis strategies using CCXT, WebSocket streaming, dynamic market scanning for high-volatility coins, adaptive strategy selection, automated risk protection (Break-Even & Trailing Stop), Daily Drawdown circuit breaker, and interactive Telegram control commands.

## Key Features & Phases
- **Dynamic Market Scanner (`MarketScanner`):** Automatically scans Binance Futures markets for the Top N USDT pairs with the highest 24h volatility range and liquid volume ($10M+ USDT volume filter).
- **Multi-Symbol Concurrency:** Runs WebSocket streams, orderbook analytics, and strategy engines concurrently for multiple top volatile crypto pairs.
- **Break-Even & Trailing Stop Protection:**
  - **Break-Even:** When a position reaches +1% profit, the Stop-Loss is automatically moved to the entry price to eliminate risk.
  - **Trailing Stop:** As price moves further in profit, the Stop-Loss dynamically trails behind peak prices by 0.8% to lock in maximum profit.
  - **Precision Formatting:** All SL/TP orders are strictly formatted with Binance symbol `tickSize` and `stepSize` precision.
- **Daily Drawdown Protection (Circuit Breaker):**
  - Tracks daily realized and unrealized PnL against daily starting balance.
  - Automatically pauses new trade execution if daily drawdown hits the threshold (default: `-3%`).
- **Interactive Telegram Bot Commands:**
  - `/status` - Displays live bot status, active symbols, open positions, PnL, and circuit breaker status.
  - `/balance` - Shows current wallet balances.
  - `/topcoins` - Lists currently monitored volatile crypto pairs.
  - `/closeall` - Emergency command to close all active open positions immediately.
  - `/help` - Displays command list.
- **Adaptive Strategy Selector (`adaptive` - Default):** Dynamically analyzes market regime (trending via ADX, volatile/ranging via Bollinger Bandwidth) for each coin and delegates execution to the optimal sub-strategy (`confluence`, `ema_trend`, or `scalping`).

## Environment Configuration Variables
Set these variables in `.env`:
- `ENABLE_SCANNER=true` - Automatically scan and trade top volatile USDT pairs on startup.
- `TOP_SYMBOLS_COUNT=3` - Number of top volatile coins to trade concurrently.
- `MIN_24H_VOLUME_USDT=10000000.0` - Minimum 24h volume threshold ($10M).
- `MAX_DAILY_DRAWDOWN_PCT=0.03` - Maximum daily drawdown percentage before circuit breaker triggers (3%).
- `STRATEGY=adaptive` - Active strategy (`adaptive`, `confluence`, `ema_trend`, `scalping`, `sma`).
- `TIMEFRAME=5m` - Candle timeframe (`1m`, `3m`, `5m`, `15m`, `1h`).
- `USE_TESTNET=true` - Set `true` for Binance Futures Testnet, `false` for Live mainnet.
- `TELEGRAM_TOKEN=` - Your Telegram Bot API Token.
- `TELEGRAM_CHAT_ID=` - Your Authorized Telegram Chat ID.

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
