import asyncio
import logging
from typing import Optional, Dict, Any, List
import pandas as pd
from autotrade.market_data.binance_stream import BinanceFuturesStreamer
from autotrade.market_data.base import StreamListener
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
        logger.info(f"🚀 Initializing bot for {self.symbol}...")
        try:
            # 1. Load historical data
            logger.info("📡 Fetching historical OHLCV data...")
            self.ohlcv_data = await self.streamer.fetch_ohlcv(self.symbol, self.timeframe, limit=100)

            # 2. Set margin mode and check permissions
            logger.info("⚙️ Setting Margin Mode to ISOLATED...")
            try:
                await self.engine.set_margin_mode(self.symbol, 'ISOLATED')
                logger.info("✅ Margin Mode set to ISOLATED.")
            except Exception as e:
                if "code=-2015" in str(e):
                    logger.error("❌ CRITICAL ERROR: API Key Permissions (Code -2015)")
                    logger.error("   Your API key is valid but does NOT have 'Enable Futures' permission.")
                    logger.error("   Please go to Binance API Management and check the 'Enable Futures' box.")
                    logger.error(f"   Context: Attempted to set margin mode for {self.symbol}")
                    raise e
                logger.warning(f"⚠️ Could not set margin mode (might be already set): {e}")

            # 3. Connect listener
            self.streamer.add_listener(self)
            logger.info("🏁 Initialization complete. Starting real-time streams...")

        except Exception as e:
            logger.error(f"💥 FATAL ERROR during initialization: {e}")
            raise e

    async def on_candle(self, symbol: str, timeframe: str, candle: dict):
        if symbol != self.symbol or timeframe != self.timeframe:
            return

        if candle['is_closed']:
            # Append new closed candle
            new_row = pd.DataFrame([candle])
            self.ohlcv_data = pd.concat([self.ohlcv_data, new_row], ignore_index=True).iloc[-100:]
            logger.info(f"🆕 Candle Closed: {candle['close']} | Vol: {candle['volume']}")

        # In scalping, we analyze every tick for faster entry
        await self.process_strategy()

    async def on_user_data(self, data: dict):
        event_type = data.get('e')
        if event_type == 'ACCOUNT_UPDATE':
            logger.info("💰 Account updated (Balance/Position change)")
        elif event_type == 'ORDER_TRADE_UPDATE':
            trade = data['o']
            if trade['X'] == 'FILLED':
                logger.info(f"✅ Order FILLED: {trade['S']} {trade['q']} @ {trade['p']}")
                self.in_position = trade['S'] == 'BUY' or trade['S'] == 'SELL'
            elif trade['X'] == 'CANCELED':
                 logger.info(f"❌ Order CANCELED: {trade['S']} {trade['i']}")

    async def on_orderbook(self, symbol: str, orderbook: dict):
        if symbol != self.symbol:
            return
        self.current_orderbook = orderbook

        best_bid = orderbook['bids'][0][0]
        best_ask = orderbook['asks'][0][0]
        spread = best_ask - best_bid

        # Log market status every 5 seconds (approx)
        if int(orderbook['timestamp']) % 5000 < 100:
            logger.info(f"📊 {self.symbol} | Bid: {best_bid} | Ask: {best_ask} | Spread: {spread:.2f}")

    async def process_strategy(self):
        # 1. Monitor Open Positions (PnL)
        try:
            positions = await self.engine.get_positions()
            symbol_no_slash = self.symbol.replace('/', '')
            active_pos = next((p for p in positions if p['symbol'] == symbol_no_slash), None)

            if active_pos:
                self.in_position = True
                pnl = active_pos['unrealized_pnl']
                # Log PnL occasionally
                if asyncio.get_event_loop().time() % 10 < 0.5:
                    logger.info(f"💰 Position: {active_pos['amount']} @ {active_pos['entry_price']} | Unrealized PnL: {pnl:.2f} USDT")
                return
            else:
                if self.in_position:
                    logger.info("ℹ️ Position closed.")
                    self.in_position = False
        except Exception as e:
            logger.error(f"Error checking positions: {e}")

        # 2. Strategy Analysis
        signal = await self.strategy.analyze(self.ohlcv_data, self.current_orderbook)
        action = signal.get('action')

        if action in ['buy', 'sell']:
            logger.info(f"🎯 Strategy Signal: {action.upper()} @ {signal['price']}")
            await self.execute_trade(signal)
        else:
            # Only log "no signal" every 30 seconds to keep console clean but informative
            if asyncio.get_event_loop().time() % 30 < 0.5:
                reason = signal.get('reason', 'no signal')
                logger.info(f"💤 Monitoring... {self.symbol} @ {self.ohlcv_data.iloc[-1]['close'] if not self.ohlcv_data.empty else ''} | {reason}")

    async def execute_trade(self, signal: Dict[str, Any]):
        action = signal['action']
        price = signal['price']

        # 1. Check funding rate
        try:
            funding_rate = await self.engine.get_funding_rate(self.symbol)
            if (action == 'buy' and funding_rate > 0.001) or (action == 'sell' and funding_rate < -0.001):
                logger.warning(f"Skipping trade due to high funding rate: {funding_rate}")
                return
        except Exception as e:
            logger.warning(f"Could not fetch funding rate: {e}")

        # 2. Risk Management
        try:
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
            self.streamer.start_orderbook_socket(self.symbol),
            self.streamer.start_user_socket()
        )
