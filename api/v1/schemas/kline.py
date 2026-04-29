# -*- coding: utf-8 -*-
"""K-line API schemas."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class KlineBar(BaseModel):
    """One OHLCV bar for stock K-line data."""

    date: str = Field(..., description="Trading date in YYYY-MM-DD format.")
    open: float = Field(..., description="Open price.")
    high: float = Field(..., description="High price.")
    low: float = Field(..., description="Low price.")
    close: float = Field(..., description="Close price.")
    volume: float = Field(..., description="Trading volume.")
    amount: Optional[float] = Field(None, description="Trading amount.")
    pct_chg: Optional[float] = Field(None, description="Percentage change.")


class KlineIndicatorBar(BaseModel):
    """Indicator values aligned with one K-line bar."""

    macd_dif: Optional[float] = Field(None, description="MACD DIF value.")
    macd_dea: Optional[float] = Field(None, description="MACD DEA value.")
    macd_hist: Optional[float] = Field(None, description="MACD histogram value.")
    kdj_k: Optional[float] = Field(None, description="KDJ K value.")
    kdj_d: Optional[float] = Field(None, description="KDJ D value.")
    kdj_j: Optional[float] = Field(None, description="KDJ J value.")
    boll_upper: Optional[float] = Field(None, description="Bollinger upper band.")
    boll_middle: Optional[float] = Field(None, description="Bollinger middle band.")
    boll_lower: Optional[float] = Field(None, description="Bollinger lower band.")


class KlineDataResponse(BaseModel):
    """K-line response payload."""

    code: str = Field(..., description="Stock code.")
    name: str = Field("", description="Stock name.")
    period: Literal["daily", "weekly", "monthly"] = Field(..., description="K-line period.")
    bars: List[KlineBar] = Field(default_factory=list, description="K-line bar list.")
    indicators: List[KlineIndicatorBar] = Field(default_factory=list, description="Indicator bar list.")


class ChipDistributionResponse(BaseModel):
    """Chip distribution response payload."""

    code: str = Field(..., description="Stock code.")
    profit_ratio: float = Field(..., description="Profit ratio.")
    avg_cost: float = Field(..., description="Average holding cost.")
    cost_90_low: float = Field(..., description="Lower bound of 90 percent chip cost.")
    cost_90_high: float = Field(..., description="Upper bound of 90 percent chip cost.")
    concentration_90: float = Field(..., description="90 percent chip concentration.")
    cost_70_low: float = Field(..., description="Lower bound of 70 percent chip cost.")
    cost_70_high: float = Field(..., description="Upper bound of 70 percent chip cost.")
    concentration_70: float = Field(..., description="70 percent chip concentration.")
