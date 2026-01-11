import pandas as pd
import logging
from typing import List, Dict, Any
from autotrade.strategies.base import Strategy
from autotrade.execution.paper import PaperExecutionEngine
from autotrade.risk.manager import RiskManager
from autotrade.config import config

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class Backtester:
    """
    Simulates strategy performance on historical data.
    """

    def __init__(self, strategy: Strategy, initial_balance: float = 10000.0, symbol: str = 'BTC/USDT'):
        self.strategy = strategy
        self.symbol = symbol
        self.execution_engine = PaperExecutionEngine(initial_balance=initial_balance)
        self.risk_manager = RiskManager()
        self.history: List[Dict] = [] # Stores daily equity
        self.trades: List[Dict] = []  # Stores trade details (not fully implemented in paper engine yet, so we track here)

    def run(self, data: pd.DataFrame):
        """
        Runs the backtest.
        Args:
            data (pd.DataFrame): OHLCV data.
        """
        logger.info(f"Starting backtest on {len(data)} candles...")

        # We need a window of data for the strategy to start working
        # Usually we step through line by line

        for i in range(len(data)):
            # Slice data up to current point (simulation of real-time)
            # Optimization: Many strategies only need the last N rows.
            # Passing full growing dataframe is slow O(N^2).
            # For MVP, we slice.
            if i < 50: # Assume minimal warm-up period
                continue

            current_slice = data.iloc[:i+1]
            current_bar = data.iloc[i]
            current_price = current_bar['close']
            current_time = current_slice.index[-1]

            # 1. Analyze
            signal = self.strategy.analyze(current_slice)

            # 2. Execute (Risk Managed)
            action = signal.get('action')

            if action == 'buy':
                balance = self.execution_engine.get_balance()
                # Ensure signal has price, or use current close
                if not signal.get('price'):
                     signal['price'] = current_price

                if self.risk_manager.check_trade_permission(signal, balance, self.symbol):
                    qty = self.risk_manager.calculate_quantity(signal, balance, self.symbol)

                    if qty > 0:
                        sl, tp = self.risk_manager.get_exit_prices(current_price, 'buy')
                        order = self.execution_engine.place_order(
                            self.symbol, 'buy', 'market', qty, price=current_price, stop_loss=sl, take_profit=tp
                        )
                        self.trades.append({
                            'timestamp': current_time,
                            'type': 'buy',
                            'price': current_price,
                            'amount': qty,
                            'cost': qty * current_price
                        })

            elif action == 'sell':
                # Sell everything logic
                positions = self.execution_engine.get_positions()
                base_currency = self.symbol.split('/')[0]
                qty = positions.get(base_currency, 0)

                if qty > 0:
                     self.execution_engine.place_order(self.symbol, 'sell', 'market', qty, price=current_price)
                     self.trades.append({
                            'timestamp': current_time,
                            'type': 'sell',
                            'price': current_price,
                            'amount': qty,
                            'revenue': qty * current_price
                        })

            # 3. Record Equity
            total_equity = self._calculate_total_equity(current_price)
            self.history.append({
                'timestamp': current_time,
                'equity': total_equity
            })

    def _calculate_total_equity(self, current_price: float) -> float:
        balance = self.execution_engine.get_balance()
        base_currency = self.symbol.split('/')[0]
        quote_currency = self.symbol.split('/')[1]

        cash = balance.get(quote_currency, 0)
        assets = balance.get(base_currency, 0)

        return cash + (assets * current_price)

    def calculate_metrics(self) -> Dict[str, float]:
        """
        Calculates performance metrics.
        """
        if not self.history:
            return {}

        df_history = pd.DataFrame(self.history)
        df_history.set_index('timestamp', inplace=True)

        initial_equity = df_history['equity'].iloc[0]
        final_equity = df_history['equity'].iloc[-1]

        total_return = ((final_equity - initial_equity) / initial_equity) * 100

        # Drawdown
        df_history['peak'] = df_history['equity'].cummax()
        df_history['drawdown'] = (df_history['equity'] - df_history['peak']) / df_history['peak']
        max_drawdown = df_history['drawdown'].min() * 100

        return {
            'total_return_pct': round(total_return, 2),
            'max_drawdown_pct': round(max_drawdown, 2),
            'final_equity': round(final_equity, 2),
            'trade_count': len(self.trades)
        }
