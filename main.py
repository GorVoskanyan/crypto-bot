import asyncio
import logging
from autotrade.core.bot import TradingBot
from autotrade.market_data.binance_stream import BinanceFuturesStreamer
from autotrade.strategies.scalping_strategy import ScalpingStrategy
from autotrade.execution.binance_futures import BinanceFuturesEngine
from autotrade.config import config

async def main():
    logging.basicConfig(level=config.LOG_LEVEL)

    symbol = "BTC/USDT"
    timeframe = "1m"

    streamer = BinanceFuturesStreamer(
        api_key=config.API_KEY,
        api_secret=config.SECRET,
        testnet=config.USE_TESTNET
    )

    strategy = ScalpingStrategy()

    engine = BinanceFuturesEngine(
        api_key=config.API_KEY,
        api_secret=config.SECRET,
        testnet=config.USE_TESTNET
    )

    bot = TradingBot(streamer, strategy, engine, symbol, timeframe)

    try:
        await bot.run()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    finally:
        await streamer.close()
        await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
