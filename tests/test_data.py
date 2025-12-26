import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from autotrade.data.exchange import ExchangeDataFetcher

class TestExchangeDataFetcher(unittest.TestCase):

    @patch('autotrade.data.exchange.ccxt')
    def test_initialization(self, mock_ccxt):
        """Test that the exchange is initialized correctly."""
        # Setup mock
        mock_exchange_class = MagicMock()
        setattr(mock_ccxt, 'binance', mock_exchange_class)

        # Initialize fetcher
        fetcher = ExchangeDataFetcher('binance', 'key', 'secret')

        # Verify
        mock_exchange_class.assert_called_with({
            'apiKey': 'key',
            'secret': 'secret',
            'enableRateLimit': True,
        })
        self.assertEqual(fetcher.exchange_id, 'binance')

    @patch('autotrade.data.exchange.ccxt')
    def test_fetch_ohlcv_success(self, mock_ccxt):
        """Test successful data fetching and normalization."""
        # Setup mock return data (timestamp, open, high, low, close, volume)
        mock_data = [
            [1609459200000, 29000.0, 29100.0, 28900.0, 29050.0, 100.0],
            [1609462800000, 29050.0, 29200.0, 29000.0, 29150.0, 150.0]
        ]

        mock_exchange_instance = MagicMock()
        mock_exchange_instance.fetch_ohlcv.return_value = mock_data

        mock_exchange_class = MagicMock()
        mock_exchange_class.return_value = mock_exchange_instance
        setattr(mock_ccxt, 'binance', mock_exchange_class)

        # Execute
        fetcher = ExchangeDataFetcher('binance')
        df = fetcher.fetch_ohlcv('BTC/USDT')

        # Verify interactions
        mock_exchange_instance.fetch_ohlcv.assert_called_with('BTC/USDT', '1h', limit=100)

        # Verify DataFrame structure
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertListEqual(list(df.columns), ['open', 'high', 'low', 'close', 'volume'])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df.index))
        self.assertEqual(df.iloc[0]['close'], 29050.0)

    @patch('autotrade.data.exchange.ccxt')
    def test_fetch_ohlcv_error(self, mock_ccxt):
        """Test error handling during fetch."""
        mock_exchange_instance = MagicMock()
        mock_exchange_instance.fetch_ohlcv.side_effect = Exception("Network Error")

        mock_exchange_class = MagicMock()
        mock_exchange_class.return_value = mock_exchange_instance
        setattr(mock_ccxt, 'binance', mock_exchange_class)

        fetcher = ExchangeDataFetcher('binance')

        with self.assertRaises(Exception):
            fetcher.fetch_ohlcv('BTC/USDT')

if __name__ == '__main__':
    unittest.main()
