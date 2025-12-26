from abc import ABC, abstractmethod
from typing import Dict, Optional
from pydantic import BaseModel
from datetime import datetime

class Order(BaseModel):
    """
    Represents a trade order.
    """
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    type: str  # 'market' or 'limit'
    amount: float
    price: Optional[float] = None
    status: str  # 'open', 'closed', 'canceled'
    timestamp: datetime

class ExecutionEngine(ABC):
    """
    Abstract base class for order execution.
    """

    @abstractmethod
    def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: Optional[float] = None) -> Order:
        """
        Places an order.

        Args:
            symbol (str): The trading pair (e.g., 'BTC/USDT').
            side (str): 'buy' or 'sell'.
            order_type (str): 'market' or 'limit'.
            amount (float): The amount to trade (in base currency).
            price (float, optional): The price for limit orders.

        Returns:
            Order: The created order object.
        """
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        """
        Returns the current account balance.

        Returns:
            Dict[str, float]: Dictionary of currency balances (e.g., {'USDT': 1000.0, 'BTC': 0.5}).
        """
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, float]:
        """
        Returns current open positions.
        """
        pass
