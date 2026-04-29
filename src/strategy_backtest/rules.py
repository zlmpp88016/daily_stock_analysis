from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

import pandas as pd


ComparisonOperator = Literal["gt", "lt"]
CrossoverOperator = Literal["cross_over", "cross_under"]
LogicalOperator = Literal["and", "or"]
ValueKind = Literal["column", "constant"]


@dataclass(frozen=True)
class ValueNode:
    """Reference a DataFrame column or a numeric constant."""

    kind: ValueKind
    value: str | float


@dataclass(frozen=True)
class ComparisonNode:
    """Compare two operands with a greater-than or less-than operator."""

    operator: ComparisonOperator
    left: ValueNode
    right: ValueNode


@dataclass(frozen=True)
class CrossoverNode:
    """Detect a crossover event between two operands."""

    operator: CrossoverOperator
    left: ValueNode
    right: ValueNode


@dataclass(frozen=True)
class LogicalNode:
    """Combine two rule branches with boolean logic."""

    operator: LogicalOperator
    left: "RuleNode"
    right: "RuleNode"


RuleNode: TypeAlias = ComparisonNode | CrossoverNode | LogicalNode
RuleLike: TypeAlias = str | RuleNode


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str


_TOKEN_PATTERN = re.compile(
    r"""
    \s*
    (?:
        (?P<number>-?(?:\d+(?:\.\d*)?|\.\d+))
        | (?P<identifier>[A-Za-z_][A-Za-z0-9_]*)
        | (?P<operator>>|<)
        | (?P<comma>,)
        | (?P<lparen>\()
        | (?P<rparen>\))
    )
    """,
    re.VERBOSE,
)
_LOGICAL_KEYWORDS = {"and", "or"}
_CROSSOVER_FUNCTIONS = {"cross_over", "cross_under"}


class _RuleParser:
    def __init__(self, expression: str) -> None:
        self._expression = expression
        self._tokens = _tokenize(expression)
        self._position = 0

    def parse(self) -> RuleNode:
        node = self._parse_or_expression()
        self._expect("eof")
        return node

    def _parse_or_expression(self) -> RuleNode:
        node = self._parse_and_expression()
        while self._match("keyword", "or"):
            node = LogicalNode(operator="or", left=node, right=self._parse_and_expression())
        return node

    def _parse_and_expression(self) -> RuleNode:
        node = self._parse_condition()
        while self._match("keyword", "and"):
            node = LogicalNode(operator="and", left=node, right=self._parse_condition())
        return node

    def _parse_condition(self) -> RuleNode:
        current = self._current()
        if current.kind == "lparen":
            self._advance()
            node = self._parse_or_expression()
            self._expect("rparen")
            return node

        if current.kind == "identifier" and self._peek().kind == "lparen":
            if current.value not in _CROSSOVER_FUNCTIONS:
                raise ValueError(f"Unsupported function: {current.value}")
            return self._parse_crossover()

        return self._parse_comparison()

    def _parse_crossover(self) -> CrossoverNode:
        operator = self._expect("identifier").value
        self._expect("lparen")
        left = self._parse_value()
        self._expect("comma")
        right = self._parse_value()
        self._expect("rparen")
        return CrossoverNode(operator=operator, left=left, right=right)

    def _parse_comparison(self) -> ComparisonNode:
        left = self._parse_value()
        operator_token = self._expect("operator")
        right = self._parse_value()
        operator: ComparisonOperator = "gt" if operator_token.value == ">" else "lt"
        return ComparisonNode(operator=operator, left=left, right=right)

    def _parse_value(self) -> ValueNode:
        current = self._current()
        if current.kind == "identifier":
            self._advance()
            return ValueNode(kind="column", value=current.value)
        if current.kind == "number":
            self._advance()
            return ValueNode(kind="constant", value=float(current.value))
        raise ValueError(f"Expected column name or numeric constant, got '{current.value}'")

    def _current(self) -> _Token:
        return self._tokens[self._position]

    def _peek(self) -> _Token:
        return self._tokens[self._position + 1]

    def _advance(self) -> _Token:
        token = self._current()
        self._position += 1
        return token

    def _match(self, kind: str, value: str | None = None) -> bool:
        current = self._current()
        if current.kind != kind:
            return False
        if value is not None and current.value != value:
            return False
        self._advance()
        return True

    def _expect(self, kind: str, value: str | None = None) -> _Token:
        current = self._current()
        if current.kind != kind or (value is not None and current.value != value):
            expected = f"{kind} '{value}'" if value is not None else kind
            raise ValueError(f"Expected {expected}, got '{current.value}'")
        return self._advance()


