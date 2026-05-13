import asyncio
import logging
from typing import Optional, Dict, Any
import pandas as pd
from autotrade.data.binance_stream import BinanceFuturesStreamer
from autotrade.data.base import StreamListener
from autotrade.strategies.base import Strategy
from autotrade.execution.binance_futures import BinanceFuturesEngine
from autotrade.risk.manager import RiskManager
from autotrade.notifications.telegram import TelegramNotificationProvider
from autotrade.config import config

logger = logging.getLogger(__name__)

class TradingBot(StreamListener):
    def __init__(self, streamer: BinanceFuturesStreamer, strategy: Strategy, engine: BinanceFuturesEngine, symbol: str, timeframe: str = '1m'):
        self.streamer = streamer
        self.strategy = strategy
        self.engine = engine
        self.risk_manager = RiskManager()
        self.symbol = symbol
        self.timeframe = timeframe

        self.ohlcv_data: pd.DataFrame = pd.DataFrame()
        self.current_orderbook: Dict[str, Any] = {}
        self.in_position = False

        self.notifier = None
        if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
            self.notifier = TelegramNotificationProvider(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID)

    def _notify(self, message: str):
        if self.notifier:
            self.notifier.send(message)

    async def initialize(self):
        logger.info(f"Initializing bot for {self.symbol}...")
        # Load historical data
        self.ohlcv_data = await self.streamer.fetch_ohlcv(self.symbol, self.timeframe, limit=100)

        # Set margin mode to ISOLATED
        try:
            await self.engine.set_margin_mode(self.symbol, 'ISOLATED')
        except Exception as e:
            logger.warning(f"Could not set margin mode: {e}")

        self.streamer.add_listener(self)
        logger.info("Initialization complete.")

    async def on_candle(self, symbol: str, timeframe: str, candle: dict):
        if symbol != self.symbol or timeframe != self.timeframe:
            return

        if candle['is_closed']:
            # Append new closed candle
            new_row = pd.DataFrame([candle])
            self.ohlcv_data = pd.concat([self.ohlcv_data, new_row], ignore_index=True).iloc[-100:]
            logger.debug(f"New candle for {self.symbol}")

            # Re-analyze on closed candle or every tick? For scalping, maybe every tick.
            # But indicators like RSI are usually better on closed candles.
            await self.process_strategy()

    async def on_orderbook(self, symbol: str, orderbook: dict):
        if symbol != self.symbol:
            return
        self.current_orderbook = orderbook
        # For ultra-fast scalping, we could call process_strategy here too.
        # But let's start with candle-based for stability.

    async def process_strategy(self):
        if self.in_position:
            # Check if we should exit? Or let SL/TP handle it.
            # For now, let SL/TP handle exits.
            # Check positions to see if we are still in trade
            positions = await self.engine.get_positions()
            if not any(p['symbol'] == self.symbol.replace('/', '') for p in positions):
                self.in_position = False
            return

        signal = await self.strategy.analyze(self.ohlcv_data, self.current_orderbook)
        action = signal.get('action')

        if action in ['buy', 'sell']:
            await self.execute_trade(signal)

    async def execute_trade(self, signal: Dict[str, Any]):
        action = signal['action']
        price = signal['price']

        # 1. Check funding rate
        funding_rate = await self.engine.get_funding_rate(self.symbol)
        if (action == 'buy' and funding_rate > 0.001) or (action == 'sell' and funding_rate < -0.001):
            logger.warning(f"Skipping trade due to high funding rate: {funding_rate}")
            return

        # 2. Risk Management
        balance = await self.engine.get_balance()
        quote_currency = self.symbol.split('/')[1]

        if balance.get(quote_currency, 0) < 10: # Min $10
            logger.warning("Insufficient balance")
            return

        sl_pct = signal.get('sl_pct', config.STOP_LOSS_PCT)
        tp_pct = signal.get('tp_pct', config.TAKE_PROFIT_PCT)

        sl_price = price * (1 - sl_pct) if action == 'buy' else price * (1 + sl_pct)
        tp_price = price * (1 + tp_pct) if action == 'buy' else price * (1 - tp_pct)

        leverage = self.risk_manager.calculate_dynamic_leverage(price, sl_price)
        amount = self.risk_manager.calculate_quantity(signal, balance, self.symbol, leverage)

        if amount <= 0:
            logger.warning("Calculated amount is 0")
            return

        # 3. Execution
        try:
            order = await self.engine.place_order(
                symbol=self.symbol,
                side=action,
                order_type='MARKET',
                amount=amount,
                stop_loss=sl_price,
                take_profit=tp_price,
                leverage=leverage
            )
            self.in_position = True
            msg = f"🚀 {action.upper()} {amount} {self.symbol} @ {price}\nLev: {leverage}x, SL: {sl_price:.2f}, TP: {tp_price:.2f}"
            logger.info(msg)
            self._notify(msg)
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            self._notify(f"❌ Error: {e}")

    async def run(self):
        await self.initialize()
        await asyncio.gather(
            self.streamer.start_kline_socket(self.symbol, self.timeframe),
            self.streamer.start_orderbook_socket(self.symbol)
        )
