import asyncio
import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from binance import AsyncClient, BinanceSocketManager
from autotrade.market_data.base import DataFetcher, StreamListener

logger = logging.getLogger(__name__)

class BinanceFuturesStreamer(DataFetcher):
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client: Optional[AsyncClient] = None
        self.bsm: Optional[BinanceSocketManager] = None
        self.listeners: List[StreamListener] = []

    async def connect(self):
        self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=self.testnet)
        self.bsm = BinanceSocketManager(self.client)

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        if not self.client:
            await self.connect()

        # CCXT uses 'BTC/USDT', Binance uses 'BTCUSDT'
        binance_symbol = symbol.replace('/', '')

        klines = await self.client.futures_klines(symbol=binance_symbol, interval=timeframe, limit=limit)

        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    def add_listener(self, listener: StreamListener):
        self.listeners.append(listener)

    async def start_kline_socket(self, symbol: str, timeframe: str):
        if not self.bsm:
            await self.connect()

        binance_symbol = symbol.replace('/', '')
        socket = self.bsm.kline_futures_socket(symbol=binance_symbol, interval=timeframe)

        async with socket as stream:
            while True:
                msg = await stream.recv()
                if msg and msg['e'] == 'kline':
                    kline = msg['k']
                    candle = {
                        'timestamp': pd.to_datetime(kline['t'], unit='ms'),
                        'open': float(kline['o']),
                        'high': float(kline['h']),
                        'low': float(kline['l']),
                        'close': float(kline['c']),
                        'volume': float(kline['v']),
                        'is_closed': kline['x']
                    }
                    for listener in self.listeners:
                        await listener.on_candle(symbol, timeframe, candle)

    async def start_orderbook_socket(self, symbol: str):
        if not self.bsm:
            await self.connect()

        binance_symbol = symbol.replace('/', '')
        socket = self.bsm.depth_futures_socket(symbol=binance_symbol)

        async with socket as stream:
            while True:
                msg = await stream.recv()
                if msg:
                    orderbook = {
                        'bids': [[float(p), float(q)] for p, q in msg['b']],
                        'asks': [[float(p), float(q)] for p, q in msg['a']],
                        'timestamp': msg['E']
                    }
                    for listener in self.listeners:
                        await listener.on_orderbook(symbol, orderbook)

    async def close(self):
        if self.client:
            await self.client.close_connection()
