import unittest
import pandas as pd
from unittest.mock import MagicMock
from autotrade.core.backtest import Backtester
from autotrade.strategies.base import Strategy

class MockStrategy(Strategy):
    def analyze(self, data):
        # Always buy on first candle after warmup, then hold
        # This is hard to test deterministically without controlling the iteration
        # So we mock the analyze behavior dynamically in the test or use simple logic

        # Simple Logic:
        # If price is 100, BUY.
        # If price is 200, SELL.
        current_price = data.iloc[-1]['close']
        if current_price == 100:
            return {'action': 'buy', 'price': 100.0}
        elif current_price == 200:
            return {'action': 'sell', 'price': 200.0}
        return {'action': 'hold'}

class TestBacktester(unittest.TestCase):

    def test_simple_profit_scenario(self):
        """
        Test a scenario where we buy at 100 and sell at 200.
        Profit should be ~100% (minus fees/slippage if modeled).
        """
        # Create Dummy Data
        # 0-49: Warmup (price 50)
        # 50: Price 100 (Buy Trigger)
        # 51: Price 150
        # 52: Price 200 (Sell Trigger)

        data_list = [{'close': 50}] * 50
        data_list.append({'close': 100}) # Buy
        data_list.append({'close': 150}) # Hold
        data_list.append({'close': 200}) # Sell

        df = pd.DataFrame(data_list)

        strategy = MockStrategy()

        # Disable risk manager sizing for simple math (100% allocation test logic?)
        # Or just rely on the default (1% risk).
        # To make math easy, let's look at relative return.

        backtester = Backtester(strategy, initial_balance=10000.0, symbol='BTC/USDT')

        # Override risk manager to allow big trade for testing impact
        # Setting Risk to 100% per trade effectively
        backtester.risk_manager.risk_per_trade = 1.0
        backtester.risk_manager.stop_loss_pct = 0.5 # Deep SL so we get large position

        # Calculation:
        # Balance 10,000. Risk 10,000.
        # Entry 100. SL 50. Dist 50.
        # Qty = 10000 / 50 = 200 units.
        # Cost = 200 * 100 = 20,000.
        # Cap at Balance: 10,000 / 100 = 100 units.

        # So we buy 100 units at 100.
        # Sell 100 units at 200.
        # Revenue = 20,000.
        # Profit = 10,000.
        # Final Balance = 20,000.
        # Return = 100%.

        backtester.run(df)

        metrics = backtester.calculate_metrics()

        self.assertEqual(metrics['trade_count'], 2) # Buy then Sell
        self.assertAlmostEqual(metrics['final_equity'], 20000.0)
        self.assertAlmostEqual(metrics['total_return_pct'], 100.0)

if __name__ == '__main__':
    unittest.main()
