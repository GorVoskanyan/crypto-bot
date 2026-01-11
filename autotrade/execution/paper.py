import uuid
from datetime import datetime
from typing import Dict, Optional
from autotrade.execution.base import ExecutionEngine, Order

class PaperExecutionEngine(ExecutionEngine):
    """
    Simulates order execution without real funds.
    """

    def __init__(self, initial_balance: float = 10000.0, base_currency: str = 'USDT'):
        """
        Initialize the paper trading engine.

        Args:
            initial_balance (float): Starting cash.
            base_currency (str): The currency of the balance (e.g., 'USDT').
        """
        self.base_currency = base_currency
        self.balance = {base_currency: initial_balance}
        self.positions = {}  # e.g., {'BTC': 0.5}

    def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: Optional[float] = None, stop_loss: Optional[float] = None, take_profit: Optional[float] = None) -> Order:
        """
        Executes a paper trade.
        """
        if price is None:
            raise ValueError("Price must be provided for paper trading execution (simulation requires external price feed).")

        base_asset, quote_asset = symbol.split('/')  # e.g. BTC/USDT -> BTC, USDT

        # Simple validation
        if quote_asset != self.base_currency:
            # In a real system we'd handle cross-pair conversions, but for now strict matching
            raise ValueError(f"Quote asset {quote_asset} does not match account currency {self.base_currency}")

        cost = amount * price

        if side == 'buy':
            if self.balance.get(self.base_currency, 0) < cost:
                raise ValueError("Insufficient funds")

            # Deduct cash, add asset
            self.balance[self.base_currency] -= cost
            self.balance[base_asset] = self.balance.get(base_asset, 0) + amount

        elif side == 'sell':
            if self.positions.get(base_asset, 0) < amount:
                # Check if we have the asset in balance (positions usually tracked in balance for simple spot)
                # Let's align positions and balance. usually in spot, balance['BTC'] IS the position.
                if self.balance.get(base_asset, 0) < amount:
                    raise ValueError(f"Insufficient {base_asset} balance")

            # Deduct asset, add cash
            self.balance[base_asset] = self.balance.get(base_asset, 0) - amount
            self.balance[self.base_currency] += cost

        else:
            raise ValueError(f"Invalid side: {side}")

        # Create Order record
        order = Order(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            type=order_type,
            amount=amount,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status='closed', # Instant fill
            timestamp=datetime.now()
        )
        return order

    def get_balance(self) -> Dict[str, float]:
        return self.balance

    def get_positions(self) -> Dict[str, float]:
        # In this simple spot model, positions are just non-base-currency balances
        return {k: v for k, v in self.balance.items() if k != self.base_currency}
