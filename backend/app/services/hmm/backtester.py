"""Backtesting engine for strategy evaluation."""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .strategy import Signal, StrategyParams


@dataclass
class Trade:
    """Represents a single trade."""

    entry_date: pd.Timestamp
    exit_date: Optional[pd.Timestamp]
    entry_price: float
    exit_price: Optional[float]
    direction: str  # "LONG" or "SHORT"
    size: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    regime_at_entry: str = ""

    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization."""
        return {
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "direction": self.direction,
            "size": self.size,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "regime_at_entry": self.regime_at_entry,
        }


@dataclass
class BacktestResult:
    """Results of a backtest run."""

    total_return: float
    buy_hold_return: float
    alpha: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    profit_factor: float
    trades: List[Trade]
    equity_curve: pd.Series
    drawdown_curve: pd.Series

    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization."""
        return {
            "total_return": self.total_return,
            "buy_hold_return": self.buy_hold_return,
            "alpha": self.alpha,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": [
                {"timestamp": idx.isoformat() if hasattr(idx, "isoformat") else str(idx), "value": float(val)}
                for idx, val in self.equity_curve.items()
            ],
            "drawdown_curve": [
                {"timestamp": idx.isoformat() if hasattr(idx, "isoformat") else str(idx), "value": float(val)}
                for idx, val in self.drawdown_curve.items()
            ],
        }


