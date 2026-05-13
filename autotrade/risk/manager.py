from typing import Dict, Optional, Tuple
from autotrade.config import config

class RiskManager:
    """
    Manages trading risk, position sizing, and trade permissions.
    """

    def __init__(self):
        self.risk_per_trade = config.RISK_PERCENT_PER_TRADE
        self.stop_loss_pct = config.STOP_LOSS_PCT
        self.take_profit_pct = config.TAKE_PROFIT_PCT

    def check_trade_permission(self, signal: Dict, balance: Dict[str, float], symbol: str) -> bool:
        """
        Checks if a trade is allowed based on risk rules.
        """
        action = signal.get('action')
        if action not in ['buy', 'sell']:
            return False

        # Example check: Do we have enough quote currency to open a position?
        if action == 'buy':
            quote_currency = symbol.split('/')[1]
            if balance.get(quote_currency, 0) <= 0:
                return False

        # Example check: Do we have asset to sell?
        if action == 'sell':
            base_currency = symbol.split('/')[0]
            if balance.get(base_currency, 0) <= 0:
                return False

        return True

    def calculate_quantity(self, signal: Dict, balance: Dict[str, float], symbol: str, leverage: int = 1) -> float:
        """
        Calculates the safe quantity to trade based on risk per trade for futures.
        """
        entry_price = signal.get('price')
        if not entry_price or entry_price <= 0:
            return 0.0

        quote_currency = symbol.split('/')[1]
        account_balance = balance.get(quote_currency, 0)

        # Risk amount in quote currency
        risk_amount = account_balance * self.risk_per_trade

        # SL percentage from signal or config
        sl_pct = signal.get('sl_pct', self.stop_loss_pct)

        price_distance = entry_price * sl_pct

        if price_distance == 0:
            return 0.0

        # Quantity based on risk management: (Balance * Risk%) / SL_Distance
        quantity = risk_amount / price_distance

        # In futures, max quantity is (balance * leverage) / entry_price
        max_leverage_quantity = (account_balance * leverage) / entry_price

        return min(quantity, max_leverage_quantity)

    def calculate_dynamic_leverage(self, entry_price: float, stop_loss_price: float) -> int:
        """
        Calculates required leverage to sustain the stop loss while respecting risk.
        If SL is 2%, 1/0.02 = 50x is the liquidation leverage. We want to be safer.
        """
        if entry_price == 0 or entry_price == stop_loss_price:
            return 1

        sl_dist_pct = abs(entry_price - stop_loss_price) / entry_price

        # We want our liquidation price to be BEYOND our stop loss.
        # Approx Liquidation % = 1 / Leverage
        # So Leverage < 1 / SL_dist_pct
        # We apply a safety factor (e.g., 0.8)
        recommended_leverage = int(0.8 / sl_dist_pct)
        return max(1, min(recommended_leverage, 20)) # Cap at 20x for safety

    def estimate_liquidation_price(self, entry_price: float, leverage: int, side: str, isolated: bool = True) -> float:
        """
        Simple estimation of liquidation price.
        """
        if side == 'buy':
            return entry_price * (1 - (1 / leverage) + 0.005) # 0.5% buffer
        else:
            return entry_price * (1 + (1 / leverage) - 0.005)

    def get_exit_prices(self, entry_price: float, signal_type: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculates Stop Loss and Take Profit prices.

        Returns: (stop_loss_price, take_profit_price)
        """
        if signal_type == 'buy':
            sl_price = entry_price * (1 - self.stop_loss_pct)
            tp_price = entry_price * (1 + self.take_profit_pct)
            return sl_price, tp_price

        elif signal_type == 'sell':
            # For short selling (future implementation), logic mirrors 'buy'
            # But currently we only support Spot Sell (exit position).
            # If this were a short open:
            sl_price = entry_price * (1 + self.stop_loss_pct)
            tp_price = entry_price * (1 - self.take_profit_pct)
            return sl_price, tp_price

        return None, None
