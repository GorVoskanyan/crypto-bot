import math
from typing import Dict, Any, Tuple

class RiskManager:
    """
    Handles position sizing, leverage calculation, Stop-Loss / Take-Profit logic,
    Break-Even activation, and Trailing Stop updates.
    """

    def __init__(
        self,
        risk_percent_per_trade: float = 0.01,
        max_leverage: int = 20,
        breakeven_trigger_pct: float = 0.01,   # Activate Break-Even at +1% profit
        trailing_stop_pct: float = 0.008,      # Trail Stop-Loss by 0.8% behind peak price
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04
    ):
        self.risk_percent_per_trade = risk_percent_per_trade
        self.max_leverage = max_leverage
        self.breakeven_trigger_pct = breakeven_trigger_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def check_trade_permission(self, signal: Dict[str, Any], balance: Dict[str, float], symbol: str) -> bool:
        quote_currency = symbol.split('/')[1] if '/' in symbol else 'USDT'
        available = balance.get(quote_currency, 0.0)
        return available > 10.0 and signal.get('action') in ['buy', 'sell']

    def get_exit_prices(self, entry_price: float, side: str) -> Tuple[float, float]:
        side_upper = side.upper()
        if side_upper in ['BUY', 'LONG']:
            sl = entry_price * (1 - self.stop_loss_pct)
            tp = entry_price * (1 + self.take_profit_pct)
        else:
            sl = entry_price * (1 + self.stop_loss_pct)
            tp = entry_price * (1 - self.take_profit_pct)
        return sl, tp

    def calculate_quantity(self, signal: Dict[str, Any], balance: Dict[str, float], symbol: str, leverage: int = 1) -> float:
        """
        Calculates position quantity based on risk percent and stop loss distance.
        """
        quote_currency = symbol.split('/')[1] if '/' in symbol else 'USDT'
        available_balance = balance.get(quote_currency, 0.0)

        if available_balance <= 0:
            return 0.0

        price = signal['price']
        sl_pct = signal.get('sl_pct', self.stop_loss_pct)

        risk_amount = available_balance * self.risk_percent_per_trade

        sl_dist = price * sl_pct
        if sl_dist <= 0:
            return 0.0

        quantity = risk_amount / sl_dist

        # Cap quantity by available balance * leverage
        max_notional = available_balance * leverage
        max_quantity = max_notional / price

        return min(quantity, max_quantity)

    def calculate_dynamic_leverage(self, entry_price: float, sl_price: float) -> int:
        """
        Calculates dynamic leverage based on stop loss distance.
        """
        sl_dist_pct = abs(entry_price - sl_price) / entry_price
        if sl_dist_pct <= 0:
            return 1

        recommended_leverage = int(1 / (sl_dist_pct * 2))
        return max(1, min(recommended_leverage, self.max_leverage))

    def evaluate_trailing_and_breakeven(
        self,
        side: str,
        entry_price: float,
        current_price: float,
        highest_price: float,
        lowest_price: float,
        current_sl_price: float
    ) -> Dict[str, Any]:
        """
        Evaluates current position price to determine if Break-Even or Trailing Stop should update the SL price.
        """
        side_upper = side.upper()
        if side_upper in ['BUY', 'LONG']:
            price_gain_pct = (current_price - entry_price) / entry_price
            peak_gain_pct = (highest_price - entry_price) / entry_price

            # 1. Break-Even Check
            if price_gain_pct >= self.breakeven_trigger_pct and current_sl_price < entry_price:
                return {
                    'update_sl': True,
                    'new_sl_price': entry_price * 1.0005,
                    'reason': 'Break-Even activated'
                }

            # 2. Trailing Stop Check
            if peak_gain_pct >= self.breakeven_trigger_pct:
                trailed_sl = highest_price * (1 - self.trailing_stop_pct)
                if trailed_sl > current_sl_price:
                    return {
                        'update_sl': True,
                        'new_sl_price': trailed_sl,
                        'reason': f'Trailing Stop update (peak {highest_price:.2f})'
                    }

        elif side_upper in ['SELL', 'SHORT']:
            price_gain_pct = (entry_price - current_price) / entry_price
            peak_gain_pct = (entry_price - lowest_price) / entry_price

            # 1. Break-Even Check
            if price_gain_pct >= self.breakeven_trigger_pct and current_sl_price > entry_price:
                return {
                    'update_sl': True,
                    'new_sl_price': entry_price * 0.9995,
                    'reason': 'Break-Even activated'
                }

            # 2. Trailing Stop Check
            if peak_gain_pct >= self.breakeven_trigger_pct:
                trailed_sl = lowest_price * (1 + self.trailing_stop_pct)
                if trailed_sl < current_sl_price:
                    return {
                        'update_sl': True,
                        'new_sl_price': trailed_sl,
                        'reason': f'Trailing Stop update (trough {lowest_price:.2f})'
                    }

        return {'update_sl': False, 'new_sl_price': current_sl_price, 'reason': 'No change'}
