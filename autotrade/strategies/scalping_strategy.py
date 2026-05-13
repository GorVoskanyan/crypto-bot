import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional
from autotrade.strategies.base import Strategy

class ScalpingStrategy(Strategy):
    """
    High-frequency scalping strategy for Binance Futures.
    Uses RSI, ATR (for dynamic SL/TP), and Order Book imbalance.
    """

    def __init__(self, rsi_period: int = 14, rsi_overbought: int = 70, rsi_oversold: int = 30, atr_period: int = 14):
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.atr_period = atr_period

    async def analyze(self, data: pd.DataFrame, orderbook: Dict[str, Any] = None) -> Dict[str, Any]:
        if len(data) < max(self.rsi_period, self.atr_period) + 1:
            return {'action': 'hold', 'reason': 'Insufficient data'}

        df = data.copy()

        # Technical Indicators
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)

        last_row = df.iloc[-1]
        current_price = last_row['close']
        atr = last_row['atr']
        rsi = last_row['rsi']

        # Order Book Imbalance (if available)
        imbalance = 0
        if orderbook:
            total_bids = sum([q for p, q in orderbook['bids'][:10]])
            total_asks = sum([q for p, q in orderbook['asks'][:10]])
            imbalance = (total_bids - total_asks) / (total_bids + total_asks)

        # Scalping Logic
        # 1. RSI-based entry
        # 2. Imbalance confirmation (optional)

        action = 'hold'
        if rsi < self.rsi_oversold:
            # Possible Long
            if imbalance > 0.2: # More buyers than sellers
                action = 'buy'
        elif rsi > self.rsi_overbought:
            # Possible Short
            if imbalance < -0.2: # More sellers than buyers
                action = 'sell'

        if action != 'hold':
            # Dynamic SL/TP based on ATR
            sl_dist = atr * 1.5
            tp_dist = atr * 2.0

            return {
                'action': action,
                'price': current_price,
                'sl_pct': sl_dist / current_price,
                'tp_pct': tp_dist / current_price,
                'metadata': {
                    'rsi': rsi,
                    'imbalance': imbalance,
                    'atr': atr
                }
            }

        return {'action': 'hold'}