def _tokenize(expression: str) -> list[_Token]:
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Rule expression must be a non-empty string")

    tokens: list[_Token] = []
    position = 0

    while position < len(expression):
        match = _TOKEN_PATTERN.match(expression, position)
        if match is None:
            fragment = expression[position:].strip() or expression[position:]
            raise ValueError(f"Invalid token near '{fragment}'")

        position = match.end()
        kind = match.lastgroup
        if kind is None:
            continue

        value = match.group(kind)
        if kind == "identifier" and value in _LOGICAL_KEYWORDS:
            kind = "keyword"

        tokens.append(_Token(kind=kind, value=value))

    tokens.append(_Token(kind="eof", value=""))
    return tokens


def _resolve_operand(df: pd.DataFrame, operand: ValueNode) -> pd.Series:
    if operand.kind == "constant":
        return pd.Series(operand.value, index=df.index, dtype="float64")

    column_name = str(operand.value)
    if column_name not in df.columns:
        raise ValueError(f"Missing required columns: {column_name}")
    return df[column_name]


def _normalize_boolean_series(series: pd.Series) -> pd.Series:
    return series.fillna(False).astype(bool)


def _evaluate_node(df: pd.DataFrame, node: RuleNode) -> pd.Series:
    if isinstance(node, ComparisonNode):
        left = _resolve_operand(df, node.left)
        right = _resolve_operand(df, node.right)
        result = left > right if node.operator == "gt" else left < right
        return _normalize_boolean_series(result)

    if isinstance(node, CrossoverNode):
        left = _resolve_operand(df, node.left)
        right = _resolve_operand(df, node.right)
        previous_left = left.shift(1)
        previous_right = right.shift(1)

        if node.operator == "cross_over":
            result = (previous_left <= previous_right) & (left > right)
        else:
            result = (previous_left >= previous_right) & (left < right)

        if not result.empty:
            result.iloc[0] = False
        return _normalize_boolean_series(result)

    left = _evaluate_node(df, node.left)
    right = _evaluate_node(df, node.right)
    result = left & right if node.operator == "and" else left | right
    return _normalize_boolean_series(result)


def parse_rule(expression: str) -> RuleNode:
    """Parse a rule expression into a structured AST."""

    return _RuleParser(expression).parse()


def evaluate_rule(df: pd.DataFrame, rule: RuleLike) -> pd.Series:
    """Evaluate one parsed rule or rule expression against a DataFrame."""

    parsed_rule = parse_rule(rule) if isinstance(rule, str) else rule
    return _evaluate_node(df, parsed_rule)


def evaluate_rules(df: pd.DataFrame, rules: list[RuleLike] | tuple[RuleLike, ...]) -> pd.Series:
    """Evaluate multiple rules and AND-combine them into one signal Series."""

    if not rules:
        return pd.Series(False, index=df.index, dtype=bool)

    result = pd.Series(True, index=df.index, dtype=bool)
    for rule in rules:
        result &= evaluate_rule(df, rule)
    return _normalize_boolean_series(result)


__all__ = [
    "ComparisonNode",
    "CrossoverNode",
    "LogicalNode",
    "ValueNode",
    "evaluate_rule",
    "evaluate_rules",
    "parse_rule",
]
