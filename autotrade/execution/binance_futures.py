import logging
from typing import Dict, Any, Optional, List
from binance import AsyncClient
from autotrade.execution.base import ExecutionEngine, Order
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class BinanceFuturesEngine(ExecutionEngine):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client: Optional[AsyncClient] = None

    async def _ensure_client(self):
        if not self.client:
            self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=self.testnet)

    async def set_leverage(self, symbol: str, leverage: int):
        await self._ensure_client()
        binance_symbol = symbol.replace('/', '')
        return await self.client.futures_change_leverage(symbol=binance_symbol, leverage=leverage)

    async def set_margin_mode(self, symbol: str, margin_mode: str):
        await self._ensure_client()
        binance_symbol = symbol.replace('/', '')
        # margin_mode should be 'ISOLATED' or 'CROSSED'
        try:
            return await self.client.futures_change_margin_type(symbol=binance_symbol, marginType=margin_mode.upper())
        except Exception as e:
            if "No need to change margin type" in str(e):
                return None
            raise e

    async def get_balance(self) -> Dict[str, float]:
        await self._ensure_client()
        account_info = await self.client.futures_account()
        balances = {}
        for asset in account_info['assets']:
            if float(asset['walletBalance']) > 0:
                balances[asset['asset']] = float(asset['walletBalance'])
        return balances

    async def get_positions(self) -> List[Dict[str, Any]]:
        await self._ensure_client()
        account_info = await self.client.futures_account()
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
        info = await self.client.futures_exchange_info()
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
        # Ensure we return a string that doesn't use scientific notation
        return format(precision, 'f').rstrip('0').rstrip('.')

    async def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: Optional[float] = None, stop_loss: Optional[float] = None, take_profit: Optional[float] = None, leverage: int = 1) -> Order:
        await self._ensure_client()
        binance_symbol = symbol.replace('/', '')

        # 1. Set leverage
        await self.set_leverage(symbol, leverage)

        # 2. Get symbol filters for precision
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

        res = await self.client.futures_create_order(**params)

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

        # TP/SL orders are usually placed separately in Binance Futures
        if stop_loss:
            sl_side = 'SELL' if side_upper == 'BUY' else 'BUY'
            formatted_sl = self._format_value(stop_loss, tick_size)
            await self.client.futures_create_order(
                symbol=binance_symbol,
                side=sl_side,
                type='STOP_MARKET',
                stopPrice=formatted_sl,
                closePosition='true'
            )

        if take_profit:
            tp_side = 'SELL' if side_upper == 'BUY' else 'BUY'
            formatted_tp = self._format_value(take_profit, tick_size)
            await self.client.futures_create_order(
                symbol=binance_symbol,
                side=tp_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=formatted_tp,
                closePosition='true'
            )

        return order

    async def get_funding_rate(self, symbol: str) -> float:
        await self._ensure_client()
        binance_symbol = symbol.replace('/', '')
        res = await self.client.futures_funding_rate(symbol=binance_symbol, limit=1)
        if res:
            return float(res[0]['fundingRate'])
        return 0.0

    async def close(self):
        if self.client:
            await self.client.close_connection()
