import asyncio
import argparse
import pandas as pd
import pandas_ta as ta
import numpy as np
import ccxt
import random
from datetime import datetime
from autotrade.strategies.sma_crossover import SMACrossoverStrategy
from autotrade.strategies.scalping_strategy import ScalpingStrategy
from autotrade.strategies.confluence_strategy import ConfluenceStrategy

def generate_mock_data(symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    """
    Generates realistic synthetic financial data with trends and noise as a fallback.
    """
    print("⚠️ Using synthetic/simulated market data for backtesting...")
    np.random.seed(42)
    base_price = 50000.0 if "BTC" in symbol else 3000.0 if "ETH" in symbol else 100.0
    prices = [base_price]

    # Generate random walk with drift (some overall trend)
    drift = 0.00005
    volatility = 0.0015

    for _ in range(limit - 1):
        change = prices[-1] * (drift + volatility * np.random.randn())
        prices.append(max(prices[-1] + change, 0.01))

    dates = pd.date_range(end=datetime.now(), periods=limit, freq='1min')

    df = pd.DataFrame(index=dates)
    df['open'] = prices
    df['high'] = [p * (1 + abs(np.random.randn()) * 0.0005) for p in prices]
    df['low'] = [p * (1 - abs(np.random.randn()) * 0.0005) for p in prices]
    df['close'] = [random.uniform(l, h) for l, h in zip(df['low'], df['high'])]
    df['volume'] = [random.uniform(10, 100) for _ in range(limit)]
    df['timestamp'] = df.index.astype(np.int64) // 10**6

    # Clean high/low relationship
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)

    return df.reset_index(drop=True)

