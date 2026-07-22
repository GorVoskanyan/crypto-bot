import unittest
import pandas as pd
from autotrade.strategies.sma_crossover import SMACrossoverStrategy

class TestSMACrossover(unittest.IsolatedAsyncioTestCase):

    async def test_hold_not_enough_data(self):
        strategy = SMACrossoverStrategy(short_window=2, long_window=5)
        # Create small dataframe
        df = pd.DataFrame({'close': [10, 11, 12]})
        signal = await strategy.analyze(df)
        self.assertEqual(signal['action'], 'hold')
        self.assertEqual(signal['reason'], 'Not enough data')

    async def test_golden_cross_buy(self):
        strategy = SMACrossoverStrategy(short_window=2, long_window=3)
        # Data
        data = [10, 10, 10, 12]
        df = pd.DataFrame({'close': data})

        signal = await strategy.analyze(df)

        self.assertEqual(signal['action'], 'buy')
        self.assertEqual(signal['price'], 12)

    async def test_death_cross_sell(self):
        strategy = SMACrossoverStrategy(short_window=2, long_window=3)
        data = [10, 12, 12, 8]
        df = pd.DataFrame({'close': data})

        signal = await strategy.analyze(df)
        self.assertEqual(signal['action'], 'sell')
        self.assertEqual(signal['price'], 8)

if __name__ == '__main__':
    unittest.main()
