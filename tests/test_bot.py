import unittest
from unittest.mock import MagicMock
import pandas as pd
from autotrade.core.bot import TradingBot

class TestTradingBot(unittest.TestCase):

    def setUp(self):
        self.mock_data = MagicMock()
        self.mock_strategy = MagicMock()
        self.mock_execution = MagicMock()

        self.bot = TradingBot(
            self.mock_data,
            self.mock_strategy,
            self.mock_execution,
            symbol='BTC/USDT'
        )

    def test_run_iteration_buy(self):
        """Test that a buy signal triggers an order."""
        # 1. Setup Data Fetcher
        self.mock_data.fetch_ohlcv.return_value = pd.DataFrame({'close': [100]})

        # 2. Setup Strategy
        self.mock_strategy.analyze.return_value = {'action': 'buy', 'price': 100.0}

        # 3. Setup Execution (Available balance)
        self.mock_execution.get_balance.return_value = {'USDT': 1000.0}

        # Run
        self.bot.run_iteration()

        # Verify
        # Should buy 10% of 1000 = 100 USDT. Price = 100. Amount = 1.
        self.mock_execution.place_order.assert_called_with(
            'BTC/USDT', 'buy', 'market', 1.0, price=100.0
        )

    def test_run_iteration_sell(self):
        """Test that a sell signal triggers an order."""
        # 1. Setup Data
        self.mock_data.fetch_ohlcv.return_value = pd.DataFrame({'close': [100]})

        # 2. Setup Strategy
        self.mock_strategy.analyze.return_value = {'action': 'sell', 'price': 100.0}

        # 3. Setup Execution (Has positions)
        self.mock_execution.get_positions.return_value = {'BTC': 0.5}

        # Run
        self.bot.run_iteration()

        # Verify
        # Should sell all 0.5 BTC
        self.mock_execution.place_order.assert_called_with(
            'BTC/USDT', 'sell', 'market', 0.5, price=100.0
        )

    def test_run_iteration_hold(self):
        """Test that hold signal does nothing."""
        self.mock_data.fetch_ohlcv.return_value = pd.DataFrame({'close': [100]})
        self.mock_strategy.analyze.return_value = {'action': 'hold'}

        self.bot.run_iteration()

        self.mock_execution.place_order.assert_not_called()

if __name__ == '__main__':
    unittest.main()
