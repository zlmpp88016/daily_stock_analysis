# -*- coding: utf-8 -*-
"""Service layer for stock K-line data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy import select

from src.storage import DatabaseManager, StockDaily
from src.strategy_backtest.indicators import calc_boll, calc_kdj, calc_macd


_BAR_COLUMNS = ["date", "open", "high", "low", "close", "volume", "amount", "pct_chg"]
_INDICATOR_COLUMNS = [
    "macd_dif",
    "macd_dea",
    "macd_hist",
    "kdj_k",
    "kdj_d",
    "kdj_j",
    "boll_upper",
    "boll_middle",
    "boll_lower",
]
_VALID_PERIODS = {"daily", "weekly", "monthly"}


class KlineService:
    """Query, aggregate, and serialize stock K-line data."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    def _query_daily_data(
        self,
        code: str,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> pd.DataFrame:
        """Load daily bars from stock_daily as a DataFrame."""
        conditions = [StockDaily.code == code]
        if start_date is not None:
            conditions.append(StockDaily.date >= start_date)
        if end_date is not None:
            conditions.append(StockDaily.date <= end_date)

        stmt = select(StockDaily).where(*conditions).order_by(StockDaily.date)
        with self.db.get_session() as session:
            rows = session.execute(stmt).scalars().all()

        if not rows:
            return pd.DataFrame(columns=["name", *_BAR_COLUMNS])

        frame = pd.DataFrame(
            [
                {
                    "name": row.name or "",
                    "date": row.date,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": row.volume,
                    "amount": row.amount,
                    "pct_chg": row.pct_chg,
                }
                for row in rows
            ]
        )
        frame["date"] = pd.to_datetime(frame["date"])
        return frame

    def _aggregate_weekly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate daily bars into weekly bars."""
        return self._aggregate_period(df, "W")

    def _aggregate_monthly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate daily bars into month-end bars."""
        return self._aggregate_period(df, "ME")

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Append MACD, KDJ, and BOLL indicators."""
        if df.empty:
            result = df.copy(deep=True)
            for column in _INDICATOR_COLUMNS:
                result[column] = pd.Series(dtype="float64")
            return result

        result = calc_macd(df)
        result = calc_kdj(result)
        result = calc_boll(result)
        return result

    def get_kline_data(
        self,
        code: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """Return K-line bars and indicators as JSON-serializable data."""
        stock_code = (code or "").strip()
        if not stock_code:
            raise ValueError("code is required.")
        if limit < 1:
            raise ValueError("limit must be greater than 0.")

        normalized_period = (period or "").strip().lower()
        if normalized_period not in _VALID_PERIODS:
            raise ValueError("period must be one of: daily, weekly, monthly.")

        parsed_start = self._parse_date(start_date, field_name="start_date")
        parsed_end = self._parse_date(end_date, field_name="end_date")
        if parsed_start is not None and parsed_end is not None and parsed_start > parsed_end:
            raise ValueError("start_date cannot be later than end_date.")

        daily_df = self._query_daily_data(stock_code, parsed_start, parsed_end)
        stock_name = self._extract_name(daily_df)
        if daily_df.empty:
            return {
                "code": stock_code,
                "name": stock_name,
                "period": normalized_period,
                "bars": [],
                "indicators": [],
            }

        if normalized_period == "weekly":
            base_df = self._aggregate_weekly(daily_df)
        elif normalized_period == "monthly":
            base_df = self._aggregate_monthly(daily_df)
        else:
            base_df = daily_df[_BAR_COLUMNS].copy(deep=True)

        enriched_df = self._compute_indicators(base_df.sort_values("date").reset_index(drop=True))
        result_df = enriched_df.tail(limit).reset_index(drop=True)

        return {
            "code": stock_code,
            "name": stock_name,
            "period": normalized_period,
            "bars": [self._serialize_bar(row) for _, row in result_df.iterrows()],
            "indicators": [self._serialize_indicator(row) for _, row in result_df.iterrows()],
        }

    @staticmethod
    def _aggregate_period(df: pd.DataFrame, frequency: str) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=_BAR_COLUMNS)

        indexed = df[_BAR_COLUMNS].copy(deep=True)
        indexed["_real_date"] = pd.to_datetime(indexed["date"])
        indexed["date"] = pd.to_datetime(indexed["date"])
        indexed = indexed.set_index("date").sort_index()

        aggregated = indexed.resample(frequency).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
                "amount": "sum",
                "_real_date": "max",
            }
        )
        aggregated = aggregated.dropna(subset=["open", "high", "low", "close"])
        aggregated["pct_chg"] = aggregated["close"].pct_change() * 100
        aggregated["date"] = aggregated["_real_date"].dt.normalize()
        aggregated = aggregated.drop(columns=["_real_date"])
        return aggregated.reset_index(drop=True)

    @staticmethod
    def _parse_date(value: Optional[str], *, field_name: str) -> Optional[date]:
        if value in (None, ""):
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"{field_name} must be in YYYY-MM-DD format.") from exc

    @staticmethod
    def _extract_name(df: pd.DataFrame) -> str:
        if df.empty or "name" not in df.columns:
            return ""
        names = df["name"].fillna("").astype(str).str.strip()
        names = names[names != ""]
        if names.empty:
            return ""
        return names.iloc[-1]

    @staticmethod
    def _serialize_bar(row: pd.Series) -> Dict[str, Any]:
        return {
            "date": KlineService._serialize_date(row.get("date")),
            "open": KlineService._to_float(row.get("open")) or 0.0,
            "high": KlineService._to_float(row.get("high")) or 0.0,
            "low": KlineService._to_float(row.get("low")) or 0.0,
            "close": KlineService._to_float(row.get("close")) or 0.0,
            "volume": KlineService._to_float(row.get("volume")) or 0.0,
            "amount": KlineService._to_float(row.get("amount")),
            "pct_chg": KlineService._to_float(row.get("pct_chg")),
        }

    @staticmethod
    def _serialize_indicator(row: pd.Series) -> Dict[str, Optional[float]]:
        return {
            "macd_dif": KlineService._to_float(row.get("macd_dif")),
            "macd_dea": KlineService._to_float(row.get("macd_dea")),
            "macd_hist": KlineService._to_float(row.get("macd_hist")),
            "kdj_k": KlineService._to_float(row.get("kdj_k")),
            "kdj_d": KlineService._to_float(row.get("kdj_d")),
            "kdj_j": KlineService._to_float(row.get("kdj_j")),
            "boll_upper": KlineService._to_float(row.get("boll_upper")),
            "boll_middle": KlineService._to_float(row.get("boll_middle")),
            "boll_lower": KlineService._to_float(row.get("boll_lower")),
        }

    @staticmethod
    def _serialize_date(value: Any) -> str:
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")
        return str(value)

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None or pd.isna(value):
            return None
        return float(value)
