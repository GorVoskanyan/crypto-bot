import pandas as pd
import pandas_ta as ta
from typing import Dict, Any
from autotrade.strategies.base import Strategy

class SMACrossoverStrategy(Strategy):
    """
    Simple Moving Average Crossover Strategy.
    Buys when Short SMA crosses above Long SMA.
    Sells when Short SMA crosses below Long SMA.
    """

    def __init__(self, short_window: int = 10, long_window: int = 50):
        self.short_window = short_window
        self.long_window = long_window

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes data for SMA crossover.
        """
        if len(data) < self.long_window:
            return {'action': 'hold', 'reason': 'Not enough data'}

        # Calculate Indicators
        # Copy to avoid SettingWithCopy warning on the original df if needed, though pandas_ta handles this well usually.
        df = data.copy()

        # Calculate SMAs using pandas_ta
        # 'length' is the standard argument for pandas_ta functions
        df['sma_short'] = ta.sma(df['close'], length=self.short_window)
        df['sma_long'] = ta.sma(df['close'], length=self.long_window)

        # Get the last two rows to check for crossover
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        # Check if SMAs are calculated (not NaN)
        if pd.isna(last_row['sma_short']) or pd.isna(last_row['sma_long']):
             return {'action': 'hold', 'reason': 'Indicators not ready'}

        current_price = last_row['close']

        # Golden Cross: Short crosses above Long
        if prev_row['sma_short'] <= prev_row['sma_long'] and last_row['sma_short'] > last_row['sma_long']:
            return {
                'action': 'buy',
                'price': current_price,
                'metadata': {
                    'sma_short': last_row['sma_short'],
                    'sma_long': last_row['sma_long']
                }
            }

        # Death Cross: Short crosses below Long
        elif prev_row['sma_short'] >= prev_row['sma_long'] and last_row['sma_short'] < last_row['sma_long']:
             return {
                'action': 'sell',
                'price': current_price,
                'metadata': {
                    'sma_short': last_row['sma_short'],
                    'sma_long': last_row['sma_long']
                }
            }

        return {'action': 'hold', 'metadata': {'sma_short': last_row['sma_short'], 'sma_long': last_row['sma_long']}}
