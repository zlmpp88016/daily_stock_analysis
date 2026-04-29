# -*- coding: utf-8 -*-
"""Strategy backtest API schemas."""

from __future__ import annotations

from typing import List

from pydantic import Field

from src.strategy_backtest.models import (
    StrategyBacktestEquityResponse as StrategyBacktestEquityModel,
    StrategyBacktestRequest as StrategyBacktestRequestModel,
    StrategyBacktestRunResponse as StrategyBacktestRunModel,
    StrategyBacktestTradeResponse as StrategyBacktestTradeModel,
)


class StrategyBacktestRunRequest(StrategyBacktestRequestModel):
    """API payload for launching one strategy backtest run."""


class StrategyBacktestRunResponse(StrategyBacktestRunModel):
    """API response for a persisted strategy backtest run."""


class StrategyBacktestTradeResponse(StrategyBacktestTradeModel):
    """API response for one persisted strategy backtest trade."""


class StrategyBacktestEquityResponse(StrategyBacktestEquityModel):
    """API response for one persisted equity curve point."""


class StrategyBacktestRunDetailResponse(StrategyBacktestRunResponse):
    """Detailed API response with trades and equity curve."""

    trades: List[StrategyBacktestTradeResponse] = Field(default_factory=list, description="Executed trades.")
    equity_curve: List[StrategyBacktestEquityResponse] = Field(
        default_factory=list,
        description="Daily equity curve.",
    )
