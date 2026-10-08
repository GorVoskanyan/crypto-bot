import unittest
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
from autotrade.core.bot import TradingBot

class TestTradingBot(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_streamer = MagicMock()
        self.mock_strategy = MagicMock()
        self.mock_strategy.analyze = AsyncMock()
        self.mock_engine = MagicMock()

        # Default async mocks
        self.mock_engine.get_positions = AsyncMock(return_value=[])
        self.mock_engine.get_funding_rate = AsyncMock(return_value=0.0001)
        self.mock_engine.get_balance = AsyncMock(return_value={'USDT': 1000.0})
        self.mock_engine.place_order = AsyncMock(return_value={'orderId': '12345'})

        self.bot = TradingBot(
            streamer=self.mock_streamer,
            strategy=self.mock_strategy,
            engine=self.mock_engine,
            symbol='BTC/USDT',
            timeframe='1m'
        )

        # Populate initial candle data
        self.bot.ohlcv_data = pd.DataFrame([
            {'timestamp': '2023-01-01 00:00:00', 'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 100.0, 'volume': 10.0}
        ])

    async def test_process_strategy_buy(self):
        """Test that a buy signal calculates risk and triggers a market buy order."""
        self.mock_strategy.analyze.return_value = {
            'action': 'buy',
            'price': 100.0,
            'sl_pct': 0.02,
            'tp_pct': 0.04
        }

        await self.bot.process_strategy()

        self.mock_engine.place_order.assert_called_once_with(
            symbol='BTC/USDT',
            side='buy',
            order_type='MARKET',
            amount=5.0,
            stop_loss=98.0,
            take_profit=104.0,
            leverage=10
        )

    async def test_process_strategy_sell(self):
        """Test that a sell signal calculates risk and triggers a market sell order."""
        self.mock_strategy.analyze.return_value = {
            'action': 'sell',
            'price': 100.0,
            'sl_pct': 0.02,
            'tp_pct': 0.04
        }

        await self.bot.process_strategy()

        self.mock_engine.place_order.assert_called_once_with(
            symbol='BTC/USDT',
            side='sell',
            order_type='MARKET',
            amount=5.0,
            stop_loss=102.0,
            take_profit=96.0,
            leverage=10
        )

    async def test_process_strategy_hold(self):
        """Test that hold signal does not trigger any orders."""
        self.mock_strategy.analyze.return_value = {'action': 'hold'}

        await self.bot.process_strategy()

        self.mock_engine.place_order.assert_not_called()

    async def test_process_strategy_active_position(self):
        """Test that having an active position skips strategy analysis."""
        self.mock_engine.get_positions.return_value = [{
            'symbol': 'BTCUSDT',
            'amount': 0.5,
            'entry_price': 95.0,
            'unrealized_pnl': 2.5,
            'leverage': 10,
            'isolated': True
        }]

        await self.bot.process_strategy()

        self.mock_strategy.analyze.assert_not_called()
        self.mock_engine.place_order.assert_not_called()

if __name__ == '__main__':
    unittest.main()
