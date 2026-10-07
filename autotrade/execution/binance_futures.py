import logging
from typing import Dict, Any, Optional, List
from binance import AsyncClient
from autotrade.execution.base import ExecutionEngine, Order
from autotrade.market_data.binance_stream import retry_async
from datetime import datetime

logger = logging.getLogger(__name__)

class BinanceFuturesEngine(ExecutionEngine):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client: Optional[AsyncClient] = None

    async def _ensure_client(self):
        if not self.client:
            self.client = await retry_async(
                lambda: AsyncClient.create(self.api_key, self.api_secret, testnet=self.testnet),
                max_retries=5,
                initial_delay=2.0
            )

    async def set_leverage(self, symbol: str, leverage: int):
        await self._ensure_client()
        binance_symbol = symbol.replace('/', '')

        async def _change_leverage():
            try:
                return await self.client.futures_change_leverage(symbol=binance_symbol, leverage=leverage)
            except Exception as e:
                err_str = str(e)
                if "-4161" in err_str or "Leverage reduction is not supported" in err_str:
                    logger.info(f"Leverage change skipped for {symbol} due to existing open position.")
                    return None
                raise e

        return await retry_async(_change_leverage, max_retries=3)

    async def set_margin_mode(self, symbol: str, margin_mode: str):
        await self._ensure_client()
        binance_symbol = symbol.replace('/', '')

        async def _change_margin():
            try:
                return await self.client.futures_change_margin_type(
                    symbol=binance_symbol,
                    marginType=margin_mode.upper()
                )
            except Exception as e:
                err_str = str(e)
                if "No need to change margin type" in err_str or "-4046" in err_str:
                    logger.info(f"Margin mode already set to {margin_mode.upper()} for {symbol}.")
                    return None
                raise e

        return await retry_async(_change_margin, max_retries=3)

    async def get_balance(self) -> Dict[str, float]:
        await self._ensure_client()
        account_info = await retry_async(lambda: self.client.futures_account(), max_retries=3)
        balances = {}
        for asset in account_info['assets']:
            if float(asset['walletBalance']) > 0:
                balances[asset['asset']] = float(asset['walletBalance'])
        return balances

    async def get_positions(self) -> List[Dict[str, Any]]:
        await self._ensure_client()
        account_info = await retry_async(lambda: self.client.futures_account(), max_retries=3)
        positions = []
        for pos in account_info['positions']:
            if float(pos['positionAmt']) != 0:
                positions.append({
                    'symbol': pos['symbol'],
                    'amount': float(pos['positionAmt']),
                    'entry_price': float(pos['entryPrice']),
                    'unrealized_pnl': float(pos['unrealizedProfit']),
                    'leverage': int(pos['leverage']),
                    'isolated': pos['isolated']
                })
        return positions

    async def get_symbol_info(self, symbol: str):
        await self._ensure_client()
        info = await retry_async(lambda: self.client.futures_exchange_info(), max_retries=3)
        binance_symbol = symbol.replace('/', '')
        for s in info['symbols']:
            if s['symbol'] == binance_symbol:
                return s
        return None

    def _format_value(self, value: float, step_size: str) -> str:
        import decimal
        d = decimal.Decimal(str(value))
        step = decimal.Decimal(step_size)
        remainder = d % step
        precision = d - remainder
        return format(precision, 'f').rstrip('0').rstrip('.')

    async def update_stop_loss(self, symbol: str, side: str, new_sl_price: float) -> bool:
        await self._ensure_client()
        binance_symbol = symbol.replace('/', '')

        try:
            open_orders = await retry_async(
                lambda: self.client.futures_get_open_orders(symbol=binance_symbol),
                max_retries=3
            )
            for o in open_orders:
                if o['type'] == 'STOP_MARKET':
                    await retry_async(
                        lambda: self.client.futures_cancel_order(symbol=binance_symbol, orderId=o['orderId']),
                        max_retries=3
                    )

            info = await self.get_symbol_info(symbol)
            price_filter = next(f for f in info['filters'] if f['filterType'] == 'PRICE_FILTER')
            tick_size = price_filter['tickSize']
            formatted_sl = self._format_value(new_sl_price, tick_size)

            sl_side = 'SELL' if side.upper() in ['BUY', 'LONG'] else 'BUY'

            async def _place_sl():
                try:
                    return await self.client.futures_create_order(
                        symbol=binance_symbol,
                        side=sl_side,
                        type='STOP_MARKET',
                        stopPrice=formatted_sl,
                        closePosition='true'
                    )
                except Exception as e:
                    err_str = str(e)
                    if "-4509" in err_str or "-2021" in err_str:
                        logger.warning(f"⚠️ Stop-Loss placement warning [{symbol}]: {err_str}")
                        return None
                    raise e

            await retry_async(_place_sl, max_retries=3)
            logger.info(f"✅ Stop-Loss updated to {formatted_sl} for {symbol}.")
            return True
        except Exception as e:
            logger.error(f"Failed to update Stop-Loss for {symbol}: {e}")
            return False

    async def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: Optional[float] = None, stop_loss: Optional[float] = None, take_profit: Optional[float] = None, leverage: int = 1) -> Order:
        await self._ensure_client()
        binance_symbol = symbol.replace('/', '')

        await self.set_leverage(symbol, leverage)

        info = await self.get_symbol_info(symbol)
        price_filter = next(f for f in info['filters'] if f['filterType'] == 'PRICE_FILTER')
        lot_size = next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')

        tick_size = price_filter['tickSize']
        step_size = lot_size['stepSize']

        formatted_amount = self._format_value(amount, step_size)

        side_upper = side.upper()
        type_upper = order_type.upper()

        params = {
            'symbol': binance_symbol,
            'side': side_upper,
            'type': type_upper,
            'quantity': formatted_amount,
        }

        if type_upper == 'LIMIT' and price:
            params['price'] = str(price)
            params['timeInForce'] = 'GTC'

        res = await retry_async(lambda: self.client.futures_create_order(**params), max_retries=3)

        order = Order(
            id=str(res['orderId']),
            symbol=symbol,
            side=side,
            type=order_type,
            amount=amount,
            price=float(res.get('price', 0)) or price,
            status='open',
            timestamp=datetime.fromtimestamp(res['updateTime'] / 1000.0)
        )

        if stop_loss or take_profit:
            import asyncio
            await asyncio.sleep(0.5)

        if stop_loss:
            sl_side = 'SELL' if side_upper == 'BUY' else 'BUY'
            formatted_sl = self._format_value(stop_loss, tick_size)

            async def _place_stop_loss():
                try:
                    return await self.client.futures_create_order(
                        symbol=binance_symbol,
                        side=sl_side,
                        type='STOP_MARKET',
                        stopPrice=formatted_sl,
                        closePosition='true'
                    )
                except Exception as e:
                    err_str = str(e)
                    if "-4509" in err_str or "-2021" in err_str:
                        logger.warning(f"⚠️ Stop Loss order warning for {symbol}: {err_str}")
                        return None
                    raise e

            await retry_async(_place_stop_loss, max_retries=3)

        if take_profit:
            tp_side = 'SELL' if side_upper == 'BUY' else 'BUY'
            formatted_tp = self._format_value(take_profit, tick_size)

            async def _place_take_profit():
                try:
                    return await self.client.futures_create_order(
                        symbol=binance_symbol,
                        side=tp_side,
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=formatted_tp,
                        closePosition='true'
                    )
                except Exception as e:
                    err_str = str(e)
                    if "-4509" in err_str or "-2021" in err_str:
                        logger.warning(f"⚠️ Take Profit order warning for {symbol}: {err_str}")
                        return None
                    raise e

            await retry_async(_place_take_profit, max_retries=3)

        return order

    async def get_funding_rate(self, symbol: str) -> float:
        await self._ensure_client()
        binance_symbol = symbol.replace('/', '')
        res = await retry_async(lambda: self.client.futures_funding_rate(symbol=binance_symbol, limit=1), max_retries=3)
        if res:
            return float(res[0]['fundingRate'])
        return 0.0

    async def close(self):
        if self.client:
            await self.client.close_connection()
