import pandas as pd
import pandas_ta as ta
from typing import Dict, Any
from autotrade.strategies.base import Strategy

class ConfluenceStrategy(Strategy):
    """
    High-probability confluence strategy combining Bollinger Bands, RSI, MACD,
    Volume MA, and ATR dynamic SL/TP levels.
    Requires at least 1:2 Risk-to-Reward ratio.
    """

    def __init__(
        self,
        bb_length: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14,
        rsi_overbought: float = 65.0,
        rsi_oversold: float = 35.0,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        volume_ma_period: int = 20,
        atr_period: int = 14,
        rr_ratio: float = 2.0
    ):
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.volume_ma_period = volume_ma_period
        self.atr_period = atr_period
        self.rr_ratio = rr_ratio

    async def analyze(self, data: pd.DataFrame, orderbook: Dict[str, Any] = None) -> Dict[str, Any]:
        min_bars = max(self.bb_length, self.rsi_period, self.macd_slow + self.macd_signal, self.volume_ma_period, self.atr_period) + 5
        if len(data) < min_bars:
            return {'action': 'hold', 'reason': f'Insufficient data (need at least {min_bars} bars)'}

        df = data.copy()

        # 1. Bollinger Bands
        bb = ta.bbands(df['close'], length=self.bb_length, std=self.bb_std)
        if bb is None or bb.empty:
            return {'action': 'hold', 'reason': 'Failed to calculate Bollinger Bands'}

        # Identify columns
        lower_col = [c for c in bb.columns if c.startswith('BBL')][0]
        mid_col = [c for c in bb.columns if c.startswith('BBM')][0]
        upper_col = [c for c in bb.columns if c.startswith('BBU')][0]

        df['bb_lower'] = bb[lower_col]
        df['bb_mid'] = bb[mid_col]
        df['bb_upper'] = bb[upper_col]

        # 2. RSI
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)

        # 3. MACD
        macd = ta.macd(df['close'], fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
        if macd is None or macd.empty:
            return {'action': 'hold', 'reason': 'Failed to calculate MACD'}

        macd_line_col = [c for c in macd.columns if c.startswith('MACD_')][0]
        macd_signal_col = [c for c in macd.columns if c.startswith('MACDs_')][0]
        macd_hist_col = [c for c in macd.columns if c.startswith('MACDh_')][0]

        df['macd'] = macd[macd_line_col]
        df['macd_signal'] = macd[macd_signal_col]
        df['macd_hist'] = macd[macd_hist_col]

        # 4. Volume MA
        df['vol_ma'] = ta.sma(df['volume'], length=self.volume_ma_period)

        # 5. ATR for Dynamic SL/TP
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        price = float(last_row['close'])
        rsi = float(last_row['rsi'])
        bb_lower = float(last_row['bb_lower'])
        bb_upper = float(last_row['bb_upper'])
        macd_hist = float(last_row['macd_hist'])
        prev_macd_hist = float(prev_row['macd_hist'])
        volume = float(last_row['volume'])
        vol_ma = float(last_row['vol_ma']) if not pd.isna(last_row['vol_ma']) else 0
        atr = float(last_row['atr'])

        if pd.isna(rsi) or pd.isna(atr) or pd.isna(macd_hist) or pd.isna(bb_lower):
            return {'action': 'hold', 'reason': 'Indicator values contain NaN'}

        volume_confirmed = volume > vol_ma * 0.8  # Reasonable volume check

        # Confluence Buy Signal (LONG)
        # Price near/below lower BB, RSI oversold or turning up, MACD momentum increasing, decent volume
        buy_confluence = (
            price <= bb_lower * 1.002 and
            rsi < self.rsi_oversold and
            macd_hist > prev_macd_hist and
            volume_confirmed
        )

        # Confluence Sell Signal (SHORT)
        # Price near/above upper BB, RSI overbought or turning down, MACD momentum decreasing, decent volume
        sell_confluence = (
            price >= bb_upper * 0.998 and
            rsi > self.rsi_overbought and
            macd_hist < prev_macd_hist and
            volume_confirmed
        )

        if buy_confluence:
            sl_dist = max(atr * 1.5, price * 0.008)
            tp_dist = sl_dist * self.rr_ratio
            return {
                'action': 'buy',
                'price': price,
                'sl_pct': sl_dist / price,
                'tp_pct': tp_dist / price,
                'metadata': {
                    'strategy': 'Confluence',
                    'rsi': rsi,
                    'bb_lower': bb_lower,
                    'macd_hist': macd_hist,
                    'atr': atr
                }
            }
        elif sell_confluence:
            sl_dist = max(atr * 1.5, price * 0.008)
            tp_dist = sl_dist * self.rr_ratio
            return {
                'action': 'sell',
                'price': price,
                'sl_pct': sl_dist / price,
                'tp_pct': tp_dist / price,
                'metadata': {
                    'strategy': 'Confluence',
                    'rsi': rsi,
                    'bb_upper': bb_upper,
                    'macd_hist': macd_hist,
                    'atr': atr
                }
            }

        return {'action': 'hold', 'reason': 'No confluence alignment'}
