# -*- coding: utf-8 -*-
"""K-line endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from api.deps import get_database_manager
from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.kline import ChipDistributionResponse, KlineDataResponse
from data_provider.base import DataFetcherManager
from src.services.kline_service import KlineService
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()


def get_fetcher_manager() -> DataFetcherManager:
    """Return one data fetcher manager instance."""
    return DataFetcherManager()


@router.get(
    "/{code}",
    response_model=KlineDataResponse,
    responses={
        200: {"description": "K-line data returned successfully."},
        400: {"description": "Invalid request parameters.", "model": ErrorResponse},
        500: {"description": "Internal server error.", "model": ErrorResponse},
    },
    summary="Get stock K-line data",
    description="Query daily, weekly, or monthly K-line bars and MACD/KDJ/BOLL indicators from stock_daily.",
)
def get_kline_data(
    code: str = Path(..., min_length=1, description="Stock code."),
    period: str = Query("daily", description="K-line period: daily, weekly, or monthly."),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format."),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format."),
    limit: int = Query(500, ge=1, le=2000, description="Maximum number of bars to return."),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> KlineDataResponse:
    try:
        service = KlineService(db_manager)
        payload = service.get_kline_data(
            code=code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return KlineDataResponse(**payload)
    except ValueError as exc:
        logger.warning("K-line request rejected: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_request", "message": str(exc)},
        )
    except Exception as exc:
        logger.error("Failed to query K-line data: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"Failed to query K-line data: {exc}"},
        )


@router.get(
    "/{code}/chip-distribution",
    response_model=ChipDistributionResponse,
    responses={
        200: {"description": "Chip distribution returned successfully."},
        400: {"description": "Invalid request parameters.", "model": ErrorResponse},
        404: {"description": "Chip distribution data not found.", "model": ErrorResponse},
        500: {"description": "Internal server error.", "model": ErrorResponse},
    },
    summary="Get stock chip distribution",
    description="Query chip distribution data from the configured external data providers.",
)
def get_chip_distribution(
    code: str = Path(..., min_length=1, description="Stock code."),
    fetcher_manager: DataFetcherManager = Depends(get_fetcher_manager),
) -> ChipDistributionResponse:
    try:
        stock_code = code.strip()
        if not stock_code:
            raise ValueError("code is required.")

        chip = fetcher_manager.get_chip_distribution(stock_code)
        if chip is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"No chip distribution data available for {stock_code}."},
            )

        return ChipDistributionResponse(
            code=chip.code,
            profit_ratio=chip.profit_ratio,
            avg_cost=chip.avg_cost,
            cost_90_low=chip.cost_90_low,
            cost_90_high=chip.cost_90_high,
            concentration_90=chip.concentration_90,
            cost_70_low=chip.cost_70_low,
            cost_70_high=chip.cost_70_high,
            concentration_70=chip.concentration_70,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning("Chip distribution request rejected: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_request", "message": str(exc)},
        )
    except Exception as exc:
        logger.error("Failed to query chip distribution: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"Failed to query chip distribution: {exc}"},
        )
