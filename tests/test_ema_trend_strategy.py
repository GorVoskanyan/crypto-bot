import unittest
import pandas as pd
import numpy as np
from autotrade.strategies.ema_trend_strategy import EMATrendStrategy

class TestEMATrendStrategy(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.strategy = EMATrendStrategy()

    async def test_insufficient_data(self):
        df = pd.DataFrame({'close': [100.0, 101.0]})
        signal = await self.strategy.analyze(df)
        self.assertEqual(signal['action'], 'hold')
        self.assertIn('Insufficient data', signal['reason'])

    async def test_analyze_structure(self):
        np.random.seed(42)
        n = 250
        close = np.linspace(100, 150, n) + np.random.randn(n) * 0.2
        high = close + 0.3
        low = close - 0.3
        open_p = close - 0.05
        volume = np.random.uniform(500, 1500, n)

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
