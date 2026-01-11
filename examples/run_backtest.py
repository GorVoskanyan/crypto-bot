from autotrade.core.backtest import Backtester
from autotrade.strategies.sma_crossover import SMACrossoverStrategy
from autotrade.data.exchange import ExchangeDataFetcher
from autotrade.config import config
import matplotlib.pyplot as plt

def main():
    print("=== Backtesting Mode ===")

    # 1. Fetch Data
    symbol = 'BTC/USDT'
    timeframe = '1d' # Daily candles for faster backtest
    limit = 500 # Past 500 days

    # Use Kraken again for demo stability
    exchange_id = 'kraken'
    print(f"Fetching {limit} candles of {symbol} from {exchange_id}...")

    data_fetcher = ExchangeDataFetcher(exchange_id=exchange_id)
    try:
        data = data_fetcher.fetch_ohlcv(symbol, timeframe, limit=limit)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    print(f"Data fetched: {len(data)} rows.")

    # 2. Run Backtest
    # SMA 20/50 is a common daily strategy
    strategy = SMACrossoverStrategy(short_window=20, long_window=50)

    backtester = Backtester(strategy, initial_balance=10000.0, symbol=symbol)
    backtester.run(data)

    # 3. Report
    metrics = backtester.calculate_metrics()
    print("\n=== Performance Report ===")
    print(f"Total Return: {metrics.get('total_return_pct')}%")
    print(f"Max Drawdown: {metrics.get('max_drawdown_pct')}%")
    print(f"Final Equity: ${metrics.get('final_equity')}")
    print(f"Total Trades: {metrics.get('trade_count')}")

    # 4. Optional: Save Equity Curve
    # In a real SaaP, this would return a JSON for the frontend to chart
    # Here we just print confirmation
    print("\nBacktest complete.")

if __name__ == "__main__":
    main()
