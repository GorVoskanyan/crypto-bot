import pandas as pd
import pandas_ta as ta
from typing import Dict, Any
from autotrade.strategies.base import Strategy

class EMATrendStrategy(Strategy):
    """
    Trend-following strategy utilizing EMA Ribbon (9, 21, 50, 200)
    filtered by ADX trend intensity and ATR dynamic SL/TP.
    """

    def __init__(
        self,
        fast_ema: int = 9,
        mid_ema: int = 21,
        slow_ema: int = 50,
        baseline_ema: int = 200,
        adx_period: int = 14,
        adx_threshold: float = 20.0,
        atr_period: int = 14,
        rr_ratio: float = 2.0
    ):
        self.fast_ema = fast_ema
        self.mid_ema = mid_ema
        self.slow_ema = slow_ema
        self.baseline_ema = baseline_ema
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.atr_period = atr_period
        self.rr_ratio = rr_ratio

    async def analyze(self, data: pd.DataFrame, orderbook: Dict[str, Any] = None) -> Dict[str, Any]:
        min_bars = max(self.baseline_ema, self.adx_period, self.atr_period) + 5
        if len(data) < min_bars:
            return {'action': 'hold', 'reason': f'Insufficient data (need at least {min_bars} bars)'}

        df = data.copy()

        # EMAs
        df['ema_fast'] = ta.ema(df['close'], length=self.fast_ema)
        df['ema_mid'] = ta.ema(df['close'], length=self.mid_ema)
        df['ema_slow'] = ta.ema(df['close'], length=self.slow_ema)
        df['ema_base'] = ta.ema(df['close'], length=self.baseline_ema)

        # ADX
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=self.adx_period)
        if adx_df is not None and not adx_df.empty:
            adx_col = [c for c in adx_df.columns if c.startswith('ADX_')][0]
            df['adx'] = adx_df[adx_col]
        else:
            df['adx'] = 0

        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        price = float(last_row['close'])
        prev_price = float(prev_row['close'])
        ema_fast = float(last_row['ema_fast'])
        ema_mid = float(last_row['ema_mid'])
        ema_slow = float(last_row['ema_slow'])
        ema_base = float(last_row['ema_base'])
        adx = float(last_row['adx'])
        atr = float(last_row['atr'])

        if pd.isna(ema_fast) or pd.isna(ema_mid) or pd.isna(ema_slow) or pd.isna(adx) or pd.isna(atr):
            return {'action': 'hold', 'reason': 'Indicator values contain NaN'}

        # Strong trend filter
        strong_trend = adx >= self.adx_threshold

        # Bullish alignment: fast > mid > slow, price above baseline
        bullish_alignment = (ema_fast > ema_mid > ema_slow) and (price > ema_base if not pd.isna(ema_base) else True)
        # Bearish alignment: fast < mid < slow, price below baseline
        bearish_alignment = (ema_fast < ema_mid < ema_slow) and (price < ema_base if not pd.isna(ema_base) else True)

        # Crossover / Pullback entry signal
        # Fast EMA crosses above Mid EMA OR Price crosses above Fast EMA in bullish alignment
        prev_ema_fast = float(prev_row['ema_fast'])
        prev_ema_mid = float(prev_row['ema_mid'])

        bullish_trigger = (prev_ema_fast <= prev_ema_mid and ema_fast > ema_mid) or (prev_price <= prev_ema_fast and price > ema_fast)
        bearish_trigger = (prev_ema_fast >= prev_ema_mid and ema_fast < ema_mid) or (prev_price >= prev_ema_fast and price < ema_fast)

        if bullish_alignment and strong_trend and bullish_trigger:
            sl_dist = max(atr * 1.5, price * 0.008)
            tp_dist = sl_dist * self.rr_ratio
            return {
                'action': 'buy',
                'price': price,
                'sl_pct': sl_dist / price,
                'tp_pct': tp_dist / price,
                'metadata': {
                    'strategy': 'EMATrend',
                    'adx': adx,
                    'ema_fast': ema_fast,
                    'ema_mid': ema_mid,
                    'atr': atr
                }
            }
        elif bearish_alignment and strong_trend and bearish_trigger:
            sl_dist = max(atr * 1.5, price * 0.008)
            tp_dist = sl_dist * self.rr_ratio
            return {
                'action': 'sell',
                'price': price,
                'sl_pct': sl_dist / price,
                'tp_pct': tp_dist / price,
                'metadata': {
                    'strategy': 'EMATrend',
                    'adx': adx,
                    'ema_fast': ema_fast,
                    'ema_mid': ema_mid,
                    'atr': atr
                }
            }

        return {'action': 'hold', 'reason': 'No trend alignment or weak ADX'}