async def fetch_historical_data(symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    """
    Fetches real historical candle data from Binance using CCXT.
    Falls back to mock data if exchange API is unreachable.
    """
    try:
        print(f"📡 Fetching historical data for {symbol} ({timeframe}) from Binance...")
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        ohlcv = exchange.fetch_ohlcv(symbol.replace('/', ''), timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        print(f"✅ Successfully fetched {len(df)} candles.")
        return df
    except Exception as e:
        print(f"❌ Failed to fetch data from Binance: {e}")
        return generate_mock_data(symbol, timeframe, limit)

async def run_backtest(strategy_name: str, symbol: str, timeframe: str, limit: int):
    # 1. Fetch data
    df = await fetch_historical_data(symbol, timeframe, limit)

    # 2. Instantiate strategy
    if strategy_name.lower() == 'sma':
        print("📈 Selected Strategy: Simple Moving Average (SMA) Crossover")
        strategy = SMACrossoverStrategy(short_window=5, long_window=20)
    elif strategy_name.lower() == 'confluence':
        print("🛡️ Selected Strategy: Multi-Indicator Confluence Strategy (BB + RSI + MACD + Vol + ATR)")
        strategy = ConfluenceStrategy()
    else:
        print("⚡ Selected Strategy: High-Frequency Scalping Strategy")
        strategy = ScalpingStrategy(rsi_period=14, rsi_overbought=70, rsi_oversold=30, atr_period=14)

    # 3. Simulate Backtest
    initial_balance = 10000.0
    balance = initial_balance
    position = None # None, 'long', or 'short'
    entry_price = 0.0
    position_amount = 0.0
    sl_price = 0.0
    tp_price = 0.0
    leverage = 10 # standard leverage
    fee_rate = 0.0004 # 0.04% futures fee

    trades = []
    equity_curve = [initial_balance]

    # Start simulating candles
    # We need enough history to calculate indicators, so we start loop from 30
    for i in range(30, len(df)):
        current_data = df.iloc[:i+1].copy()
        row = current_data.iloc[-1]
        current_price = row['close']

        # Check active position exit first
        if position:
            closed = False
            exit_price = current_price
            exit_reason = "Signal"

            # Check Stop Loss / Take Profit hits
            if position == 'long':
                if row['low'] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "Stop Loss 🛑"
                    closed = True
                elif row['high'] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "Take Profit 🎯"
                    closed = True
            elif position == 'short':
                if row['high'] >= sl_price:
                    exit_price = sl_price
                    exit_reason = "Stop Loss 🛑"
                    closed = True
                elif row['low'] <= tp_price:
                    exit_price = tp_price
                    exit_reason = "Take Profit 🎯"
                    closed = True

            if closed:
                # Calculate PnL
                entry_value = entry_price * position_amount
                exit_value = exit_price * position_amount

                # Buy low, sell high for long; sell high, buy low for short
                if position == 'long':
                    pnl = exit_value - entry_value
                else:
                    pnl = entry_value - exit_value

                # Subtract fees
                entry_fee = entry_value * fee_rate
                exit_fee = exit_value * fee_rate
                total_fees = entry_fee + exit_fee
                net_pnl = pnl - total_fees

                balance += net_pnl

                trades.append({
                    'type': position.upper(),
                    'entry_time': current_data.index[-1], # placeholder
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'net_pnl': net_pnl,
                    'fees': total_fees,
                    'reason': exit_reason,
                    'balance': balance
                })

                print(f"🚪 Closed {position.upper()} | Entry: {entry_price:.2f} | Exit: {exit_price:.2f} ({exit_reason}) | Net PnL: {net_pnl:+.2f} USDT | Balance: {balance:.2f} USDT")
                position = None
                position_amount = 0.0

        # If no active position, look for entry signals
        if not position:
            # For ScalpingStrategy, simulate random yet slightly biased orderbook imbalance to confirm entries
            orderbook = None
            if strategy_name.lower() == 'scalping':
                # Generate high-imbalance orderbook to simulate ticks
                # If close > open (bullish), bid volume is larger
                # If close < open (bearish), ask volume is larger
                bullish = row['close'] >= row['open']
                bids_qty = 50.0 if bullish else 10.0
                asks_qty = 10.0 if bullish else 50.0
                orderbook = {
                    'bids': [[current_price * 0.999, bids_qty]],
                    'asks': [[current_price * 1.001, asks_qty]],
                    'timestamp': int(row['timestamp'])
                }

            signal = await strategy.analyze(current_data, orderbook)
            action = signal.get('action')

            if action in ['buy', 'sell']:
                # Risk parameters
                sl_pct = signal.get('sl_pct', 0.02)
                tp_pct = signal.get('tp_pct', 0.04)

                entry_price = current_price
                position = 'long' if action == 'buy' else 'short'

                # Position sizing (1% risk)
                risk_amount = balance * 0.01
                sl_dist = entry_price * sl_pct
                position_amount = risk_amount / sl_dist

                # Limit size by leverage limits (80% of max margin)
                max_leverage_amount = (balance * leverage * 0.8) / entry_price
                position_amount = min(position_amount, max_leverage_amount)

                # Stop loss and take profit values
                if position == 'long':
                    sl_price = entry_price * (1 - sl_pct)
                    tp_price = entry_price * (1 + tp_pct)
                else:
                    sl_price = entry_price * (1 + sl_pct)
                    tp_price = entry_price * (1 - tp_pct)

                print(f"🚀 Open {position.upper()} @ {entry_price:.2f} | SL: {sl_price:.2f} | TP: {tp_price:.2f} | Size: {position_amount:.4f} units")

        equity_curve.append(balance)

    # --- Performance Report ---
    print("\n" + "="*50)
    print("📊 BACKTEST PERFORMANCE REPORT (ԲԵՔԹԵՍԹԻ ՀԱՇՎԵՏՎՈՒԹՅՈՒՆ)")
    print("="*50)

    total_trades = len(trades)
    winning_trades = [t for t in trades if t['net_pnl'] > 0]
    losing_trades = [t for t in trades if t['net_pnl'] <= 0]

    total_win = sum([t['net_pnl'] for t in winning_trades])
    total_loss = sum([abs(t['net_pnl']) for t in losing_trades])
    net_profit = balance - initial_balance
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0
    profit_factor = (total_win / total_loss) if total_loss > 0 else float('inf')

    # Calculate Max Drawdown
    equity_series = pd.Series(equity_curve)
    cum_max = equity_series.cummax()
    drawdowns = (equity_series - cum_max) / cum_max * 100
    max_dd = drawdowns.min()

    print(f"Strategy (Ռազմավարություն):       {strategy_name.upper()}")
    print(f"Symbol (Զույգ):                 {symbol}")
    print(f"Timeframe (Ժամանակացույց):       {timeframe}")
    print(f"Total Candles (Մոմեր):          {len(df)}")
    print(f"Initial Balance (Սկզբն. հաշվեկշիռ): ${initial_balance:,.2f} USDT")
    print(f"Final Balance (Վերջն. հաշվեկշիռ):   ${balance:,.2f} USDT")
    print(f"Net Profit (Զուտ Շահույթ):        ${net_profit:,.2f} USDT ({net_profit/initial_balance*100:+.2f}%)")
    print(f"Total Trades (Գործարքներ):       {total_trades}")
    print(f"Win Rate (Հաղթող %):            {win_rate:.2f}%")
    print(f"Winning Trades (Հաղթողներ):     {len(winning_trades)}")
    print(f"Losing Trades (Պարտվողներ):      {len(losing_trades)}")
    print(f"Profit Factor (Շահույթի Գործակից): {profit_factor:.2f}")
    print(f"Max Drawdown (Մաքս. Անկում):      {max_dd:.2f}%")
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoTrade Backtesting Engine")
    parser.add_argument('--strategy', type=str, default='confluence', choices=['sma', 'scalping', 'confluence'], help="Strategy name (sma, scalping, confluence)")
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help="Trading symbol (e.g. BTC/USDT)")
    parser.add_argument('--timeframe', type=str, default='1m', help="Timeframe (1m, 5m, 15m, 1h, 1d)")
    parser.add_argument('--limit', type=type(1), default=500, help="Number of candles to load")

    args = parser.parse_args()
    asyncio.run(run_backtest(args.strategy, args.symbol, args.timeframe, args.limit))
