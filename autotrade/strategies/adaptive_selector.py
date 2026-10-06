import pandas as pd
import pandas_ta as ta
import logging
from typing import Dict, Any, Optional
from autotrade.strategies.base import Strategy
from autotrade.strategies.scalping_strategy import ScalpingStrategy
from autotrade.strategies.ema_trend_strategy import EMATrendStrategy
from autotrade.strategies.confluence_strategy import ConfluenceStrategy
from autotrade.strategies.sma_crossover import SMACrossoverStrategy

logger = logging.getLogger(__name__)

class AdaptiveStrategySelector(Strategy):
    """
    Dynamically analyzes the market regime (trending, volatile/range-bound, low volatility)
    for a given coin and delegates signal generation to the optimal strategy.
    """

    def __init__(
        self,
        adx_period: int = 14,
        adx_trending_threshold: float = 25.0,
        bb_length: int = 20,
        bb_std: float = 2.0,
        atr_period: int = 14
    ):
        self.adx_period = adx_period
        self.adx_trending_threshold = adx_trending_threshold
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.atr_period = atr_period

        # Sub-strategies
        self.ema_trend_strategy = EMATrendStrategy()
        self.confluence_strategy = ConfluenceStrategy()
        self.scalping_strategy = ScalpingStrategy()
        self.sma_crossover_strategy = SMACrossoverStrategy()

    def detect_market_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates ADX and BB Bandwidth to classify current market state:
        - 'trending': High ADX (>= 25)
        - 'ranging': Moderate ADX, wide BB (high relative volatility)
        - 'scalp': Low ADX (< 25), fast opportunities or orderbook imbalance
        """
        min_bars = max(self.adx_period, self.bb_length, self.atr_period) + 5
        if len(df) < min_bars:
            return {'regime': 'unknown', 'adx': 0.0, 'bandwidth': 0.0}

        # ADX calculation
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=self.adx_period)
        adx_val = 0.0
        if adx_df is not None and not adx_df.empty:
            adx_col = [c for c in adx_df.columns if c.startswith('ADX_')][0]
            adx_val = float(adx_df[adx_col].iloc[-1]) if not pd.isna(adx_df[adx_col].iloc[-1]) else 0.0

        # BB Bandwidth calculation
        bb = ta.bbands(df['close'], length=self.bb_length, std=self.bb_std)
        bandwidth = 0.0
        if bb is not None and not bb.empty:
            bandwidth_col = [c for c in bb.columns if c.startswith('BBB_')][0]
            bandwidth = float(bb[bandwidth_col].iloc[-1]) if not pd.isna(bb[bandwidth_col].iloc[-1]) else 0.0

        if adx_val >= self.adx_trending_threshold:
            regime = 'trending'
        elif bandwidth > 2.0: # Moderate/High volatility range
            regime = 'ranging'
        else:
            regime = 'scalp'

        return {
            'regime': regime,
            'adx': adx_val,
            'bandwidth': bandwidth
        }

    async def analyze(self, data: pd.DataFrame, orderbook: Dict[str, Any] = None) -> Dict[str, Any]:
        if len(data) < 30:
            return {'action': 'hold', 'reason': 'Insufficient data for market regime analysis'}

        df = data.copy()
        regime_info = self.detect_market_regime(df)
        regime = regime_info['regime']

        # Delegate analysis based on market regime
        if regime == 'trending':
            signal = await self.ema_trend_strategy.analyze(df, orderbook)
            active_strategy_name = 'EMA Trend'
        elif regime == 'ranging':
            signal = await self.confluence_strategy.analyze(df, orderbook)
            active_strategy_name = 'Confluence'
        else:
            # High-frequency scalp or range bound
            signal = await self.scalping_strategy.analyze(df, orderbook)
            active_strategy_name = 'Scalping'

        # If secondary signal was 'hold' in trending/ranging, try Confluence as backup
        if signal.get('action') == 'hold' and regime == 'trending':
            backup_signal = await self.confluence_strategy.analyze(df, orderbook)
            if backup_signal.get('action') in ['buy', 'sell']:
                signal = backup_signal
                active_strategy_name = 'Confluence (Backup)'

        if signal.get('action') in ['buy', 'sell']:
            if 'metadata' not in signal:
                signal['metadata'] = {}
            signal['metadata']['selected_regime'] = regime
            signal['metadata']['active_strategy'] = active_strategy_name
            signal['metadata']['adx'] = regime_info['adx']

        return signal
