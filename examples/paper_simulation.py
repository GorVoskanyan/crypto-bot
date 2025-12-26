from autotrade.execution.paper import PaperExecutionEngine
from autotrade.data.exchange import ExchangeDataFetcher
from autotrade.config import config
import time

def main():
    print("=== Paper Trading Simulation ===")

    # 1. Initialize Execution Engine
    # Note: Config has PAPER_INITIAL_BALANCE, but we can pass it explicitly or use config.
    engine = PaperExecutionEngine(initial_balance=config.PAPER_INITIAL_BALANCE)
    print(f"Initial Balance: {engine.get_balance()}")

    # 2. Initialize Data Fetcher (We need a price to trade)
    # Using 'binance' as default public exchange for price data
    # Fallback to kraken if binance is blocked
    exchange_id = 'kraken'
    fetcher = ExchangeDataFetcher(exchange_id=exchange_id)
    symbol = 'BTC/USDT'

    try:
        print(f"Fetching price for {symbol}...")
        # Get latest OHLCV
        df = fetcher.fetch_ohlcv(symbol, limit=1)
        if df.empty:
            print("Error: No data fetched.")
            return

        current_price = df.iloc[-1]['close']
        print(f"Current Price: {current_price} USDT")

        # 3. Execute a Buy Order
        amount_to_buy = 0.001 # BTC
        print(f"\nPlacing BUY order for {amount_to_buy} {symbol}...")

        order = engine.place_order(symbol, 'buy', 'market', amount_to_buy, price=current_price)
        print(f"Order Executed: {order}")

        # 4. Check Balance
        print(f"\nUpdated Balance: {engine.get_balance()}")

    except Exception as e:
        print(f"Simulation failed: {e}")

if __name__ == "__main__":
    main()
