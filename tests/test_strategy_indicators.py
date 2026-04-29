from __future__ import annotations

import math
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategy_backtest.indicators import (  # noqa: E402
    calc_boll,
    calc_indicators,
    calc_kdj,
    calc_ma,
    calc_macd,
)


def _build_ohlcv_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": [10.0, 10.3, 10.5, 10.8, 11.0, 11.2, 11.5, 11.7],
            "high": [10.4, 10.7, 10.9, 11.2, 11.4, 11.7, 12.0, 12.2],
            "low": [9.8, 10.0, 10.2, 10.5, 10.8, 11.0, 11.2, 11.4],
            "close": [10.2, 10.5, 10.7, 11.0, 11.3, 11.5, 11.8, 12.0],
            "volume": [1000, 1200, 1100, 1400, 1500, 1600, 1700, 1800],
        }
    )


class StrategyIndicatorTestCase(unittest.TestCase):
    def assert_series_close(self, series: pd.Series, expected: list[float | None], *, tolerance: float = 1e-6) -> None:
        self.assertEqual(len(series), len(expected))
        for idx, expected_value in enumerate(expected):
            actual_value = series.iloc[idx]
            if expected_value is None:
                self.assertTrue(pd.isna(actual_value), f"Expected NaN at index {idx}, got {actual_value!r}")
                continue

            delta = max(abs(expected_value) * 1e-4, tolerance)
            self.assertAlmostEqual(float(actual_value), expected_value, delta=delta, msg=f"Mismatch at index {idx}")

    def test_public_indicator_functions_do_not_mutate_input(self) -> None:
        cases = (
            (calc_ma, {"periods": [3, 5]}),
            (calc_macd, {"fast": 3, "slow": 6, "signal": 2}),
            (calc_kdj, {"n": 3, "k_period": 2, "d_period": 2}),
            (calc_boll, {"period": 3, "stddev": 2}),
        )

        for func, kwargs in cases:
            with self.subTest(func=func.__name__):
                df = _build_ohlcv_df()
                original = df.copy(deep=True)

                result = func(df, **kwargs)

                self.assertIsNot(result, df)
                pd.testing.assert_frame_equal(df, original)

    def test_calc_ma_matches_hand_calculated_reference(self) -> None:
        result = calc_ma(_build_ohlcv_df(), periods=[3, 5])

        self.assert_series_close(
            result["ma_3"],
            [None, None, 10.4666666667, 10.7333333333, 11.0, 11.2666666667, 11.5333333333, 11.7666666667],
        )
        self.assert_series_close(result["ma_5"], [None, None, None, None, 10.74, 11.0, 11.26, 11.52])

    def test_calc_macd_matches_hand_calculated_reference(self) -> None:
        result = calc_macd(_build_ohlcv_df(), fast=3, slow=6, signal=2)

        self.assert_series_close(
            result["macd_dif"],
            [0.0, 0.0642857143, 0.1209183673, 0.1881559767, 0.2495756976, 0.278714784, 0.3135909172, 0.3241051194],
        )
        self.assert_series_close(
            result["macd_dea"],
            [0.0, 0.0428571429, 0.0948979592, 0.1570699708, 0.2187404554, 0.2587233411, 0.2953017251, 0.314503988],
        )
        self.assert_series_close(
            result["macd_hist"],
            [0.0, 0.0428571429, 0.0520408163, 0.0621720117, 0.0616704845, 0.0399828858, 0.036578384, 0.0192022628],
        )

    def test_calc_kdj_matches_hand_calculated_reference(self) -> None:
        result = calc_kdj(_build_ohlcv_df(), n=3, k_period=2, d_period=2)

        self.assert_series_close(
            result["kdj_k"],
            [None, None, None, 82.5757575758, 87.5, 87.5, 83.3333333333, 83.3333333333],
        )
        self.assert_series_close(result["kdj_d"], [None, None, None, None, 85.0378787879, 87.5, 85.4166666667, 83.3333333333])
        self.assert_series_close(result["kdj_j"], [None, None, None, None, 92.4242424242, 87.5, 79.1666666667, 83.3333333333])

    def test_calc_boll_matches_hand_calculated_reference(self) -> None:
        result = calc_boll(_build_ohlcv_df(), period=3, stddev=2)

        self.assert_series_close(
            result["boll_middle"],
            [None, None, 10.4666666667, 10.7333333333, 11.0, 11.2666666667, 11.5333333333, 11.7666666667],
        )
        self.assert_series_close(
            result["boll_upper"],
            [None, None, 10.9699889624, 11.236655629, 11.6, 11.7699889624, 12.036655629, 12.2699889624],
        )
        self.assert_series_close(
            result["boll_lower"],
            [None, None, 9.963344371, 10.2300110376, 10.4, 10.763344371, 11.0300110376, 11.263344371],
        )

    def test_rolling_indicators_propagate_nan_close_values(self) -> None:
        df = _build_ohlcv_df()
        df.loc[3, "close"] = float("nan")

        ma_result = calc_ma(df, periods=[3])
        boll_result = calc_boll(df, period=3, stddev=2)
        kdj_result = calc_kdj(df, n=3, k_period=2, d_period=2)

        for idx in (3, 4, 5):
            self.assertTrue(math.isnan(ma_result.loc[idx, "ma_3"]))
            self.assertTrue(math.isnan(boll_result.loc[idx, "boll_middle"]))

        self.assertTrue(math.isnan(kdj_result.loc[3, "kdj_k"]))
        self.assertTrue(math.isnan(kdj_result.loc[4, "kdj_k"]))
        self.assertTrue(math.isnan(kdj_result.loc[4, "kdj_d"]))

    def test_indicator_functions_handle_empty_frames(self) -> None:
        empty_df = _build_ohlcv_df().iloc[0:0]
        cases = (
            (calc_ma, {"periods": [3]}, {"ma_3"}),
            (calc_macd, {"fast": 3, "slow": 6, "signal": 2}, {"macd_dif", "macd_dea", "macd_hist"}),
            (calc_kdj, {"n": 3, "k_period": 2, "d_period": 2}, {"kdj_k", "kdj_d", "kdj_j"}),
            (calc_boll, {"period": 3, "stddev": 2}, {"boll_upper", "boll_middle", "boll_lower"}),
        )

        for func, kwargs, expected_columns in cases:
            with self.subTest(func=func.__name__):
                result = func(empty_df, **kwargs)
                self.assertTrue(result.empty)
                self.assertTrue(expected_columns.issubset(result.columns))

    def test_calc_indicators_handles_single_row_input_with_boolean_config(self) -> None:
        df = _build_ohlcv_df().iloc[:1]

        result = calc_indicators(df, {"ma": True, "macd": True, "kdj": True, "boll": True})

        self.assertEqual(len(result), 1)
        self.assertTrue(math.isnan(result.loc[0, "ma_5"]))
        self.assertAlmostEqual(result.loc[0, "macd_dif"], 0.0)
        self.assertAlmostEqual(result.loc[0, "macd_dea"], 0.0)
        self.assertAlmostEqual(result.loc[0, "macd_hist"], 0.0)
        self.assertTrue(math.isnan(result.loc[0, "kdj_k"]))
        self.assertTrue(math.isnan(result.loc[0, "boll_middle"]))

    def test_calc_ma_returns_all_nan_for_periods_larger_than_frame(self) -> None:
        result = calc_ma(_build_ohlcv_df(), periods=[20, 20, 30])

        self.assertIn("ma_20", result.columns)
        self.assertIn("ma_30", result.columns)
        self.assertNotIn("ma_20.0", result.columns)
        self.assertTrue(result["ma_20"].isna().all())
        self.assertTrue(result["ma_30"].isna().all())

    def test_calc_indicators_dispatches_all_enabled_indicators(self) -> None:
        config = {
            "ma": {"periods": [3, 5]},
            "macd": {"fast": 3, "slow": 6, "signal": 2},
            "kdj": {"n": 3, "k": 2, "d": 2},
            "boll": {"period": 3, "stddev": 2},
        }

        result = calc_indicators(_build_ohlcv_df(), config)

        self.assertTrue(
            {
                "ma_3",
                "ma_5",
                "macd_dif",
                "macd_dea",
                "macd_hist",
                "kdj_k",
                "kdj_d",
                "kdj_j",
                "boll_upper",
                "boll_middle",
                "boll_lower",
            }.issubset(result.columns)
        )

    def test_calc_indicators_validates_invalid_config_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "mapping or boolean"):
            calc_indicators(_build_ohlcv_df(), {"ma": 123})

    def test_public_indicator_functions_validate_parameters(self) -> None:
        cases = (
            (calc_ma, {"periods": [0]}, "positive integer"),
            (calc_macd, {"fast": 0}, "positive integer"),
            (calc_kdj, {"n": 0}, "positive integer"),
            (calc_boll, {"stddev": 0}, "greater than 0"),
        )

        for func, kwargs, error_message in cases:
            with self.subTest(func=func.__name__):
                with self.assertRaisesRegex(ValueError, error_message):
                    func(_build_ohlcv_df(), **kwargs)

    def test_public_indicator_functions_validate_required_columns(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            calc_kdj(pd.DataFrame({"close": [1.0, 2.0, 3.0]}))


if __name__ == "__main__":
    unittest.main()
