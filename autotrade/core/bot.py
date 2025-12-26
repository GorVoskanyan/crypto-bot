import time
import logging
from typing import Optional
from autotrade.data.base import DataFetcher
from autotrade.strategies.base import Strategy
from autotrade.execution.base import ExecutionEngine
from autotrade.config import config

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class TradingBot:
    """
    The main orchestrator class.
    """

    def __init__(self, data_fetcher: DataFetcher, strategy: Strategy, execution_engine: ExecutionEngine, symbol: str, timeframe: str = '1h'):
        self.data_fetcher = data_fetcher
        self.strategy = strategy
        self.execution_engine = execution_engine
        self.symbol = symbol
        self.timeframe = timeframe
        self.is_running = False

    def run_iteration(self):
        """
        Runs one iteration of the trading loop.
        """
        logger.info(f"--- Starting iteration for {self.symbol} ---")

        # 1. Fetch Data
        try:
            # Fetch enough data for the strategy (e.g., long window + buffer)
            # Hardcoded limit for now, ideally strategy defines its requirement
            data = self.data_fetcher.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
            logger.debug(f"Fetched {len(data)} candles")
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return

        # 2. Analyze
        try:
            signal = self.strategy.analyze(data)
            logger.info(f"Signal: {signal}")
        except Exception as e:
            logger.error(f"Strategy analysis failed: {e}")
            return

        # 3. Execute
        action = signal.get('action')

        if action == 'buy':
            # Simple logic: Buy with 10% of available USDT balance
            # Real logic would be in a RiskManager module
            try:
                balance = self.execution_engine.get_balance()
                # Assuming USDT for now as quote currency
                quote_currency = self.symbol.split('/')[1]
                available_cash = balance.get(quote_currency, 0)

                if available_cash > 0:
                    amount_to_spend = available_cash * 0.10
                    price = signal.get('price')

                    if price:
                         amount_to_buy = amount_to_spend / price
                         # Filter small dust?
                         self.execution_engine.place_order(self.symbol, 'buy', 'market', amount_to_buy, price=price)
                         logger.info(f"Executed BUY for {amount_to_buy} {self.symbol}")
                    else:
                        logger.warning("Signal 'buy' missing price")
                else:
                    logger.warning("Insufficient funds to buy")

            except Exception as e:
                logger.error(f"Execution failed: {e}")

        elif action == 'sell':
             # Simple logic: Sell all holdings of the base asset
            try:
                base_currency = self.symbol.split('/')[0]
                positions = self.execution_engine.get_positions()
                available_asset = positions.get(base_currency, 0)

                if available_asset > 0:
                     price = signal.get('price')
                     self.execution_engine.place_order(self.symbol, 'sell', 'market', available_asset, price=price)
                     logger.info(f"Executed SELL for {available_asset} {self.symbol}")
                else:
                    logger.info("No assets to sell")

            except Exception as e:
                logger.error(f"Execution failed: {e}")

        elif action == 'hold':
            pass

        else:
            logger.warning(f"Unknown action: {action}")

    def run(self, interval: int = 60):
        """
        Runs the bot loop indefinitely.
        """
        self.is_running = True
        while self.is_running:
            self.run_iteration()
            time.sleep(interval)
