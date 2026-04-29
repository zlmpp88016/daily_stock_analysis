# -*- coding: utf-8 -*-
"""Strategy backtest endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from api.deps import get_database_manager
from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.strategy_backtest import (
    StrategyBacktestRunDetailResponse,
    StrategyBacktestRunRequest,
    StrategyBacktestRunResponse,
)
from src.services.strategy_backtest_service import StrategyBacktestService
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/run",
    response_model=StrategyBacktestRunResponse,
    responses={
        200: {"description": "策略回测执行完成"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="运行策略回测",
    description="获取历史日线数据，执行策略回测，并持久化运行结果、交易记录与资金曲线。",
)
def run_strategy_backtest(
    request: StrategyBacktestRunRequest,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> StrategyBacktestRunResponse:
    try:
        service = StrategyBacktestService(db_manager)
        run = service.run_backtest(**request.model_dump())
        return StrategyBacktestRunResponse(**run)
    except ValueError as exc:
        logger.warning("Strategy backtest request rejected: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_request", "message": str(exc)},
        )
    except Exception as exc:
        logger.error("Strategy backtest execution failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"Strategy backtest execution failed: {exc}"},
        )


@router.get(
    "/history",
    response_model=list[StrategyBacktestRunResponse],
    responses={
        200: {"description": "策略回测历史列表"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取策略回测历史",
    description="按股票代码筛选最近的策略回测运行记录。",
)
def get_strategy_backtest_history(
    code: Optional[str] = Query(None, description="股票代码筛选"),
    limit: int = Query(20, ge=1, le=200, description="返回记录上限"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> list[StrategyBacktestRunResponse]:
    try:
        service = StrategyBacktestService(db_manager)
        runs = service.get_history(code=code, limit=limit)
        return [StrategyBacktestRunResponse(**run) for run in runs]
    except Exception as exc:
        logger.error("Failed to query strategy backtest history: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"Failed to query strategy backtest history: {exc}"},
        )


@router.get(
    "/{run_id}",
    response_model=StrategyBacktestRunDetailResponse,
    responses={
        200: {"description": "策略回测详情"},
        404: {"description": "未找到对应运行记录", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取策略回测详情",
    description="返回策略回测运行详情，包括交易记录和资金曲线。",
)
def get_strategy_backtest_detail(
    run_id: int = Path(..., ge=1, description="策略回测运行 ID"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> StrategyBacktestRunDetailResponse:
    try:
        service = StrategyBacktestService(db_manager)
        detail = service.get_run_detail(run_id)
        if detail is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"Strategy backtest run {run_id} not found."},
            )
        return StrategyBacktestRunDetailResponse(**detail)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to query strategy backtest detail: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"Failed to query strategy backtest detail: {exc}"},
        )
