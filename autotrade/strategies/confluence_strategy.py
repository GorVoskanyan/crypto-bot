import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional
from autotrade.strategies.base import Strategy

class ConfluenceStrategy(Strategy):
    """
    High-probability Confluence Strategy for Binance Futures.
    Combines Bollinger Bands, RSI, MACD, Volume, and ATR to identify high-conviction reversal setups.
    Enforces a strict Risk:Reward ratio of at least 1:2.
    """

    def __init__(
        self,
        bb_length: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14,
        rsi_oversold: float = 35.0,
        rsi_overbought: float = 65.0,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        volume_ma_period: int = 20,
        atr_period: int = 14
    ):
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.volume_ma_period = volume_ma_period
        self.atr_period = atr_period

    async def analyze(self, data: pd.DataFrame, orderbook: Dict[str, Any] = None) -> Dict[str, Any]:
        min_required = max(self.bb_length, self.macd_slow + self.macd_signal, self.volume_ma_period) + 5
        if len(data) < min_required:
            return {'action': 'hold', 'reason': 'Insufficient data'}

        df = data.copy()

        # 1. Bollinger Bands
        bb = ta.bbands(df['close'], length=self.bb_length, std=self.bb_std)
        if bb is None or bb.empty:
            return {'action': 'hold', 'reason': 'Failed to calculate Bollinger Bands'}

        # Columns in pandas_ta bbands: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        lower_band_col = [c for c in bb.columns if c.startswith('BBL')][0]
        upper_band_col = [c for c in bb.columns if c.startswith('BBU')][0]
        middle_band_col = [c for c in bb.columns if c.startswith('BBM')][0]

        df['bb_lower'] = bb[lower_band_col]
        df['bb_upper'] = bb[upper_band_col]
        df['bb_middle'] = bb[middle_band_col]

        # 2. RSI
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)

        # 3. MACD
        macd = ta.macd(df['close'], fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
        if macd is None or macd.empty:
            return {'action': 'hold', 'reason': 'Failed to calculate MACD'}

        macd_col = [c for c in macd.columns if c.startswith('MACD_')][0]
        signal_col = [c for c in macd.columns if c.startswith('MACDs_')][0]
        hist_col = [c for c in macd.columns if c.startswith('MACDh_')][0]

        df['macd'] = macd[macd_col]
        df['macd_signal'] = macd[signal_col]
        df['macd_hist'] = macd[hist_col]

        # 4. Volume MA
        df['vol_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()

        # 5. ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)

        # Extract last row & previous row for confirmation
        last = df.iloc[-1]
        prev = df.iloc[-2]

        current_price = last['close']
        atr = last['atr']
        rsi = last['rsi']
        volume = last['volume']
        vol_ma = last['vol_ma']

        if pd.isna(atr) or pd.isna(rsi) or pd.isna(last['macd']) or pd.isna(last['bb_lower']):
            return {'action': 'hold', 'reason': 'Indicator values contain NaN'}

        # --- Confluence Criteria ---
        # Volume Filter: Volume must be above 80% of volume MA
        high_volume = volume >= (vol_ma * 0.8) if not pd.isna(vol_ma) and vol_ma > 0 else True

        # LONG Setup:
        # 1. Price is at/below lower Bollinger Band or previously touched it
        bb_long_trigger = (last['low'] <= last['bb_lower']) or (prev['low'] <= prev['bb_lower'])
        # 2. RSI is oversold (< 35)
        rsi_long_trigger = rsi <= self.rsi_oversold or prev['rsi'] <= self.rsi_oversold
        # 3. MACD Histogram is turning bullish (histogram is increasing or positive)
        macd_long_trigger = last['macd_hist'] > prev['macd_hist'] or last['macd'] > last['macd_signal']

        # SHORT Setup:
        # 1. Price is at/above upper Bollinger Band or previously touched it
        bb_short_trigger = (last['high'] >= last['bb_upper']) or (prev['high'] >= prev['bb_upper'])
        # 2. RSI is overbought (> 65)
        rsi_short_trigger = rsi >= self.rsi_overbought or prev['rsi'] >= self.rsi_overbought
        # 3. MACD Histogram is turning bearish (histogram is decreasing or negative)
        macd_short_trigger = last['macd_hist'] < prev['macd_hist'] or last['macd'] < last['macd_signal']

        action = 'hold'
        if bb_long_trigger and rsi_long_trigger and macd_long_trigger and high_volume:
            action = 'buy'
        elif bb_short_trigger and rsi_short_trigger and macd_short_trigger and high_volume:
            action = 'sell'

        if action != 'hold':
            # Dynamic Risk:Reward Ratio 1:2 using ATR
            sl_dist = atr * 1.2
            tp_dist = atr * 2.5 # Risk:Reward = 1:2.08

            sl_pct = sl_dist / current_price
            tp_pct = tp_dist / current_price

            return {
                'action': action,
                'price': float(current_price),
                'sl_pct': float(sl_pct),
                'tp_pct': float(tp_pct),
                'metadata': {
                    'rsi': float(rsi),
                    'macd_hist': float(last['macd_hist']),
                    'bb_lower': float(last['bb_lower']),
                    'bb_upper': float(last['bb_upper']),
                    'atr': float(atr)
                }
            }

        return {'action': 'hold'}
