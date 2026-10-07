import logging
import asyncio
from typing import List, Dict, Any, Optional
from binance import AsyncClient
from autotrade.market_data.binance_stream import retry_async

logger = logging.getLogger(__name__)

class MarketScanner:
    """
    Scans Binance Futures USDT pairs to identify the top N most volatile
    and liquid trading symbols based on 24h volume and price movement range.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False):
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

    async def scan_top_volatile_symbols(
        self,
        top_n: int = 5,
        min_24h_volume_usdt: float = 10_000_000.0,
        exclude_symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetches 24h ticker data for all USDT futures pairs, filters out low volume or leverage tokens,
        and returns the top_n symbols sorted by volatility (high - low percentage spread).
        """
        await self._ensure_client()
        if exclude_symbols is None:
            exclude_symbols = []

        # Standardize excluded symbols format (e.g. BTC/USDT -> BTCUSDT)
        excluded_clean = {s.replace('/', '') for s in exclude_symbols}

        logger.info("🔍 Scanning Binance Futures markets for top volatile symbols...")

        tickers = await retry_async(lambda: self.client.futures_ticker(), max_retries=3)

        candidates = []
        for t in tickers:
            symbol = t['symbol']

            # Filter: Only USDT pairs, exclude leverage tokens or custom excluded list
            if not symbol.endswith('USDT'):
                continue
            if symbol in excluded_clean:
                continue
            if any(token in symbol for token in ['UPUSDT', 'DOWNUSDT', 'BULLUSDT', 'BEARUSDT']):
                continue

            try:
                quote_volume = float(t.get('quoteVolume', 0))
                high_price = float(t.get('highPrice', 0))
                low_price = float(t.get('lowPrice', 0))
                last_price = float(t.get('lastPrice', 0))
                price_change_pct = abs(float(t.get('priceChangePercent', 0)))

                if quote_volume < min_24h_volume_usdt or last_price == 0:
                    continue

                # Calculate 24h price volatility range percentage: (High - Low) / Low
                volatility_range_pct = ((high_price - low_price) / low_price) * 100.0 if low_price > 0 else 0.0

                # Formatted CCXT style symbol (e.g., BTC/USDT)
                formatted_symbol = f"{symbol[:-4]}/USDT"

                candidates.append({
                    'symbol': formatted_symbol,
                    'raw_symbol': symbol,
                    'last_price': last_price,
                    'volume_24h': quote_volume,
                    'price_change_pct': price_change_pct,
                    'volatility_range_pct': volatility_range_pct
                })
            except (ValueError, TypeError) as e:
                continue

        # Sort candidates primarily by volatility range percentage descending
        sorted_candidates = sorted(candidates, key=lambda x: x['volatility_range_pct'], reverse=True)
        top_symbols = sorted_candidates[:top_n]

        logger.info(f"✅ Found Top {len(top_symbols)} Volatile Pairs:")
        for idx, item in enumerate(top_symbols, 1):
            logger.info(
                f"   #{idx} {item['symbol']} | Volatility 24h: {item['volatility_range_pct']:.2f}% | "
                f"24h Vol: ${item['volume_24h']:,.0f} USDT | Change: {item['price_change_pct']:+.2f}%"
            )

        return top_symbols

    async def close(self):
        if self.client:
            await self.client.close_connection()
