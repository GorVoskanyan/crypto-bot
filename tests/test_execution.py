import unittest
from autotrade.execution.paper import PaperExecutionEngine

class TestPaperExecution(unittest.TestCase):

    def setUp(self):
        self.engine = PaperExecutionEngine(initial_balance=1000.0, base_currency='USDT')

    def test_initial_balance(self):
        """Test initial balance is set correctly."""
        balance = self.engine.get_balance()
        self.assertEqual(balance['USDT'], 1000.0)

    def test_buy_order_success(self):
        """Test a successful buy order."""
        # Buy 0.1 BTC at 5000 USDT -> Cost 500 USDT
        order = self.engine.place_order('BTC/USDT', 'buy', 'market', 0.1, price=5000.0)

        balance = self.engine.get_balance()
        self.assertEqual(balance['USDT'], 500.0)
        self.assertEqual(balance['BTC'], 0.1)

        self.assertEqual(order.status, 'closed')

    def test_insufficient_funds(self):
        """Test buy with insufficient funds."""
        with self.assertRaises(ValueError):
            # Buy 1 BTC at 2000 USDT (Cost 2000 > 1000)
            self.engine.place_order('BTC/USDT', 'buy', 'market', 1.0, price=2000.0)

    def test_sell_order_success(self):
        """Test a successful sell order."""
        # First buy some BTC
        self.engine.place_order('BTC/USDT', 'buy', 'market', 0.1, price=5000.0)

        # Sell 0.05 BTC at 6000 USDT -> Receive 300 USDT
        self.engine.place_order('BTC/USDT', 'sell', 'market', 0.05, price=6000.0)

        balance = self.engine.get_balance()
        self.assertEqual(balance['USDT'], 500.0 + 300.0) # 800
        self.assertEqual(balance['BTC'], 0.05)

if __name__ == '__main__':
    unittest.main()
