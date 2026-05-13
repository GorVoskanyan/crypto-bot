from abc import ABC, abstractmethod
import pandas as pd

class DataFetcher(ABC):
    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        pass

class StreamListener(ABC):
    @abstractmethod
    async def on_candle(self, symbol: str, timeframe: str, candle: dict):
        pass

    @abstractmethod
    async def on_orderbook(self, symbol: str, orderbook: dict):
        pass
