import unittest
import pandas as pd
import numpy as np
from autotrade.strategies.adaptive_selector import AdaptiveStrategySelector

class TestAdaptiveSelector(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.selector = AdaptiveStrategySelector()

    async def test_detect_market_regime(self):
        np.random.seed(42)
        n = 100
        close = np.linspace(100, 120, n) + np.random.randn(n) * 0.5
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

        regime_info = self.selector.detect_market_regime(df)
        self.assertIn('regime', regime_info)
        self.assertIn(regime_info['regime'], ['trending', 'ranging', 'scalp', 'unknown'])

    async def test_analyze(self):
        np.random.seed(42)
        n = 100
        close = np.linspace(100, 120, n) + np.random.randn(n) * 0.5
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

        signal = await self.selector.analyze(df)
        self.assertIn(signal['action'], ['buy', 'sell', 'hold'])

if __name__ == '__main__':
    unittest.main()
