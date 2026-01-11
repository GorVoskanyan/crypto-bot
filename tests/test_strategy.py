import unittest
import pandas as pd
from autotrade.strategies.sma_crossover import SMACrossoverStrategy

class TestSMACrossover(unittest.TestCase):

    def test_hold_not_enough_data(self):
        strategy = SMACrossoverStrategy(short_window=2, long_window=5)
        # Create small dataframe
        df = pd.DataFrame({'close': [10, 11, 12]})
        signal = strategy.analyze(df)
        self.assertEqual(signal['action'], 'hold')
        self.assertEqual(signal['reason'], 'Not enough data')

    def test_golden_cross_buy(self):
        strategy = SMACrossoverStrategy(short_window=2, long_window=3)
        # Setup data where short crosses above long
        # SMA2: [10, 10.5, 11.5, 12.5]
        # SMA3: [NaN, NaN, 11.0, 12.0]
        # Prev: SMA2=11.5, SMA3=11.0 (Wait, 11.5 > 11.0 already? Let's tune numbers)

        # Prices: 10, 10, 13, 13
        # i=0: 10
        # i=1: 10. SMA2=(10+10)/2=10. SMA3=NaN
        # i=2: 13. SMA2=(10+13)/2=11.5. SMA3=(10+10+13)/3=11.0. Short > Long.
        # i=3: 13. SMA2=(13+13)/2=13. SMA3=(10+13+13)/3=12. Short > Long.

        # We need PREV row to have Short <= Long, and LAST row Short > Long.

        # Try:
        # P: 10, 10, 10, 12
        # i=0: 10
        # i=1: 10. SMA2=10. SMA3=NaN
        # i=2: 10. SMA2=10. SMA3=10. (Equal)
        # i=3: 12. SMA2=11. SMA3=10.66. (Short > Long)

        # Data
        data = [10, 10, 10, 12]
        df = pd.DataFrame({'close': data})

        signal = strategy.analyze(df)

        # Debug print if fails
        # print(signal)

        self.assertEqual(signal['action'], 'buy')
        self.assertEqual(signal['price'], 12)

    def test_death_cross_sell(self):
        strategy = SMACrossoverStrategy(short_window=2, long_window=3)

        # We need PREV row Short >= Long, LAST row Short < Long.

        # P: 10, 12, 12, 8
        # i=2: 12. SMA2=12. SMA3=11.33. Short > Long.
        # i=3: 8.  SMA2=10. SMA3=10.66. Short < Long.

        data = [10, 12, 12, 8]
        df = pd.DataFrame({'close': data})

        signal = strategy.analyze(df)
        self.assertEqual(signal['action'], 'sell')
        self.assertEqual(signal['price'], 8)

if __name__ == '__main__':
    unittest.main()
