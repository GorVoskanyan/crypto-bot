import pandas as pd
from typing import Dict, Any, Optional
from autotrade.strategies.base import Strategy

class SMACrossoverStrategy(Strategy):
    """
    Simple Moving Average (SMA) Crossover Strategy.
    Generates a Buy signal when the short-term SMA crosses above the long-term SMA (Golden Cross).
    Generates a Sell signal when the short-term SMA crosses below the long-term SMA (Death Cross).
    """

    def __init__(self, short_window: int = 5, long_window: int = 20):
        self.short_window = short_window
        self.long_window = long_window

    async def analyze(self, data: pd.DataFrame, orderbook: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyzes historical data to find SMA crossover signals.
        """
        if len(data) < self.long_window:
            return {'action': 'hold', 'reason': 'Not enough data'}

        df = data.copy()

        # Calculate short and long SMAs
        df['sma_short'] = df['close'].rolling(window=self.short_window).mean()
        df['sma_long'] = df['close'].rolling(window=self.long_window).mean()

        # Ensure we have at least 2 valid historical rows of both SMAs to check for crossover
        if len(df) < 2 or df['sma_short'].isnull().iloc[-1] or df['sma_long'].isnull().iloc[-1] or \
           df['sma_short'].isnull().iloc[-2] or df['sma_long'].isnull().iloc[-2]:
            return {'action': 'hold', 'reason': 'Not enough data'}

        short_prev = df['sma_short'].iloc[-2]
        long_prev = df['sma_long'].iloc[-2]
        short_curr = df['sma_short'].iloc[-1]
        long_curr = df['sma_long'].iloc[-1]

        current_price = df['close'].iloc[-1]

        # Check for Crossovers
        # Golden Cross (Buy)
        if short_prev <= long_prev and short_curr > long_curr:
            return {
                'action': 'buy',
                'price': float(current_price),
                'metadata': {
                    'short_sma': float(short_curr),
                    'long_sma': float(long_curr)
                }
            }

        # Death Cross (Sell)
        elif short_prev >= long_prev and short_curr < long_curr:
            return {
                'action': 'sell',
                'price': float(current_price),
                'metadata': {
                    'short_sma': float(short_curr),
                    'long_sma': float(long_curr)
                }
            }

        return {'action': 'hold'}
