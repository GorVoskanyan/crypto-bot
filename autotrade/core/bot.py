import time
import logging
from typing import Optional
from autotrade.data.base import DataFetcher
from autotrade.strategies.base import Strategy
from autotrade.execution.base import ExecutionEngine
from autotrade.risk.manager import RiskManager
from autotrade.notifications.telegram import TelegramNotificationProvider
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
        self.risk_manager = RiskManager()
        self.symbol = symbol
        self.timeframe = timeframe
        self.is_running = False

        # Initialize Notifier
        self.notifier = None
        if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
            self.notifier = TelegramNotificationProvider(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID)
            self._notify(f"Bot started for {symbol}")

    def _notify(self, message: str):
        """Helper to send notifications safely."""
        if self.notifier:
            self.notifier.send(message)

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
            msg = f"Failed to fetch data: {e}"
            logger.error(msg)
            self._notify(f"⚠️ Error: {msg}")
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
            try:
                balance = self.execution_engine.get_balance()
                price = signal.get('price')

                if not price:
                    logger.warning("Signal 'buy' missing price")
                    return

                # Risk Management Checks
                if not self.risk_manager.check_trade_permission(signal, balance, self.symbol):
                    logger.warning("Risk Manager blocked trade permission")
                    return

                amount_to_buy = self.risk_manager.calculate_quantity(signal, balance, self.symbol)

                if amount_to_buy <= 0:
                    logger.warning("Risk Manager calculated zero quantity (insufficient funds or too high risk)")
                    return

                sl_price, tp_price = self.risk_manager.get_exit_prices(price, 'buy')

                # Execute
                self.execution_engine.place_order(
                    self.symbol,
                    'buy',
                    'market',
                    amount_to_buy,
                    price=price,
                    stop_loss=sl_price,
                    take_profit=tp_price
                )
                msg = f"🚀 BUY {amount_to_buy:.4f} {self.symbol} @ {price}\nSL: {sl_price}\nTP: {tp_price}"
                logger.info(msg.replace('\n', ' '))
                self._notify(msg)

            except Exception as e:
                msg = f"Execution failed: {e}"
                logger.error(msg)
                self._notify(f"⚠️ Error: {msg}")

        elif action == 'sell':
             # Simple logic: Sell all holdings of the base asset
            try:
                base_currency = self.symbol.split('/')[0]
                positions = self.execution_engine.get_positions()
                available_asset = positions.get(base_currency, 0)

                if available_asset > 0:
                     price = signal.get('price')
                     self.execution_engine.place_order(self.symbol, 'sell', 'market', available_asset, price=price)
                     msg = f"📉 SELL {available_asset:.4f} {self.symbol} @ {price}"
                     logger.info(msg)
                     self._notify(msg)
                else:
                    logger.info("No assets to sell")

            except Exception as e:
                msg = f"Execution failed: {e}"
                logger.error(msg)
                self._notify(f"⚠️ Error: {msg}")

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
