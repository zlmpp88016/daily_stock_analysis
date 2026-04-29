# -*- coding: utf-8 -*-
"""Pydantic models for strategy backtest requests and responses."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MAIndicatorConfig(BaseModel):
    """Moving average indicator configuration."""

    periods: List[int] = Field(..., min_length=1, description="Moving average periods.")


class MACDIndicatorConfig(BaseModel):
    """MACD indicator configuration."""

    fast: int = Field(12, ge=1, description="Fast EMA period.")
    slow: int = Field(26, ge=1, description="Slow EMA period.")
    signal: int = Field(9, ge=1, description="Signal EMA period.")


class KDJIndicatorConfig(BaseModel):
    """KDJ indicator configuration."""

    n: int = Field(9, ge=1, description="RSV lookback window.")
    k: int = Field(3, ge=1, description="K smoothing factor.")
    d: int = Field(3, ge=1, description="D smoothing factor.")


class BollIndicatorConfig(BaseModel):
    """Bollinger Band indicator configuration."""

    period: int = Field(20, ge=1, description="Rolling window period.")
    stddev: float = Field(2.0, gt=0, description="Standard deviation multiplier.")


class IndicatorConfig(BaseModel):
    """Supported strategy indicator configuration."""

    model_config = ConfigDict(extra="forbid")

    ma: Optional[MAIndicatorConfig] = None
    macd: Optional[MACDIndicatorConfig] = None
    kdj: Optional[KDJIndicatorConfig] = None
    boll: Optional[BollIndicatorConfig] = None


class RuleConfig(BaseModel):
    """Rule lists for strategy entry and exit logic."""

    buy_rules: List[str] = Field(..., min_length=1, description="Buy rule expressions.")
    sell_rules: List[str] = Field(..., min_length=1, description="Sell rule expressions.")


class StrategyBacktestRequest(RuleConfig):
    """Strategy backtest request payload."""

    code: str = Field(..., min_length=1, max_length=40, description="Stock code.")
    start_date: date = Field(..., description="Backtest start date.")
    end_date: date = Field(..., description="Backtest end date.")
    initial_cash: float = Field(..., gt=0, description="Initial cash balance.")
    commission_rate: float = Field(0.0, ge=0, description="Commission rate.")
    slippage_rate: float = Field(0.0, ge=0, description="Slippage rate.")
    execution_mode: str = Field("next_open", min_length=1, max_length=64, description="Execution mode.")
    indicators: IndicatorConfig = Field(..., description="Indicator configuration.")

    @model_validator(mode="after")
    def validate_date_range(self) -> "StrategyBacktestRequest":
        """Validate that the requested date range is ordered."""

        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class StrategyBacktestSummary(BaseModel):
    """Summary metrics for a strategy backtest run."""

    model_config = ConfigDict(from_attributes=True)

    total_return: Optional[float] = Field(None, description="Total return ratio.")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown ratio.")
    win_rate: Optional[float] = Field(None, description="Win rate ratio.")
    trade_count: int = Field(0, ge=0, description="Number of completed trades.")
    avg_holding_days: Optional[float] = Field(None, description="Average holding days.")


class StrategyBacktestRunResponse(StrategyBacktestRequest):
    """Stored strategy backtest run."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str = Field(..., description="Run status.")
    total_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    trade_count: int = 0
    avg_holding_days: Optional[float] = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_storage_snapshot(cls, value: Any) -> Any:
        """Support ORM rows that store rule and indicator snapshots as JSON text."""

        if isinstance(value, dict):
            data = dict(value)
        else:
            data = {
                field_name: getattr(value, field_name)
                for field_name in (
                    "id",
                    "code",
                    "start_date",
                    "end_date",
                    "initial_cash",
                    "commission_rate",
                    "slippage_rate",
                    "execution_mode",
                    "status",
                    "total_return",
                    "max_drawdown",
                    "win_rate",
                    "trade_count",
                    "avg_holding_days",
                    "created_at",
                )
                if hasattr(value, field_name)
            }

            for source_name, target_name, fallback in (
                ("indicators_json", "indicators", {}),
                ("buy_rules_json", "buy_rules", []),
                ("sell_rules_json", "sell_rules", []),
            ):
                if hasattr(value, source_name):
                    data[target_name] = cls._decode_json_snapshot(getattr(value, source_name), fallback)

        if "indicators" not in data and "indicators_json" in data:
            data["indicators"] = cls._decode_json_snapshot(data.pop("indicators_json"), {})
        if "buy_rules" not in data and "buy_rules_json" in data:
            data["buy_rules"] = cls._decode_json_snapshot(data.pop("buy_rules_json"), [])
        if "sell_rules" not in data and "sell_rules_json" in data:
            data["sell_rules"] = cls._decode_json_snapshot(data.pop("sell_rules_json"), [])
        return data

    @staticmethod
    def _decode_json_snapshot(raw_value: Any, fallback: Any) -> Any:
        """Decode JSON snapshots stored as strings while preserving already parsed values."""

        if raw_value is None:
            return fallback
        if isinstance(raw_value, (dict, list)):
            return raw_value
        if isinstance(raw_value, str):
            return json.loads(raw_value)
        return raw_value


class StrategyBacktestTradeResponse(BaseModel):
    """Stored strategy backtest trade."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    trade_type: Literal["buy", "sell"]
    trade_date: date
    price: float = Field(..., gt=0)
    shares: int = Field(..., gt=0)
    commission: float = Field(..., ge=0)
    profit: Optional[float] = None
    profit_rate: Optional[float] = None


class StrategyBacktestEquityResponse(BaseModel):
    """Stored strategy backtest equity curve point."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    date: date
    equity: float = Field(..., ge=0)
    cash: float = Field(..., ge=0)
    position_value: float = Field(..., ge=0)
    drawdown: Optional[float] = None
