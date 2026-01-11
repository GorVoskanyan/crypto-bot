import unittest
from autotrade.risk.manager import RiskManager
from autotrade.config import config

class TestRiskManager(unittest.TestCase):

    def setUp(self):
        self.risk_manager = RiskManager()
        # Override config for predictable tests
        self.risk_manager.risk_per_trade = 0.01  # 1%
        self.risk_manager.stop_loss_pct = 0.02   # 2%

    def test_calculate_quantity(self):
        """
        Test position sizing formula.
        Balance: 10,000 USDT
        Risk: 1% -> $100
        Entry Price: 50,000
        Stop Loss: 2% -> $1000 price drop
        Quantity = $100 / $1000 = 0.1 BTC
        """
        balance = {'USDT': 10000.0}
        signal = {'action': 'buy', 'price': 50000.0}
        symbol = 'BTC/USDT'

        qty = self.risk_manager.calculate_quantity(signal, balance, symbol)
        self.assertAlmostEqual(qty, 0.1)

    def test_calculate_quantity_insufficient_funds(self):
        """
        Test that quantity is capped by available balance.
        Balance: 100 USDT
        Risk: 1% -> $1
        Entry: 100
        SL: 0.1% -> $0.1 distance
        Calculated Qty = 1 / 0.1 = 10 units.
        Cost = 10 * 100 = 1000 USDT.
        We only have 100 USDT. Max qty = 1.
        """
        self.risk_manager.stop_loss_pct = 0.001 # 0.1%
        balance = {'USDT': 100.0}
        signal = {'action': 'buy', 'price': 100.0}
        symbol = 'BTC/USDT'

        qty = self.risk_manager.calculate_quantity(signal, balance, symbol)
        self.assertAlmostEqual(qty, 1.0)

    def test_check_trade_permission_buy(self):
        symbol = 'BTC/USDT'
        # Allowed
        self.assertTrue(self.risk_manager.check_trade_permission({'action': 'buy'}, {'USDT': 100}, symbol))
        # Denied (No funds)
        self.assertFalse(self.risk_manager.check_trade_permission({'action': 'buy'}, {'USDT': 0}, symbol))

    def test_get_exit_prices(self):
        entry = 100.0
        self.risk_manager.stop_loss_pct = 0.05
        self.risk_manager.take_profit_pct = 0.10

        sl, tp = self.risk_manager.get_exit_prices(entry, 'buy')
        self.assertAlmostEqual(sl, 95.0)
        self.assertAlmostEqual(tp, 110.0)

if __name__ == '__main__':
    unittest.main()
