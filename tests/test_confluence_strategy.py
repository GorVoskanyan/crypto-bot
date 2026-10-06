import unittest
import pandas as pd
import numpy as np
from autotrade.strategies.confluence_strategy import ConfluenceStrategy

class TestConfluenceStrategy(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.strategy = ConfluenceStrategy()

    async def test_insufficient_data(self):
        df = pd.DataFrame({'close': [100.0, 101.0]})
        signal = await self.strategy.analyze(df)
        self.assertEqual(signal['action'], 'hold')
        self.assertIn('Insufficient data', signal['reason'])

    async def test_analyze_structure(self):
        np.random.seed(42)
        n = 100
        close = np.linspace(100, 110, n) + np.random.randn(n) * 0.5
        high = close + 0.5
        low = close - 0.5
        open_p = close - 0.1
        volume = np.random.uniform(100, 500, n)

        df = pd.DataFrame({
            'open': open_p,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

        signal = await self.strategy.analyze(df)
        self.assertIn(signal['action'], ['buy', 'sell', 'hold'])

if __name__ == '__main__':
    unittest.main()
