import asyncio
import logging
import time
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

class SymbolContext:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.ohlcv_data: pd.DataFrame = pd.DataFrame()
        self.current_orderbook: Dict[str, Any] = {}
        self.in_position = False
        self.position_side = None
        self.entry_price = 0.0
        self.highest_price = 0.0
        self.lowest_price = float('inf')
        self.current_sl_price = 0.0

        self.last_orderbook_log = 0.0
        self.last_monitoring_log = 0.0
        self.last_pnl_log = 0.0

class MultiSymbolTradingBot(StreamListener):
    def __init__(
        self,
        streamer: BinanceFuturesStreamer,
        strategy_factory: Any,
        engine: BinanceFuturesEngine,
        symbols: List[str],
        timeframe: str = '5m'
    ):
        self.streamer = streamer
        self.strategy_factory = strategy_factory
        self.engine = engine
        self.risk_manager = RiskManager()
        self.symbols = symbols
        self.timeframe = timeframe

        self.contexts: Dict[str, SymbolContext] = {s: SymbolContext(s) for s in symbols}
        self.strategies: Dict[str, Strategy] = {s: strategy_factory() for s in symbols}

        self.last_position_check = 0.0
        self.cached_positions = []

        self.last_balance_check = 0.0
        self.cached_balances: Dict[str, float] = {}

        self.notifier = None
        if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
            self.notifier = TelegramNotificationProvider(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID)
            self._setup_telegram_commands()

    def _notify(self, message: str):
        if self.notifier:
            self.notifier.send(message)

    def _setup_telegram_commands(self):
        if not self.notifier:
            return

        self.notifier.register_command('/status', self._cmd_status)
        self.notifier.register_command('/balance', self._cmd_balance)
        self.notifier.register_command('/closeall', self._cmd_closeall)
        self.notifier.register_command('/topcoins', self._cmd_topcoins)
        self.notifier.register_command('/help', self._cmd_help)
        self.notifier.start_command_listener()

    async def _cmd_status(self) -> str:
        msg = f"📊 *AutoTrade Bot Status*\n"
        msg += f"• *Symbols:* {', '.join(self.symbols)}\n"
        msg += f"• *Timeframe:* {self.timeframe}\n"
        msg += f"• *Circuit Breaker:* {'🔴 TRIPPED' if self.risk_manager.circuit_breaker_tripped else '🟢 OK'}\n\n"

        positions = await self.engine.get_positions()
        if not positions:
            msg += "• *Open Positions:* None\n"
        else:
            msg += f"• *Active Positions ({len(positions)}):*\n"
            for p in positions:
                msg += f"  - `{p['symbol']}`: {p['amount']} @ {p['entry_price']} | PnL: {p['unrealized_pnl']:.2f} USDT\n"

        return msg

    async def _cmd_balance(self) -> str:
        try:
            balances = await self.engine.get_balance()
            self.cached_balances = balances
            self.last_balance_check = time.time()
            msg = "💰 *Account Balances*\n"
            for asset, bal in balances.items():
                msg += f"• *{asset}:* {bal:.2f}\n"
            return msg
        except Exception as e:
            return f"❌ Error fetching balance: {e}"

    async def _cmd_closeall(self) -> str:
        """Emergency command to close all active open positions using reduceOnly market orders."""
        msg = "🚨 *Emergency Close All Initiated*\n"
        try:
            positions = await self.engine.get_positions()
            if not positions:
                return "ℹ️ No open positions to close."

            for p in positions:
                raw_symbol = p['symbol']
                amt = abs(p['amount'])
                close_side = 'SELL' if p['amount'] > 0 else 'BUY'

                formatted_symbol = f"{raw_symbol[:-4]}/USDT" if raw_symbol.endswith('USDT') else raw_symbol

                # 1. Cancel all open orders for symbol
                try:
                    await self.engine.client.futures_cancel_all_open_orders(symbol=raw_symbol)
                except Exception as ce:
                    logger.warning(f"Could not cancel open orders for {raw_symbol}: {ce}")

                # 2. Get symbol step size precision
                info = await self.engine.get_symbol_info(formatted_symbol)
                lot_size = next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')
                step_size = lot_size['stepSize']
                formatted_qty = self.engine._format_value(amt, step_size)

                # 3. Place MARKET order with reduceOnly=True (no leverage modification)
                await self.engine.client.futures_create_order(
                    symbol=raw_symbol,
                    side=close_side,
                    type='MARKET',
                    quantity=formatted_qty,
                    reduceOnly='true'
                )

                if formatted_symbol in self.contexts:
                    ctx = self.contexts[formatted_symbol]
                    ctx.in_position = False
                    ctx.entry_price = 0.0

                msg += f"✅ Closed position for `{raw_symbol}` ({formatted_qty} units)\n"

            self.last_position_check = 0.0
            self.last_balance_check = 0.0
            return msg
        except Exception as e:
            logger.error(f"Emergency close failed: {e}")
            return f"💥 Emergency close failed: {e}"

    async def _cmd_topcoins(self) -> str:
        return f"🎯 *Active Tracked Symbols ({len(self.symbols)}):*\n" + "\n".join([f"• `{s}`" for s in self.symbols])

    async def _cmd_help(self) -> str:
        return (
            "🤖 *AutoTrade Telegram Commands*\n"
            "• `/status` - Live bot status, positions & PnL\n"
            "• `/balance` - Current account balances\n"
            "• `/topcoins` - Tracked volatile symbols\n"
            "• `/closeall` - Emergency close all positions\n"
            "• `/help` - Command list"
        )

    async def initialize(self):
        logger.info(f"🚀 Initializing Multi-Symbol Bot for {len(self.symbols)} pairs: {', '.join(self.symbols)}...")
        try:
            for symbol in self.symbols:
                logger.info(f"📡 Fetching historical OHLCV data for {symbol} (300 candles)...")
                ctx = self.contexts[symbol]
                ctx.ohlcv_data = await self.streamer.fetch_ohlcv(symbol, self.timeframe, limit=300)

                logger.info(f"⚙️ Setting Margin Mode for {symbol} to ISOLATED...")
                try:
                    await self.engine.set_margin_mode(symbol, 'ISOLATED')
                except Exception as e:
                    if "code=-2015" in str(e):
                        logger.error("❌ CRITICAL ERROR: API Key Permissions (Code -2015)")
                        raise e
                    logger.warning(f"⚠️ Could not set margin mode for {symbol}: {e}")

            self.streamer.add_listener(self)
            logger.info("🏁 Initialization complete. Starting real-time streams for all symbols...")

        except Exception as e:
            logger.error(f"💥 FATAL ERROR during multi-symbol initialization: {e}")
            raise e

    async def on_candle(self, symbol: str, timeframe: str, candle: dict):
        if symbol not in self.contexts or timeframe != self.timeframe:
            return

        ctx = self.contexts[symbol]
        if candle['is_closed']:
            new_row = pd.DataFrame([candle])
            ctx.ohlcv_data = pd.concat([ctx.ohlcv_data, new_row], ignore_index=True).iloc[-300:]
            logger.info(f"🆕 Candle Closed [{symbol}]: {candle['close']} | Vol: {candle['volume']}")

        await self.process_symbol_strategy(symbol)

    async def on_user_data(self, data: dict):
        event_type = data.get('e')
        if event_type == 'ACCOUNT_UPDATE':
            logger.info("💰 Account updated (Balance/Position change)")
            self.last_position_check = 0.0
            self.last_balance_check = 0.0
        elif event_type == 'ORDER_TRADE_UPDATE':
            trade = data['o']
            if trade['X'] == 'FILLED':
                logger.info(f"✅ Order FILLED: {trade['s']} {trade['S']} {trade['q']} @ {trade['p']}")
                self.last_position_check = 0.0
                self.last_balance_check = 0.0
            elif trade['X'] == 'CANCELED':
                 logger.info(f"❌ Order CANCELED: {trade['s']} {trade['S']} {trade['i']}")

    async def on_orderbook(self, symbol: str, orderbook: dict):
        if symbol not in self.contexts:
            return

        ctx = self.contexts[symbol]
        ctx.current_orderbook = orderbook

        now = time.time()
        best_bid = orderbook['bids'][0][0] if orderbook.get('bids') else 0
        best_ask = orderbook['asks'][0][0] if orderbook.get('asks') else 0
        spread = best_ask - best_bid

        if now - ctx.last_orderbook_log >= 15.0:
            ctx.last_orderbook_log = now
            logger.info(f"📊 {symbol} | Bid: {best_bid} | Ask: {best_ask} | Spread: {spread:.2f}")

        await self.process_symbol_strategy(symbol)

    async def process_strategy(self):
        for symbol in self.symbols:
            await self.process_symbol_strategy(symbol)

    async def _get_throttled_balance(self) -> Dict[str, float]:
        now = time.time()
        if now - self.last_balance_check >= 10.0 or not self.cached_balances:
            self.last_balance_check = now
            self.cached_balances = await self.engine.get_balance()
        return self.cached_balances

    async def process_symbol_strategy(self, symbol: str):
        now = time.time()
        ctx = self.contexts[symbol]
        strategy = self.strategies[symbol]

        current_price = 0.0
        if ctx.current_orderbook and ctx.current_orderbook.get('bids'):
            current_price = ctx.current_orderbook['bids'][0][0]
        elif not ctx.ohlcv_data.empty:
            current_price = ctx.ohlcv_data.iloc[-1]['close']

        # 1. Position Monitoring & Trailing Stop / Break-Even Evaluation
        try:
            if now - self.last_position_check >= 5.0:
                self.last_position_check = now
                self.cached_positions = await self.engine.get_positions()

            symbol_no_slash = symbol.replace('/', '')
            active_pos = next((p for p in self.cached_positions if p['symbol'] == symbol_no_slash), None)

            if active_pos:
                ctx.in_position = True
                pnl = active_pos['unrealized_pnl']
                amt = active_pos['amount']
                ctx.position_side = 'BUY' if amt > 0 else 'SELL'
                ctx.entry_price = active_pos['entry_price']

                if current_price > 0:
                    ctx.highest_price = max(ctx.highest_price, current_price)
                    ctx.lowest_price = min(ctx.lowest_price, current_price)

                if now - ctx.last_pnl_log >= 15.0:
                    ctx.last_pnl_log = now
                    logger.info(f"💰 Position [{symbol}]: {amt} @ {ctx.entry_price} | PnL: {pnl:.2f} USDT")

                if current_price > 0 and ctx.current_sl_price > 0:
                    trail_res = self.risk_manager.evaluate_trailing_and_breakeven(
                        side=ctx.position_side,
                        entry_price=ctx.entry_price,
                        current_price=current_price,
                        highest_price=ctx.highest_price,
                        lowest_price=ctx.lowest_price,
                        current_sl_price=ctx.current_sl_price
                    )

                    if trail_res['update_sl']:
                        new_sl = trail_res['new_sl_price']
                        logger.info(f"🛡️ {trail_res['reason']} [{symbol}]: Updating Stop-Loss to {new_sl:.2f}")
                        sl_updated = await self.engine.update_stop_loss(symbol, ctx.position_side, new_sl)
                        if sl_updated:
                            ctx.current_sl_price = new_sl
                            self._notify(f"🛡️ [{symbol}] {trail_res['reason']}: New SL @ {new_sl:.2f}")

                return
            else:
                if ctx.in_position:
                    logger.info(f"ℹ️ Position closed [{symbol}].")
                    ctx.in_position = False
                    ctx.entry_price = 0.0
                    ctx.highest_price = 0.0
                    ctx.lowest_price = float('inf')
                    ctx.current_sl_price = 0.0
        except Exception as e:
            logger.error(f"Error checking position/trailing stop for {symbol}: {e}")

        # Check Circuit Breaker
        try:
            balance = await self._get_throttled_balance()
            quote_currency = symbol.split('/')[1]
            tot_bal = balance.get(quote_currency, 0.0)

            if self.risk_manager.is_circuit_breaker_active(tot_bal):
                if now - ctx.last_monitoring_log >= 30.0:
                    ctx.last_monitoring_log = now
                    logger.warning(f"🛑 Circuit Breaker Active (Daily Drawdown Limit Hit). Trading paused for {symbol}.")
                return
        except Exception as e:
            pass

        # 2. Strategy Analysis
        signal = await strategy.analyze(ctx.ohlcv_data, ctx.current_orderbook)
        action = signal.get('action')

        if action in ['buy', 'sell']:
            logger.info(f"🎯 Strategy Signal [{symbol}]: {action.upper()} @ {signal['price']}")
            await self.execute_trade(symbol, signal)
        else:
            if now - ctx.last_monitoring_log >= 20.0:
                ctx.last_monitoring_log = now
                reason = signal.get('reason', 'no entry signal')
                last_price = ctx.ohlcv_data.iloc[-1]['close'] if not ctx.ohlcv_data.empty else 'N/A'
                logger.info(f"💤 Monitoring {symbol} @ {last_price} | {reason}")

    async def execute_trade(self, symbol: str, signal: Dict[str, Any]):
        action = signal['action']
        price = signal['price']
        ctx = self.contexts[symbol]

        try:
            balance = await self._get_throttled_balance()
            quote_currency = symbol.split('/')[1]
            tot_bal = balance.get(quote_currency, 0.0)

            if self.risk_manager.is_circuit_breaker_active(tot_bal):
                logger.warning(f"Skipping trade [{symbol}] because Daily Drawdown Circuit Breaker is active.")
                return

            if tot_bal < 10:
                logger.warning(f"Insufficient balance to execute trade for {symbol}")
                return

            funding_rate = await self.engine.get_funding_rate(symbol)
            max_fr = config.MAX_FUNDING_RATE
            if (action == 'buy' and funding_rate > max_fr) or (action == 'sell' and funding_rate < -max_fr):
                logger.warning(f"Skipping trade [{symbol}] due to high funding rate: {funding_rate:.6f} (Limit: +/-{max_fr:.6f})")
                return

            sl_pct = signal.get('sl_pct', config.STOP_LOSS_PCT)
            tp_pct = signal.get('tp_pct', config.TAKE_PROFIT_PCT)

            sl_price = price * (1 - sl_pct) if action == 'buy' else price * (1 + sl_pct)
            tp_price = price * (1 + tp_pct) if action == 'buy' else price * (1 - tp_pct)

            leverage = self.risk_manager.calculate_dynamic_leverage(price, sl_price)
            amount = self.risk_manager.calculate_quantity(signal, balance, symbol, leverage)

            if amount <= 0:
                logger.warning(f"Calculated amount is 0 for {symbol}")
                return

            order = await self.engine.place_order(
                symbol=symbol,
                side=action,
                order_type='MARKET',
                amount=amount,
                stop_loss=sl_price,
                take_profit=tp_price,
                leverage=leverage
            )
            ctx.in_position = True
            ctx.position_side = action.upper()
            ctx.entry_price = price
            ctx.highest_price = price
            ctx.lowest_price = price
            ctx.current_sl_price = sl_price
            self.last_position_check = 0.0
            self.last_balance_check = 0.0

            msg = f"🚀 {action.upper()} {amount} {symbol} @ {price}\nLev: {leverage}x, SL: {sl_price:.2f}, TP: {tp_price:.2f}"
            logger.info(msg)
            self._notify(msg)
        except Exception as e:
            logger.error(f"Trade execution failed for {symbol}: {e}")
            self._notify(f"❌ Error [{symbol}]: {e}")

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(15)
            await self.process_strategy()

    async def run(self):
        await self.initialize()

        tasks = [self.streamer.start_user_socket(), self._heartbeat_loop()]
        for symbol in self.symbols:
            tasks.append(self.streamer.start_kline_socket(symbol, self.timeframe))
            tasks.append(self.streamer.start_orderbook_socket(symbol))

        await asyncio.gather(*tasks)

class TradingBot(MultiSymbolTradingBot):
    def __init__(self, streamer: BinanceFuturesStreamer, strategy: Strategy, engine: BinanceFuturesEngine, symbol: str, timeframe: str = '1m'):
        super().__init__(
            streamer=streamer,
            strategy_factory=lambda: strategy,
            engine=engine,
            symbols=[symbol],
            timeframe=timeframe
        )
        self.symbol = symbol
        self.strategy = strategy

    @property
    def ohlcv_data(self):
        return self.contexts[self.symbol].ohlcv_data

    @ohlcv_data.setter
    def ohlcv_data(self, df):
        self.contexts[self.symbol].ohlcv_data = df

    @property
    def current_orderbook(self):
        return self.contexts[self.symbol].current_orderbook

    @current_orderbook.setter
    def current_orderbook(self, ob):
        self.contexts[self.symbol].current_orderbook = ob

    @property
    def in_position(self):
        return self.contexts[self.symbol].in_position

    @in_position.setter
    def in_position(self, val):
        self.contexts[self.symbol].in_position = val