class Backtester:
    """
    Backtesting engine for HMM regime-based strategies.

    Supports:
    - Configurable leverage
    - Slippage simulation
    - Commission calculation
    - Stop Loss / Take Profit
    - Trailing Stop
    - Maximum hold duration
    """

    def __init__(
        self,
        leverage: float = 1.0,
        slippage_pct: float = 0.001,  # 0.1% slippage
        commission_pct: float = 0.001,  # 0.1% commission
        initial_capital: float = 10000.0,
        strategy_params: Optional[StrategyParams] = None,
    ):
        """
        Initialize backtester.

        Args:
            leverage: Trading leverage (1x - 10x)
            slippage_pct: Slippage as percentage of price
            commission_pct: Commission as percentage of trade value
            initial_capital: Starting capital
            strategy_params: Strategy parameters including risk management
        """
        self.leverage = min(max(leverage, 1.0), 10.0)  # Clamp 1-10
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        self.initial_capital = initial_capital
        self.strategy_params = strategy_params or StrategyParams()

    def run(
        self, df: pd.DataFrame, signals_df: pd.DataFrame
    ) -> BacktestResult:
        """
        Run backtest on historical data with signals.

        Args:
            df: DataFrame with OHLCV data
            signals_df: DataFrame with signal column

        Returns:
            BacktestResult with all metrics
        """
        # Align data
        common_idx = df.index.intersection(signals_df.index)
        prices = df.loc[common_idx, "Close"].values
        highs = df.loc[common_idx, "High"].values if "High" in df.columns else prices
        lows = df.loc[common_idx, "Low"].values if "Low" in df.columns else prices
        signals = signals_df.loc[common_idx, "signal"].values
        regimes = signals_df.loc[common_idx, "regime"].values
        dates = common_idx

        # Risk management params
        sp = self.strategy_params
        stop_loss_pct = sp.stop_loss_pct
        take_profit_pct = sp.take_profit_pct
        trailing_stop_pct = sp.trailing_stop_pct
        max_hold_periods = sp.max_hold_periods
        exit_on_regime_change = sp.exit_on_regime_change

        # Initialize tracking variables
        capital = self.initial_capital
        position = 0.0  # Current position size
        position_direction = None  # "LONG" or "SHORT"
        entry_price = 0.0
        entry_date = None
        entry_regime = ""
        periods_held = 0
        highest_since_entry = 0.0  # For trailing stop (LONG)
        lowest_since_entry = float("inf")  # For trailing stop (SHORT)

        trades: List[Trade] = []
        equity = [capital]

        for i in range(1, len(prices)):
            current_price = prices[i]
            current_high = highs[i]
            current_low = lows[i]
            current_signal = signals[i]
            current_regime = regimes[i]
            prev_signal = signals[i - 1]

            # Update equity for open position
            if position != 0:
                if position_direction == "LONG":
                    unrealized_pnl = position * (current_price - entry_price)
                else:  # SHORT
                    unrealized_pnl = position * (entry_price - current_price)
                current_equity = capital + unrealized_pnl * self.leverage
            else:
                current_equity = capital

            equity.append(current_equity)

            # === CHECK EXIT CONDITIONS FOR OPEN POSITION ===
            should_exit = False
            exit_reason = ""

            if position != 0:
                periods_held += 1

                # Update trailing stop trackers
                if position_direction == "LONG":
                    highest_since_entry = max(highest_since_entry, current_high)
                else:
                    lowest_since_entry = min(lowest_since_entry, current_low)

                # Calculate current P&L percentage
                if position_direction == "LONG":
                    current_pnl_pct = (current_price - entry_price) / entry_price
                else:
                    current_pnl_pct = (entry_price - current_price) / entry_price

                # 1. Check Stop Loss
                if stop_loss_pct > 0 and current_pnl_pct <= -stop_loss_pct:
                    should_exit = True
                    exit_reason = "stop_loss"

                # 2. Check Take Profit
                if take_profit_pct > 0 and current_pnl_pct >= take_profit_pct:
                    should_exit = True
                    exit_reason = "take_profit"

                # 3. Check Trailing Stop
                if trailing_stop_pct > 0 and not should_exit:
                    if position_direction == "LONG":
                        trailing_stop_price = highest_since_entry * (1 - trailing_stop_pct)
                        if current_price <= trailing_stop_price:
                            should_exit = True
                            exit_reason = "trailing_stop"
                    else:  # SHORT
                        trailing_stop_price = lowest_since_entry * (1 + trailing_stop_pct)
                        if current_price >= trailing_stop_price:
                            should_exit = True
                            exit_reason = "trailing_stop"

                # 4. Check Max Hold Periods
                if max_hold_periods > 0 and periods_held >= max_hold_periods:
                    should_exit = True
                    exit_reason = "max_hold"

                # 5. Check Regime Change Exit
                if exit_on_regime_change and not should_exit:
                    if position_direction == "LONG" and current_regime not in sp.bullish_regimes:
                        should_exit = True
                        exit_reason = "regime_change"
                    elif position_direction == "SHORT" and current_regime not in sp.bearish_regimes:
                        should_exit = True
                        exit_reason = "regime_change"

                # 6. Check Signal Change
                signal_changed = current_signal != prev_signal
                if signal_changed and not should_exit:
                    if sp.exit_on_opposite_signal:
                        should_exit = True
                        exit_reason = "signal_change"

            # === EXECUTE EXIT ===
            if should_exit and position != 0:
                exit_price = self._apply_slippage(
                    current_price, position_direction == "SHORT"
                )

                if position_direction == "LONG":
                    pnl = position * (exit_price - entry_price)
                else:
                    pnl = position * (entry_price - exit_price)

                # Apply leverage and commission
                pnl = pnl * self.leverage
                commission = abs(position * exit_price * self.commission_pct)
                pnl -= commission

                pnl_pct = pnl / capital * 100

                trade = Trade(
                    entry_date=entry_date,
                    exit_date=dates[i],
                    entry_price=entry_price,
                    exit_price=exit_price,
                    direction=position_direction,
                    size=position,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    regime_at_entry=entry_regime,
                )
                trades.append(trade)

                capital += pnl
                position = 0.0
                position_direction = None
                periods_held = 0
                highest_since_entry = 0.0
                lowest_since_entry = float("inf")

            # === OPEN NEW POSITION ===
            if current_signal == Signal.LONG.value and position == 0:
                entry_price = self._apply_slippage(current_price, is_buy=True)
                position = capital / entry_price
                position_direction = "LONG"
                entry_date = dates[i]
                entry_regime = current_regime
                periods_held = 0
                highest_since_entry = current_high

                # Apply entry commission
                commission = capital * self.commission_pct
                capital -= commission

            elif current_signal == Signal.SHORT.value and position == 0:
                entry_price = self._apply_slippage(current_price, is_buy=False)
                position = capital / entry_price
                position_direction = "SHORT"
                entry_date = dates[i]
                entry_regime = current_regime
                periods_held = 0
                lowest_since_entry = current_low

                # Apply entry commission
                commission = capital * self.commission_pct
                capital -= commission

        # Close any remaining position at end
        if position != 0:
            final_price = prices[-1]
            exit_price = self._apply_slippage(
                final_price, position_direction == "SHORT"
            )

            if position_direction == "LONG":
                pnl = position * (exit_price - entry_price) * self.leverage
            else:
                pnl = position * (entry_price - exit_price) * self.leverage

            commission = abs(position * exit_price * self.commission_pct)
            pnl -= commission

            trade = Trade(
                entry_date=entry_date,
                exit_date=dates[-1],
                entry_price=entry_price,
                exit_price=exit_price,
                direction=position_direction,
                size=position,
                pnl=pnl,
                pnl_pct=pnl / (capital - pnl) * 100 if capital != pnl else 0,
                regime_at_entry=entry_regime,
            )
            trades.append(trade)
            capital += pnl

        # Calculate metrics
        equity_series = pd.Series(equity, index=dates[:len(equity)])

        return self._calculate_metrics(
            trades, equity_series, prices, self.initial_capital
        )

    def _apply_slippage(self, price: float, is_buy: bool) -> float:
        """Apply slippage to price."""
        if is_buy:
            return price * (1 + self.slippage_pct)
        else:
            return price * (1 - self.slippage_pct)

    def _calculate_metrics(
        self,
        trades: List[Trade],
        equity: pd.Series,
        prices: np.ndarray,
        initial_capital: float,
    ) -> BacktestResult:
        """Calculate all backtest metrics."""

        # Total return
        final_equity = equity.iloc[-1]
        total_return = (final_equity - initial_capital) / initial_capital * 100

        # Buy and hold return
        buy_hold_return = (prices[-1] - prices[0]) / prices[0] * 100

        # Alpha
        alpha = total_return - buy_hold_return

        # Drawdown calculation
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()

        # Trade statistics
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl <= 0]

        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0

        avg_win = (
            np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        )
        avg_loss = (
            abs(np.mean([t.pnl for t in losing_trades])) if losing_trades else 0
        )

        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Sharpe ratio (annualized, assuming daily data)
        returns = equity.pct_change().dropna()
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std()
        else:
            sharpe_ratio = 0.0

        return BacktestResult(
            total_return=total_return,
            buy_hold_return=buy_hold_return,
            alpha=alpha,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor if profit_factor != float("inf") else 999.99,
            trades=trades,
            equity_curve=equity,
            drawdown_curve=drawdown,
        )

    @staticmethod
    def trades_to_dataframe(trades: List[Trade]) -> pd.DataFrame:
        """Convert list of trades to DataFrame."""
        if not trades:
            return pd.DataFrame()

        data = []
        for t in trades:
            data.append(
                {
                    "Entry Date": t.entry_date,
                    "Exit Date": t.exit_date,
                    "Direction": t.direction,
                    "Entry Price": t.entry_price,
                    "Exit Price": t.exit_price,
                    "P&L": t.pnl,
                    "P&L %": t.pnl_pct,
                    "Regime": t.regime_at_entry,
                }
            )
        return pd.DataFrame(data)
