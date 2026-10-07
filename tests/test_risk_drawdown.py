import unittest
from autotrade.risk.manager import RiskManager

class TestRiskManagerDrawdown(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager(
            max_daily_drawdown_pct=0.03 # 3% limit
        )
        self.rm.day_start_balance = 1000.0

    def test_circuit_breaker_inactive(self):
        # 1000 balance -> 980 balance (-2% loss) -> breaker should NOT trip
        active = self.rm.is_circuit_breaker_active(980.0)
        self.assertFalse(active)

    def test_circuit_breaker_active(self):
        # 1000 balance -> 960 balance (-4% loss) -> breaker SHOULD trip
        active = self.rm.is_circuit_breaker_active(960.0)
        self.assertTrue(active)
        self.assertFalse(self.rm.check_trade_permission({'action': 'buy'}, {'USDT': 960.0}, 'BTC/USDT'))

if __name__ == '__main__':
    unittest.main()
