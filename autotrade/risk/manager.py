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

    def calculate_quantity(self, signal: Dict, balance: Dict[str, float], symbol: str) -> float:
        """
        Calculates the safe quantity to trade based on risk per trade.

        Formula:
        Risk Amount = Account Balance * Risk Per Trade %
        Price Distance to Stop Loss = Entry Price * Stop Loss %
        Quantity = Risk Amount / Price Distance

        Example:
        Balance $10,000. Risk 1% = $100.
        Price $50,000. SL 2%. Distance = $1,000.
        Quantity = 100 / 1000 = 0.1 BTC.

        Check: 0.1 BTC * $1000 drop = $100 loss. Correct.
        """
        entry_price = signal.get('price')
        if not entry_price or entry_price <= 0:
            return 0.0

        quote_currency = symbol.split('/')[1]
        account_balance = balance.get(quote_currency, 0)

        # Calculate max risk amount in dollars
        risk_amount = account_balance * self.risk_per_trade

        # Calculate price distance to stop loss
        price_distance = entry_price * self.stop_loss_pct

        if price_distance == 0:
            return 0.0

        quantity = risk_amount / price_distance

        # Cap quantity at available balance (cannot spend more than we have)
        max_affordable_quantity = account_balance / entry_price

        return min(quantity, max_affordable_quantity)

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
