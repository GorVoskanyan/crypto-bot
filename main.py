import asyncio
import logging
from autotrade.core.bot import MultiSymbolTradingBot
from autotrade.market_data.binance_stream import BinanceFuturesStreamer
from autotrade.market_data.scanner import MarketScanner
from autotrade.strategies.adaptive_selector import AdaptiveStrategySelector
from autotrade.strategies.confluence_strategy import ConfluenceStrategy
from autotrade.strategies.ema_trend_strategy import EMATrendStrategy
from autotrade.strategies.scalping_strategy import ScalpingStrategy
from autotrade.strategies.sma_crossover import SMACrossoverStrategy
from autotrade.execution.binance_futures import BinanceFuturesEngine
from autotrade.config import config

def get_strategy_factory(strategy_name: str):
    s_name = strategy_name.lower()
    if s_name == 'confluence':
        logging.info("🧠 Strategy Engine: Confluence (Bollinger + RSI + MACD + Volume)")
        return lambda: ConfluenceStrategy()
    elif s_name == 'ema_trend':
        logging.info("📈 Strategy Engine: EMA Trend Ribbon + ADX Filter")
        return lambda: EMATrendStrategy()
    elif s_name == 'scalping':
        logging.info("⚡ Strategy Engine: Scalping (RSI + Orderbook Imbalance)")
        return lambda: ScalpingStrategy()
    elif s_name == 'sma':
        logging.info("📊 Strategy Engine: SMA Crossover")
        return lambda: SMACrossoverStrategy()
    else:
        logging.info("🤖 Strategy Engine: Adaptive Strategy Selector (Automatic regime detection)")
        return lambda: AdaptiveStrategySelector()

async def resolve_trading_symbols(scanner: MarketScanner) -> list[str]:
    """Resolves active symbols using the MarketScanner or fallback config symbol."""
    if config.ENABLE_SCANNER:
        try:
            top_pairs = await scanner.scan_top_volatile_symbols(
                top_n=config.TOP_SYMBOLS_COUNT,
                min_24h_volume_usdt=config.MIN_24H_VOLUME_USDT
            )
            symbols = [p['symbol'] for p in top_pairs]
            if symbols:
                return symbols
        except Exception as e:
            logging.error(f"Failed to scan symbols, falling back to config symbol: {e}")

    return [config.TRADING_SYMBOL]

async def main():
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    logging.info(f"⚙️ Configuration: Strategy={config.STRATEGY} | Timeframe={config.TIMEFRAME} | Scanner={config.ENABLE_SCANNER} | Testnet={config.USE_TESTNET}")

    scanner = MarketScanner(
        api_key=config.API_KEY,
        api_secret=config.SECRET,
        testnet=config.USE_TESTNET
    )

    symbols = await resolve_trading_symbols(scanner)
    await scanner.close()

    logging.info(f"🎯 Selected Trading Symbols ({len(symbols)}): {', '.join(symbols)}")

    streamer = BinanceFuturesStreamer(
        api_key=config.API_KEY,
        api_secret=config.SECRET,
        testnet=config.USE_TESTNET
    )

    strategy_factory = get_strategy_factory(config.STRATEGY)

    engine = BinanceFuturesEngine(
        api_key=config.API_KEY,
        api_secret=config.SECRET,
        testnet=config.USE_TESTNET
    )

    bot = MultiSymbolTradingBot(
        streamer=streamer,
        strategy_factory=strategy_factory,
        engine=engine,
        symbols=symbols,
        timeframe=config.TIMEFRAME
    )

    try:
        await bot.run()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    finally:
        await streamer.close()
        await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
