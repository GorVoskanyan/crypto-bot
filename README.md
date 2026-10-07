# AutoTrade-Jules: Algorithmic Trading Bot

## Project Overview
This is a modular trading bot built in Python for Binance Futures. It automates technical analysis strategies using CCXT, WebSocket streaming, dynamic market scanning for high-volatility coins, and dynamic strategy selection (Adaptive Strategy Engine).

## Key Features & Phase 1 Highlights
- **Dynamic Market Scanner (`MarketScanner`):** Automatically scans Binance Futures markets for the Top N USDT pairs with the highest 24h volatility range and liquid volume ($10M+ USDT volume filter).
- **Multi-Symbol Concurrency:** Runs WebSocket streams, orderbook analytics, and strategy engines concurrently for multiple top volatile crypto pairs.
- **Adaptive Strategy Selector (`adaptive` - Default):** Dynamically analyzes market regime (trending via ADX, volatile/ranging via Bollinger Bandwidth) for each coin and delegates execution to the optimal sub-strategy.
- **Confluence Strategy (`confluence`):** Combines Bollinger Bands, RSI, MACD, Volume MA, and ATR dynamic Stop Loss/Take Profit.
- **EMA Trend Ribbon (`ema_trend`):** Follows trends using EMA Ribbon (9, 21, 50, 200) with ADX trend intensity filter.
- **Scalping Strategy (`scalping`):** High-frequency scalping using RSI and orderbook imbalance.
- **SMA Crossover (`sma`):** Golden Cross / Death Cross moving average crossover.

## Environment Configuration Variables
Set these variables in `.env`:
- `ENABLE_SCANNER=true` - Automatically scan and trade top volatile USDT pairs on startup.
- `TOP_SYMBOLS_COUNT=3` - Number of top volatile coins to trade concurrently.
- `MIN_24H_VOLUME_USDT=10000000.0` - Minimum 24h volume threshold ($10M).
- `STRATEGY=adaptive` - Active strategy (`adaptive`, `confluence`, `ema_trend`, `scalping`, `sma`).
- `TIMEFRAME=5m` - Candle timeframe (`1m`, `5m`, `15m`, `1h`).
- `USE_TESTNET=true` - Set `true` for Binance Futures Testnet, `false` for Live mainnet.

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
