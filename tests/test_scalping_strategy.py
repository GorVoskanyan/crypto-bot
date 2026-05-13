import pytest
import pandas as pd
import asyncio
from autotrade.strategies.scalping_strategy import ScalpingStrategy

@pytest.mark.asyncio
async def test_scalping_strategy_hold():
    strategy = ScalpingStrategy()
    data = pd.DataFrame({
        'high': [100] * 20,
        'low': [90] * 20,
        'close': [95] * 20,
        'volume': [1000] * 20
    })
    signal = await strategy.analyze(data)
    assert signal['action'] == 'hold'

@pytest.mark.asyncio
async def test_scalping_strategy_buy_signal():
    strategy = ScalpingStrategy(rsi_oversold=70) # Force oversold for testing
    data = pd.DataFrame({
        'high': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119],
        'low': [90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'close': [95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80, 79, 78, 77, 76],
        'volume': [1000] * 20
    })
    orderbook = {
        'bids': [[75, 1000], [74, 1000]],
        'asks': [[77, 10], [78, 10]],
        'timestamp': 123456789
    }
    signal = await strategy.analyze(data, orderbook)
    assert signal['action'] == 'buy'
    assert 'sl_pct' in signal
    assert 'tp_pct' in signal
