from autotrade.core.bot import TradingBot
from autotrade.data.exchange import ExchangeDataFetcher
from autotrade.strategies.sma_crossover import SMACrossoverStrategy
from autotrade.execution.paper import PaperExecutionEngine
from autotrade.config import config
import time

def main():
    print("=== Starting AutoTrade Bot (Demo Mode) ===")

    # 1. Setup Components
    # Using Kraken for demo as Binance might be blocked
    exchange_id = 'kraken' # Overriding config for demo stability
    data_fetcher = ExchangeDataFetcher(exchange_id=exchange_id)

    # Simple strategy: very short windows to trigger signals in demo if possible
    # (Though likely won't trigger in 1 iteration unless we are lucky or market is volatile)
    strategy = SMACrossoverStrategy(short_window=10, long_window=30)

    execution_engine = PaperExecutionEngine(initial_balance=config.PAPER_INITIAL_BALANCE)

    symbol = 'BTC/USDT'

    # 2. Create Bot
    bot = TradingBot(data_fetcher, strategy, execution_engine, symbol, timeframe='1h')

    # 3. Run a few iterations
    print(f"Bot initialized for {symbol} on {exchange_id}. Balance: {execution_engine.get_balance()}")

    try:
        # Run 3 iterations
        for i in range(1, 4):
            print(f"\nIteration {i}/3...")
            bot.run_iteration()

            print(f"Current Balance: {execution_engine.get_balance()}")

            if i < 3:
                print("Waiting 2 seconds...")
                time.sleep(2)

    except KeyboardInterrupt:
        print("Stopped.")

    print("\nDemo Complete.")

if __name__ == "__main__":
    main()
