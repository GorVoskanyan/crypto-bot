import unittest
from unittest.mock import MagicMock, AsyncMock
import pandas as pd
from autotrade.core.bot import TradingBot

class TestTradingBot(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_streamer = MagicMock()
        self.mock_strategy = MagicMock()
        self.mock_engine = MagicMock()

        # Mock essential async methods of components
        self.mock_streamer.fetch_ohlcv = AsyncMock(return_value=pd.DataFrame({'close': [100.0]}))
        self.mock_engine.get_positions = AsyncMock(return_value=[])
        self.mock_engine.get_funding_rate = AsyncMock(return_value=0.0001)
        self.mock_engine.get_balance = AsyncMock(return_value={'USDT': 1000.0})
        self.mock_engine.place_order = AsyncMock()
        self.mock_strategy.analyze = AsyncMock()

        self.bot = TradingBot(
            streamer=self.mock_streamer,
            strategy=self.mock_strategy,
            engine=self.mock_engine,
            symbol='BTC/USDT'
        )
        self.bot.ohlcv_data = pd.DataFrame({'close': [100.0]})

    async def test_process_strategy_buy(self):
        """Test that a buy signal calculates risk and triggers a market buy order."""
        # Setup strategy to return buy signal
        self.mock_strategy.analyze.return_value = {
            'action': 'buy',
            'price': 100.0,
            'sl_pct': 0.02,
            'tp_pct': 0.04
        }

        # Run strategy processing
        await self.bot.process_strategy()

        # Verify order execution parameters:
        # sl_price = 100 * (1 - 0.02) = 98.0
        # tp_price = 100 * (1 + 0.04) = 104.0
        # leverage = min(int(0.8 / 0.02), 20) = 20
        # amount calculation: risk_amount (1000 * 0.01 = 10) / sl_distance (2) = 5.0
        self.mock_engine.place_order.assert_called_once_with(
            symbol='BTC/USDT',
            side='buy',
            order_type='MARKET',
            amount=5.0,
            stop_loss=98.0,
            take_profit=104.0,
            leverage=20
        )
        self.assertTrue(self.bot.in_position)

    async def test_process_strategy_sell(self):
        """Test that a sell signal calculates risk and triggers a market sell order."""
        # Setup strategy to return sell signal
        self.mock_strategy.analyze.return_value = {
            'action': 'sell',
            'price': 100.0,
            'sl_pct': 0.02,
            'tp_pct': 0.04
        }

        # Run strategy processing
        await self.bot.process_strategy()

        # Verify order execution parameters:
        # sl_price = 100 * (1 + 0.02) = 102.0
        # tp_price = 100 * (1 - 0.04) = 96.0
        # leverage = min(int(0.8 / 0.02), 20) = 20
        # amount calculation: risk_amount (1000 * 0.01 = 10) / sl_distance (2) = 5.0
        self.mock_engine.place_order.assert_called_once_with(
            symbol='BTC/USDT',
            side='sell',
            order_type='MARKET',
            amount=5.0,
            stop_loss=102.0,
            take_profit=96.0,
            leverage=20
        )
        self.assertTrue(self.bot.in_position)

    async def test_process_strategy_hold(self):
        """Test that hold signal does not trigger any orders."""
        self.mock_strategy.analyze.return_value = {'action': 'hold'}

        await self.bot.process_strategy()

        self.mock_engine.place_order.assert_not_called()

    async def test_process_strategy_active_position(self):
        """Test that having an active position skips strategy analysis."""
        # Setup active position
        self.mock_engine.get_positions.return_value = [{
            'symbol': 'BTCUSDT',
            'amount': 0.5,
            'entry_price': 95.0,
            'unrealized_pnl': 2.5,
            'leverage': 20,
            'isolated': True
        }]

        await self.bot.process_strategy()

        # Should return early and not analyze or place order
        self.mock_strategy.analyze.assert_not_called()
        self.mock_engine.place_order.assert_not_called()
        self.assertTrue(self.bot.in_position)

if __name__ == '__main__':
    unittest.main()
