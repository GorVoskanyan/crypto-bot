import unittest
from unittest.mock import AsyncMock, patch
from autotrade.market_data.scanner import MarketScanner

class TestMarketScanner(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.scanner = MarketScanner()

    @patch('autotrade.market_data.scanner.retry_async')
    async def test_scan_top_volatile_symbols(self, mock_retry):
        mock_tickers = [
            {'symbol': 'BTCUSDT', 'quoteVolume': '100000000', 'highPrice': '52000', 'lowPrice': '50000', 'lastPrice': '51000', 'priceChangePercent': '4.0'},
            {'symbol': 'ETHUSDT', 'quoteVolume': '50000000', 'highPrice': '3100', 'lowPrice': '2800', 'lastPrice': '3000', 'priceChangePercent': '10.7'},
            {'symbol': 'SOLUSDT', 'quoteVolume': '20000000', 'highPrice': '110', 'lowPrice': '90', 'lastPrice': '100', 'priceChangePercent': '22.2'},
            {'symbol': 'DODGEUSDT', 'quoteVolume': '1000', 'highPrice': '1', 'lowPrice': '0.1', 'lastPrice': '0.5', 'priceChangePercent': '50.0'}, # Volume too low
            {'symbol': 'BTCUPUSDT', 'quoteVolume': '50000000', 'highPrice': '2', 'lowPrice': '1', 'lastPrice': '1.5', 'priceChangePercent': '50.0'} # Leverage token
        ]

        async def mock_retry_impl(coro_fn, **kwargs):
            return await coro_fn()

        mock_retry.side_effect = mock_retry_impl

        self.scanner.client = AsyncMock()
        self.scanner.client.futures_ticker = AsyncMock(return_value=mock_tickers)

        results = await self.scanner.scan_top_volatile_symbols(top_n=2, min_24h_volume_usdt=10_000_000.0)

        self.assertEqual(len(results), 2)
        # SOL (90->110 = 22.2% spread) should rank higher than ETH (2800->3100 = 10.7% spread)
        self.assertEqual(results[0]['symbol'], 'SOL/USDT')
        self.assertEqual(results[1]['symbol'], 'ETH/USDT')

if __name__ == '__main__':
    unittest.main()
