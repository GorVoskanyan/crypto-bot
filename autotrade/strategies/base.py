from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class Strategy(ABC):
    """
    Abstract base class for trading strategies.
    """

    @abstractmethod
    async def analyze(self, data: pd.DataFrame, orderbook: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyzes market data to generate trading signals.

        Args:
            data (pd.DataFrame): OHLCV data.
            orderbook (Dict[str, Any], optional): Real-time orderbook data.

        Returns:
            Dict[str, Any]: A dictionary containing the signal.
            Example: {'action': 'buy', 'price': 10000.0, 'metadata': {...}}
            Action can be 'buy', 'sell', or 'hold'.
        """
        pass
