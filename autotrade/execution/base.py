from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
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
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str  # 'open', 'closed', 'canceled'
    timestamp: datetime

class ExecutionEngine(ABC):
    """
    Abstract base class for order execution.
    """

    @abstractmethod
    async def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: Optional[float] = None, stop_loss: Optional[float] = None, take_profit: Optional[float] = None, leverage: int = 1) -> Order:
        """
        Places an order.

        Args:
            symbol (str): The trading pair (e.g., 'BTC/USDT').
            side (str): 'buy' or 'sell'.
            order_type (str): 'market' or 'limit'.
            amount (float): The amount to trade (in base currency).
            price (float, optional): The price for limit orders.
            stop_loss (float, optional): Stop loss price.
            take_profit (float, optional): Take profit price.
            leverage (int): Leverage to use.

        Returns:
            Order: The created order object.
        """
        pass

    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """
        Returns the current account balance.

        Returns:
            Dict[str, float]: Dictionary of currency balances (e.g., {'USDT': 1000.0, 'BTC': 0.5}).
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Returns current open positions.
        """
        pass

    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int):
        """
        Sets leverage for a symbol.
        """
        pass

    @abstractmethod
    async def set_margin_mode(self, symbol: str, margin_mode: str):
        """
        Sets margin mode (ISOLATED or CROSS).
        """
        pass
