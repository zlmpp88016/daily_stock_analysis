from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd


DEFAULT_MA_PERIODS = (5, 20, 30)
DEFAULT_MACD_FAST = 12
DEFAULT_MACD_SLOW = 26
DEFAULT_MACD_SIGNAL = 9
DEFAULT_KDJ_N = 9
DEFAULT_KDJ_K = 3
DEFAULT_KDJ_D = 3
DEFAULT_BOLL_PERIOD = 20
DEFAULT_BOLL_STDDEV = 2.0


def _require_columns(df: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def _normalize_positive_int(value: Any, name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc

    if normalized <= 0:
        raise ValueError(f"{name} must be a positive integer")

    return normalized


def _normalize_periods(periods: Sequence[int] | None) -> list[int]:
    if periods is None:
        periods = DEFAULT_MA_PERIODS

    normalized_periods: list[int] = []
    for raw_period in periods:
        period = _normalize_positive_int(raw_period, "period")
        if period not in normalized_periods:
            normalized_periods.append(period)

    return normalized_periods


def _normalize_indicator_config(config: Any, indicator_name: str) -> dict[str, Any]:
    if config is True:
        return {}
    if isinstance(config, Mapping):
        return dict(config)
    raise ValueError(f"{indicator_name} config must be a mapping or boolean")


def calc_ma(df: pd.DataFrame, periods: Sequence[int] | None = None) -> pd.DataFrame:
    """Append moving average columns without mutating the input frame."""
    _require_columns(df, ("close",))
    result = df.copy()

    for period in _normalize_periods(periods):
        result[f"ma_{period}"] = result["close"].rolling(window=period).mean()

    return result


def calc_macd(
    df: pd.DataFrame,
    fast: int = DEFAULT_MACD_FAST,
    slow: int = DEFAULT_MACD_SLOW,
    signal: int = DEFAULT_MACD_SIGNAL,
) -> pd.DataFrame:
    """Append MACD columns using the existing stock_analyzer formula."""
    _require_columns(df, ("close",))

    fast = _normalize_positive_int(fast, "fast")
    slow = _normalize_positive_int(slow, "slow")
    signal = _normalize_positive_int(signal, "signal")

    result = df.copy()
    ema_fast = result["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = result["close"].ewm(span=slow, adjust=False).mean()

    result["macd_dif"] = ema_fast - ema_slow
    result["macd_dea"] = result["macd_dif"].ewm(span=signal, adjust=False).mean()
    result["macd_hist"] = (result["macd_dif"] - result["macd_dea"]) * 2

    return result


def calc_kdj(
    df: pd.DataFrame,
    n: int = DEFAULT_KDJ_N,
    k_period: int = DEFAULT_KDJ_K,
    d_period: int = DEFAULT_KDJ_D,
) -> pd.DataFrame:
    """Append KDJ columns using rolling-window stochastic values."""
    _require_columns(df, ("high", "low", "close"))

    n = _normalize_positive_int(n, "n")
    k_period = _normalize_positive_int(k_period, "k_period")
    d_period = _normalize_positive_int(d_period, "d_period")

    result = df.copy()
    low_n = result["low"].rolling(window=n).min()
    high_n = result["high"].rolling(window=n).max()
    price_range = (high_n - low_n).where(lambda series: series != 0)

    rsv = ((result["close"] - low_n) / price_range) * 100
    result["kdj_k"] = rsv.rolling(window=k_period).mean()
    result["kdj_d"] = result["kdj_k"].rolling(window=d_period).mean()
    result["kdj_j"] = 3 * result["kdj_k"] - 2 * result["kdj_d"]

    return result


def calc_boll(
    df: pd.DataFrame,
    period: int = DEFAULT_BOLL_PERIOD,
    stddev: float = DEFAULT_BOLL_STDDEV,
) -> pd.DataFrame:
    """Append Bollinger Band columns."""
    _require_columns(df, ("close",))

    period = _normalize_positive_int(period, "period")

    try:
        stddev = float(stddev)
    except (TypeError, ValueError) as exc:
        raise ValueError("stddev must be a number") from exc

    if stddev <= 0:
        raise ValueError("stddev must be greater than 0")

    result = df.copy()
    result["boll_middle"] = result["close"].rolling(window=period).mean()
    rolling_std = result["close"].rolling(window=period).std()
    result["boll_upper"] = result["boll_middle"] + stddev * rolling_std
    result["boll_lower"] = result["boll_middle"] - stddev * rolling_std

    return result


def calc_indicators(df: pd.DataFrame, config: Mapping[str, Any] | None = None) -> pd.DataFrame:
    """Apply enabled indicators and return a new enriched DataFrame."""
    result = df.copy()
    if not config:
        return result

    if "ma" in config and config["ma"] is not False:
        ma_config = _normalize_indicator_config(config["ma"], "ma")
        result = calc_ma(result, periods=ma_config.get("periods"))

    if "macd" in config and config["macd"] is not False:
        macd_config = _normalize_indicator_config(config["macd"], "macd")
        result = calc_macd(
            result,
            fast=macd_config.get("fast", DEFAULT_MACD_FAST),
            slow=macd_config.get("slow", DEFAULT_MACD_SLOW),
            signal=macd_config.get("signal", DEFAULT_MACD_SIGNAL),
        )

    if "kdj" in config and config["kdj"] is not False:
        kdj_config = _normalize_indicator_config(config["kdj"], "kdj")
        result = calc_kdj(
            result,
            n=kdj_config.get("n", DEFAULT_KDJ_N),
            k_period=kdj_config.get("k_period", kdj_config.get("k", DEFAULT_KDJ_K)),
            d_period=kdj_config.get("d_period", kdj_config.get("d", DEFAULT_KDJ_D)),
        )

    if "boll" in config and config["boll"] is not False:
        boll_config = _normalize_indicator_config(config["boll"], "boll")
        result = calc_boll(
            result,
            period=boll_config.get("period", DEFAULT_BOLL_PERIOD),
            stddev=boll_config.get("stddev", DEFAULT_BOLL_STDDEV),
        )

    return result


__all__ = [
    "calc_boll",
    "calc_indicators",
    "calc_kdj",
    "calc_ma",
    "calc_macd",
]
