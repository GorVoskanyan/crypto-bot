import asyncio
import logging
from autotrade.core.bot import TradingBot
from autotrade.market_data.binance_stream import BinanceFuturesStreamer
from autotrade.strategies.adaptive_selector import AdaptiveStrategySelector
from autotrade.strategies.confluence_strategy import ConfluenceStrategy
from autotrade.strategies.ema_trend_strategy import EMATrendStrategy
from autotrade.strategies.scalping_strategy import ScalpingStrategy
from autotrade.strategies.sma_crossover import SMACrossoverStrategy
from autotrade.execution.binance_futures import BinanceFuturesEngine
from autotrade.config import config

def get_strategy(strategy_name: str):
    strategy_name = strategy_name.lower()
    if strategy_name == 'confluence':
        logging.info("🧠 Initializing Strategy: Confluence (Bollinger + RSI + MACD + Volume)")
        return ConfluenceStrategy()
    elif strategy_name == 'ema_trend':
        logging.info("📈 Initializing Strategy: EMA Trend Ribbon + ADX Filter")
        return EMATrendStrategy()
    elif strategy_name == 'scalping':
        logging.info("⚡ Initializing Strategy: Scalping (RSI + Orderbook Imbalance)")
        return ScalpingStrategy()
    elif strategy_name == 'sma':
        logging.info("📊 Initializing Strategy: SMA Crossover")
        return SMACrossoverStrategy()
    else:
        logging.info("🤖 Initializing Strategy: Adaptive Strategy Selector (Automatic regime detection)")
        return AdaptiveStrategySelector()

async def main():
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    symbol = config.TRADING_SYMBOL
    timeframe = config.TIMEFRAME
    strategy_type = config.STRATEGY

    logging.info(f"⚙️ Configuration: Symbol={symbol} | Timeframe={timeframe} | Strategy={strategy_type} | Testnet={config.USE_TESTNET}")

    streamer = BinanceFuturesStreamer(
        api_key=config.API_KEY,
        api_secret=config.SECRET,
        testnet=config.USE_TESTNET
    )

    strategy = get_strategy(strategy_type)

    engine = BinanceFuturesEngine(
        api_key=config.API_KEY,
        api_secret=config.SECRET,
        testnet=config.USE_TESTNET
    )

    bot = TradingBot(streamer, strategy, engine, symbol, timeframe)

    try:
        await bot.run()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    finally:
        await streamer.close()
        await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
