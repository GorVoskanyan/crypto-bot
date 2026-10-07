import unittest
from autotrade.risk.manager import RiskManager

class TestRiskManagerTrailing(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager(
            risk_percent_per_trade=0.01,
            max_leverage=20,
            breakeven_trigger_pct=0.01, # +1%
            trailing_stop_pct=0.008    # 0.8%
        )

    def test_breakeven_activation_long(self):
        # Entry at 100, current price goes to 101.5 (+1.5%), SL is at 98
        res = self.rm.evaluate_trailing_and_breakeven(
            side='BUY',
            entry_price=100.0,
            current_price=101.5,
            highest_price=101.5,
            lowest_price=99.5,
            current_sl_price=98.0
        )
        self.assertTrue(res['update_sl'])
        self.assertGreater(res['new_sl_price'], 100.0) # SL moved above entry
        self.assertIn('Break-Even', res['reason'])

    def test_trailing_stop_update_long(self):
        # Entry at 100, peak reaches 105, current price 104, SL is already at break-even (100.05)
        res = self.rm.evaluate_trailing_and_breakeven(
            side='BUY',
            entry_price=100.0,
            current_price=104.0,
            highest_price=105.0,
            lowest_price=99.5,
            current_sl_price=100.05
        )
        self.assertTrue(res['update_sl'])
        # Trailed SL = 105 * (1 - 0.008) = 104.16
        self.assertAlmostEqual(res['new_sl_price'], 104.16, places=2)
        self.assertIn('Trailing Stop', res['reason'])

    def test_breakeven_activation_short(self):
        # Entry at 100, current price drops to 98.5 (-1.5%), SL is at 102
        res = self.rm.evaluate_trailing_and_breakeven(
            side='SELL',
            entry_price=100.0,
            current_price=98.5,
            highest_price=100.5,
            lowest_price=98.5,
            current_sl_price=102.0
        )
        self.assertTrue(res['update_sl'])
        self.assertLess(res['new_sl_price'], 100.0) # SL moved below entry
        self.assertIn('Break-Even', res['reason'])

if __name__ == '__main__':
    unittest.main()
