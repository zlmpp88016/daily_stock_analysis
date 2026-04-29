from __future__ import annotations

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategy_backtest.rules import (  # noqa: E402
    ComparisonNode,
    CrossoverNode,
    LogicalNode,
    ValueNode,
    evaluate_rule,
    evaluate_rules,
    parse_rule,
)


def _build_rule_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ma_5": [1.0, 2.0, 3.0, 1.0, 0.5],
            "ma_20": [2.0, 2.0, 2.0, 2.0, 1.0],
            "macd_dif": [-1.0, -0.5, 0.2, 0.3, -0.2],
            "macd_dea": [-0.8, -0.4, 0.1, 0.4, 0.0],
            "close": [9.5, 10.0, 11.0, 8.0, 7.5],
            "boll_lower": [9.0, 9.5, 10.5, 8.5, 7.8],
        }
    )


class StrategyRuleTestCase(unittest.TestCase):
    def assert_bool_series(self, actual: pd.Series, expected: list[bool]) -> None:
        pd.testing.assert_series_equal(actual, pd.Series(expected, index=actual.index, dtype=bool))

    def test_parse_rule_returns_crossover_ast(self) -> None:
        node = parse_rule("cross_over(ma_5, ma_20)")

        self.assertEqual(
            node,
            CrossoverNode(
                operator="cross_over",
                left=ValueNode(kind="column", value="ma_5"),
                right=ValueNode(kind="column", value="ma_20"),
            ),
        )

    def test_parse_rule_returns_comparison_ast(self) -> None:
        node = parse_rule("10.5 < close")

        self.assertEqual(
            node,
            ComparisonNode(
                operator="lt",
                left=ValueNode(kind="constant", value=10.5),
                right=ValueNode(kind="column", value="close"),
            ),
        )

    def test_parse_rule_respects_parentheses_over_default_precedence(self) -> None:
        node = parse_rule("(ma_5 > ma_20 or close < boll_lower) and macd_dif > macd_dea")

        self.assertEqual(
            node,
            LogicalNode(
                operator="and",
                left=LogicalNode(
                    operator="or",
                    left=ComparisonNode(
                        operator="gt",
                        left=ValueNode(kind="column", value="ma_5"),
                        right=ValueNode(kind="column", value="ma_20"),
                    ),
                    right=ComparisonNode(
                        operator="lt",
                        left=ValueNode(kind="column", value="close"),
                        right=ValueNode(kind="column", value="boll_lower"),
                    ),
                ),
                right=ComparisonNode(
                    operator="gt",
                    left=ValueNode(kind="column", value="macd_dif"),
                    right=ValueNode(kind="column", value="macd_dea"),
                ),
            ),
        )

    def test_evaluate_rule_detects_cross_over_on_expected_day(self) -> None:
        result = evaluate_rule(_build_rule_df(), "cross_over(ma_5, ma_20)")

        self.assert_bool_series(result, [False, False, True, False, False])

    def test_evaluate_rule_detects_cross_under_on_expected_day(self) -> None:
        result = evaluate_rule(_build_rule_df(), "cross_under(ma_5, ma_20)")

        self.assert_bool_series(result, [False, False, False, True, False])

    def test_evaluate_rule_supports_column_and_constant_comparisons_in_both_orders(self) -> None:
        df = _build_rule_df()

        indicator_result = evaluate_rule(df, "macd_dif > macd_dea")
        constant_right_result = evaluate_rule(df, "close > 10.5")
        constant_left_result = evaluate_rule(df, "10.5 < close")

        self.assert_bool_series(indicator_result, [False, False, True, False, False])
        self.assert_bool_series(constant_right_result, [False, False, True, False, False])
        self.assert_bool_series(constant_left_result, [False, False, True, False, False])

    def test_evaluate_rule_supports_constant_crossovers(self) -> None:
        df = pd.DataFrame({"close": [9.0, 10.0, 10.5, 9.5]})

        result = evaluate_rule(df, "cross_over(close, 10)")

        self.assert_bool_series(result, [False, False, True, False])

    def test_evaluate_rule_supports_nested_mixed_conditions(self) -> None:
        expression = "(cross_over(ma_5, ma_20) and macd_dif > macd_dea) or (close < boll_lower and ma_5 < 2)"

        result = evaluate_rule(_build_rule_df(), expression)

        self.assert_bool_series(result, [False, False, True, True, True])

    def test_evaluate_rule_treats_nan_results_as_false(self) -> None:
        df = pd.DataFrame(
            {
                "fast": [1.0, float("nan"), 3.0],
                "slow": [2.0, 2.0, 2.0],
                "close": [10.0, float("nan"), 8.0],
                "boll_lower": [9.0, 9.0, 9.0],
            }
        )

        comparison_result = evaluate_rule(df, "close < boll_lower")
        crossover_result = evaluate_rule(df, "cross_over(fast, slow)")

        self.assert_bool_series(comparison_result, [False, False, True])
        self.assert_bool_series(crossover_result, [False, False, False])

    def test_evaluate_rule_accepts_parsed_ast_without_mutating_input(self) -> None:
        df = _build_rule_df()
        original = df.copy(deep=True)
        node = parse_rule("cross_over(ma_5, ma_20) and macd_dif > macd_dea")

        result = evaluate_rule(df, node)

        self.assert_bool_series(result, [False, False, True, False, False])
        pd.testing.assert_frame_equal(df, original)

    def test_evaluate_rules_and_combines_multiple_rules(self) -> None:
        result = evaluate_rules(_build_rule_df(), ["cross_over(ma_5, ma_20)", "macd_dif > macd_dea"])

        self.assert_bool_series(result, [False, False, True, False, False])

    def test_evaluate_rules_returns_false_series_for_empty_rules(self) -> None:
        result = evaluate_rules(_build_rule_df(), [])

        self.assert_bool_series(result, [False, False, False, False, False])

    def test_cross_over_returns_false_on_first_row(self) -> None:
        result = evaluate_rule(pd.DataFrame({"ma_5": [3.0], "ma_20": [2.0]}), "cross_over(ma_5, ma_20)")

        self.assert_bool_series(result, [False])

    def test_parse_rule_validates_invalid_expressions(self) -> None:
        cases = (
            ("", "non-empty string"),
            ("foo(ma_5, ma_20)", "Unsupported function"),
            ("cross_over(ma_5 ma_20)", "Expected comma"),
        )

        for expression, error_message in cases:
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(ValueError, error_message):
                    parse_rule(expression)

    def test_evaluate_rule_raises_for_missing_columns(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            evaluate_rule(_build_rule_df(), "missing_indicator > ma_20")


if __name__ == "__main__":
    unittest.main()
