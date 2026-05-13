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

    async def _keep_alive_listen_key(self, listen_key: str):
        while True:
            await asyncio.sleep(1800) # 30 mins
            try:
                await self.client.futures_stream_keepalive(listenKey=listen_key)
                logger.info("Listen Key kept alive")
            except Exception as e:
                logger.error(f"Failed to keep alive listen key: {e}")

    async def start_user_socket(self):
        if not self.bsm:
            await self.connect()

        listen_key = await self.client.futures_stream_get_listen_key()
        socket = self.bsm.futures_user_socket()

        # Start keep-alive task
        asyncio.create_task(self._keep_alive_listen_key(listen_key))

        async with socket as stream:
            while True:
                msg = await stream.recv()
                if msg:
                    for listener in self.listeners:
                        await listener.on_user_data(msg)

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
        socket = self.bsm.futures_depth_socket(symbol=binance_symbol)

        async with socket as stream:
            while True:
                msg = await stream.recv()
                if not msg:
                    continue

                # Handle both raw Binance and normalized python-binance formats
                bids = msg.get('b') or msg.get('bids')
                asks = msg.get('a') or msg.get('asks')

                if bids is None or asks is None:
                    continue

                orderbook = {
                    'bids': [[float(p), float(q)] for p, q in bids],
                    'asks': [[float(p), float(q)] for p, q in asks],
                    'timestamp': msg.get('E', msg.get('T', 0))
                }
                for listener in self.listeners:
                    await listener.on_orderbook(symbol, orderbook)

    async def close(self):
        if self.client:
            await self.client.close_connection()
