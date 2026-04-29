from __future__ import annotations

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategy_backtest.engine import (  # noqa: E402
    BacktestConfig,
    StrategyBacktestEngine,
)


def _build_bar_frame(
    *,
    dates: str,
    open_prices: list[float],
    close_prices: list[float],
    signal_buy: list[int],
    signal_sell: list[int],
) -> pd.DataFrame:
    high_prices = [max(open_price, close_price) for open_price, close_price in zip(open_prices, close_prices)]
    low_prices = [min(open_price, close_price) for open_price, close_price in zip(open_prices, close_prices)]

    return pd.DataFrame(
        {
            "date": pd.date_range(dates, periods=len(open_prices), freq="D"),
            "open": open_prices,
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "signal_buy": signal_buy,
            "signal_sell": signal_sell,
        }
    )


def _build_ma_crossover_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=9, freq="D"),
            "open": [10.0, 9.0, 8.0, 9.0, 10.0, 11.0, 10.0, 9.0, 8.0],
            "high": [10.2, 9.2, 8.2, 9.2, 10.2, 11.2, 10.2, 9.2, 8.2],
            "low": [9.8, 8.8, 7.8, 8.8, 9.8, 10.8, 9.8, 8.8, 7.8],
            "close": [10.0, 9.0, 8.0, 9.0, 10.0, 11.0, 10.0, 9.0, 8.0],
        }
    )


def _build_mixed_trade_df() -> pd.DataFrame:
    return _build_bar_frame(
        dates="2024-02-01",
        open_prices=[10.0, 10.0, 12.0, 12.0, 11.0, 9.0],
        close_prices=[10.0, 12.0, 12.0, 11.0, 9.0, 9.0],
        signal_buy=[1, 0, 0, 1, 0, 0],
        signal_sell=[0, 0, 1, 0, 1, 0],
    )


def _build_all_winning_df() -> pd.DataFrame:
    return _build_bar_frame(
        dates="2024-06-01",
        open_prices=[10.0, 10.0, 12.0, 10.0, 11.0, 13.0],
        close_prices=[10.0, 12.0, 12.0, 10.0, 13.0, 13.0],
        signal_buy=[1, 0, 0, 1, 0, 0],
        signal_sell=[0, 1, 0, 0, 1, 0],
    )


def _build_all_losing_df() -> pd.DataFrame:
    return _build_bar_frame(
        dates="2024-07-01",
        open_prices=[10.0, 10.0, 8.0, 10.0, 9.0, 7.0],
        close_prices=[10.0, 8.0, 8.0, 10.0, 7.0, 7.0],
        signal_buy=[1, 0, 0, 1, 0, 0],
        signal_sell=[0, 1, 0, 0, 1, 0],
    )


class StrategyBacktestEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = StrategyBacktestEngine()

    def test_run_executes_t_plus_one_with_indicator_rules_without_mutating_input(self) -> None:
        df = _build_ma_crossover_df()
        original = df.copy(deep=True)
        config = BacktestConfig(
            initial_cash=10000,
            indicators={"ma": {"periods": [2, 3]}},
            buy_rules=["cross_over(ma_2, ma_3)"],
            sell_rules=["cross_under(ma_2, ma_3)"],
        )

        result = self.engine.run(df, config)

        self.assertEqual(len(result.trades), 2)
        self.assertEqual(result.trades[0].trade_type, "buy")
        self.assertEqual(result.trades[0].date, pd.Timestamp("2024-01-06").date())
        self.assertAlmostEqual(result.trades[0].price, 11.0)
        self.assertEqual(result.trades[0].shares, 900)
        self.assertEqual(result.trades[1].trade_type, "sell")
        self.assertEqual(result.trades[1].date, pd.Timestamp("2024-01-09").date())
        self.assertAlmostEqual(result.trades[1].price, 8.0)
        self.assertEqual(result.summary.trade_count, 1)
        self.assertAlmostEqual(result.summary.avg_holding_days, 3.0)
        self.assertAlmostEqual(result.summary.total_return, -0.27)
        self.assertAlmostEqual(result.summary.max_drawdown, 0.27)
        pd.testing.assert_frame_equal(df, original)

    def test_run_applies_commission_slippage_and_share_rounding(self) -> None:
        df = _build_bar_frame(
            dates="2024-03-01",
            open_prices=[9.0, 10.0, 11.0],
            close_prices=[9.0, 10.0, 11.0],
            signal_buy=[1, 0, 0],
            signal_sell=[0, 0, 0],
        )
        config = BacktestConfig(
            initial_cash=10000,
            commission_rate=0.001,
            slippage_rate=0.01,
            buy_rules=["signal_buy > 0"],
            sell_rules=["signal_sell > 0"],
        )

        result = self.engine.run(df, config)

        buy_trade = result.trades[0]
        self.assertAlmostEqual(buy_trade.price, 10.1)
        self.assertEqual(buy_trade.shares, 900)
        self.assertAlmostEqual(buy_trade.commission, 9.09)
        self.assertAlmostEqual(result.equity_points[1].cash, 900.91)
        self.assertAlmostEqual(result.equity_points[1].position_value, 9000.0)
        self.assertEqual(result.summary.trade_count, 0)

    def test_run_enforces_single_position_with_repeated_buy_signals(self) -> None:
        df = _build_bar_frame(
            dates="2024-04-01",
            open_prices=[10.0, 10.0, 10.0, 10.0, 10.0],
            close_prices=[10.0, 10.0, 10.0, 10.0, 10.0],
            signal_buy=[1, 1, 1, 1, 1],
            signal_sell=[0, 0, 0, 0, 0],
        )
        config = BacktestConfig(
            initial_cash=10000,
            buy_rules=["signal_buy > 0"],
            sell_rules=["signal_sell > 0"],
        )

        result = self.engine.run(df, config)

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].trade_type, "buy")
        self.assertEqual(result.trades[0].shares, 1000)
        self.assertEqual(result.summary.trade_count, 0)

    def test_run_ignores_sell_signals_without_open_position(self) -> None:
        df = _build_bar_frame(
            dates="2024-05-01",
            open_prices=[10.0, 10.0, 11.0, 12.0, 12.0],
            close_prices=[10.0, 10.0, 11.0, 12.0, 12.0],
            signal_buy=[0, 1, 0, 0, 0],
            signal_sell=[1, 0, 1, 0, 0],
        )
        config = BacktestConfig(
            initial_cash=10000,
            buy_rules=["signal_buy > 0"],
            sell_rules=["signal_sell > 0"],
        )

        result = self.engine.run(df, config)

        self.assertEqual([trade.trade_type for trade in result.trades], ["buy", "sell"])
        self.assertEqual(result.trades[0].date, pd.Timestamp("2024-05-03").date())
        self.assertEqual(result.trades[1].date, pd.Timestamp("2024-05-04").date())
        self.assertAlmostEqual(result.summary.total_return, 0.09)

    def test_run_leaves_equity_unchanged_when_cash_too_small_for_one_lot(self) -> None:
        df = _build_bar_frame(
            dates="2024-08-01",
            open_prices=[10.0, 10.0, 10.0],
            close_prices=[10.0, 10.0, 10.0],
            signal_buy=[1, 0, 0],
            signal_sell=[0, 0, 0],
        )
        config = BacktestConfig(
            initial_cash=999,
            buy_rules=["signal_buy > 0"],
            sell_rules=["signal_sell > 0"],
        )

        result = self.engine.run(df, config)

        self.assertEqual(result.trades, [])
        self.assertTrue(all(point.equity == 999 for point in result.equity_points))
        self.assertAlmostEqual(result.summary.total_return, 0.0)

    def test_run_supports_zero_commission_and_zero_slippage_exact_prices(self) -> None:
        df = _build_bar_frame(
            dates="2024-09-01",
            open_prices=[9.0, 10.0, 12.0, 12.0],
            close_prices=[9.0, 10.0, 12.0, 12.0],
            signal_buy=[1, 0, 0, 0],
            signal_sell=[0, 1, 0, 0],
        )
        config = BacktestConfig(
            initial_cash=10000,
            commission_rate=0.0,
            slippage_rate=0.0,
            buy_rules=["signal_buy > 0"],
            sell_rules=["signal_sell > 0"],
        )

        result = self.engine.run(df, config)

        self.assertEqual(len(result.trades), 2)
        self.assertAlmostEqual(result.trades[0].price, 10.0)
        self.assertAlmostEqual(result.trades[0].commission, 0.0)
        self.assertAlmostEqual(result.trades[1].price, 12.0)
        self.assertAlmostEqual(result.trades[1].commission, 0.0)
        self.assertAlmostEqual(result.summary.total_return, 0.2)
        self.assertAlmostEqual(result.summary.win_rate, 1.0)

    def test_run_calculates_summary_metrics_from_mixed_trades(self) -> None:
        config = BacktestConfig(
            initial_cash=10000,
            buy_rules=["signal_buy > 0"],
            sell_rules=["signal_sell > 0"],
        )

        result = self.engine.run(_build_mixed_trade_df(), config)

        sell_trades = [trade for trade in result.trades if trade.trade_type == "sell"]
        self.assertEqual(len(sell_trades), 2)
        self.assertAlmostEqual(sell_trades[0].profit, 2000.0)
        self.assertAlmostEqual(sell_trades[1].profit, -2000.0)
        self.assertAlmostEqual(result.summary.total_return, 0.0)
        self.assertAlmostEqual(result.summary.max_drawdown, 1 / 6)
        self.assertAlmostEqual(result.summary.win_rate, 0.5)
        self.assertEqual(result.summary.trade_count, 2)
        self.assertAlmostEqual(result.summary.avg_holding_days, 1.5)

    def test_run_calculates_all_winning_trade_summary(self) -> None:
        config = BacktestConfig(
            initial_cash=10000,
            buy_rules=["signal_buy > 0"],
            sell_rules=["signal_sell > 0"],
        )

        result = self.engine.run(_build_all_winning_df(), config)

        sell_trades = [trade for trade in result.trades if trade.trade_type == "sell"]
        self.assertEqual(len(sell_trades), 2)
        self.assertTrue(all(trade.profit and trade.profit > 0 for trade in sell_trades))
        self.assertAlmostEqual(result.summary.total_return, 0.4)
        self.assertAlmostEqual(result.summary.max_drawdown, 0.0)
        self.assertAlmostEqual(result.summary.win_rate, 1.0)
        self.assertEqual(result.summary.trade_count, 2)
        self.assertAlmostEqual(result.summary.avg_holding_days, 1.0)

    def test_run_calculates_all_losing_trade_summary(self) -> None:
        config = BacktestConfig(
            initial_cash=10000,
            buy_rules=["signal_buy > 0"],
            sell_rules=["signal_sell > 0"],
        )

        result = self.engine.run(_build_all_losing_df(), config)

        sell_trades = [trade for trade in result.trades if trade.trade_type == "sell"]
        self.assertEqual(len(sell_trades), 2)
        self.assertTrue(all(trade.profit and trade.profit < 0 for trade in sell_trades))
        self.assertAlmostEqual(result.summary.total_return, -0.36)
        self.assertAlmostEqual(result.summary.max_drawdown, 0.36)
        self.assertAlmostEqual(result.summary.win_rate, 0.0)
        self.assertEqual(result.summary.trade_count, 2)
        self.assertAlmostEqual(result.summary.avg_holding_days, 1.0)

    def test_run_handles_no_signals_gracefully(self) -> None:
        df = _build_bar_frame(
            dates="2024-10-01",
            open_prices=[10.0, 10.0, 10.0, 10.0],
            close_prices=[10.0, 10.0, 10.0, 10.0],
            signal_buy=[0, 0, 0, 0],
            signal_sell=[0, 0, 0, 0],
        )
        config = BacktestConfig(
            initial_cash=10000,
            buy_rules=["signal_buy > 0"],
            sell_rules=["signal_sell > 0"],
        )

        result = self.engine.run(df, config)

        self.assertEqual(result.trades, [])
        self.assertEqual(len(result.equity_points), 4)
        self.assertAlmostEqual(result.summary.total_return, 0.0)
        self.assertAlmostEqual(result.summary.max_drawdown, 0.0)
        self.assertIsNone(result.summary.win_rate)
        self.assertEqual(result.summary.trade_count, 0)
        self.assertIsNone(result.summary.avg_holding_days)

    def test_run_validates_required_columns(self) -> None:
        df = pd.DataFrame({"date": pd.date_range("2024-11-01", periods=2, freq="D"), "close": [10.0, 10.0]})

        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            self.engine.run(df, BacktestConfig(initial_cash=10000))


if __name__ == "__main__":
    unittest.main()
