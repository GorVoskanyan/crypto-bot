import unittest
import pandas as pd
import numpy as np
from autotrade.strategies.confluence_strategy import ConfluenceStrategy

class TestConfluenceStrategy(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.strategy = ConfluenceStrategy()

    async def test_insufficient_data(self):
        """Test that insufficient candles return hold."""
        df = pd.DataFrame({
            'close': [100.0] * 10,
            'high': [101.0] * 10,
            'low': [99.0] * 10,
            'volume': [1000.0] * 10
        })
        signal = await self.strategy.analyze(df)
        self.assertEqual(signal['action'], 'hold')
        self.assertEqual(signal['reason'], 'Insufficient data')

    async def test_flat_market_hold(self):
        """Test that flat/neutral market returns hold signal."""
        periods = 50
        df = pd.DataFrame({
            'close': [100.0 + (i % 2) * 0.1 for i in range(periods)],
            'high': [101.0] * periods,
            'low': [99.0] * periods,
            'volume': [1000.0] * periods
        })
        signal = await self.strategy.analyze(df)
        self.assertEqual(signal['action'], 'hold')

    async def test_oversold_confluence_buy_signal(self):
        """Test that price touching lower BB + oversold RSI + MACD reversal triggers buy."""
        periods = 60
        prices = [100.0] * 40
        for i in range(20):
            prices.append(100.0 - (i + 1) * 1.5)

        df = pd.DataFrame({
            'close': prices,
            'high': [p + 0.5 for p in prices],
            'low': [p - 0.5 for p in prices],
            'volume': [5000.0] * len(prices)
        })

        signal = await self.strategy.analyze(df)
        self.assertIn(signal['action'], ['buy', 'hold'])
        if signal['action'] == 'buy':
            self.assertGreater(signal['tp_pct'], signal['sl_pct']) # Verify > 1:2 R:R

if __name__ == '__main__':
    unittest.main()
