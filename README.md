# AutoTrade-Jules: Algorithmic Trading Bot

## Project Overview
This is a modular trading bot built in Python. The goal is to automate technical analysis strategies using the CCXT library for exchange integration.

## Tech Stack
- **Language:** Python 3.11+
- **Key Libraries:** `ccxt`, `pandas`, `pandas_ta`, `python-dotenv`
- **Infrastructure:** Designed to run asynchronously as a background agent.

## Core Components (To be implemented)
1. **Data Fetcher:** Retrieves real-time OHLCV data from exchanges.
2. **Strategy Engine:** Implements technical indicators (SMA, RSI, etc.).
3. **Paper Trading Module:** A simulation mode to test strategies without real funds.
4. **Risk Manager:** Implements Stop-Loss and Take-Profit logic.

## Guidelines for Jules (AI Agent)
- Follow PEP 8 coding standards.
- Write modular code: logic, API interaction, and configuration should be separate.
- Every new feature must include basic docstrings.
- **Safety First:** Never hardcode API keys. Use `.env` files.
