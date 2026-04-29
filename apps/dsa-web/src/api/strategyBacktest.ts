import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  IndicatorConfig,
  StrategyBacktestEquity,
  StrategyBacktestRequest,
  StrategyBacktestRunDetail,
  StrategyBacktestRunResponse,
  StrategyBacktestTrade,
} from '../types/strategyBacktest';

type StrategyBacktestRunDetailApiResponse = StrategyBacktestRunResponse & {
  equity?: StrategyBacktestEquity[];
  equityCurve?: StrategyBacktestEquity[];
  trades?: StrategyBacktestTrade[];
};

function buildIndicatorConfigPayload(indicators: IndicatorConfig): Record<string, unknown> {
  const payload: Record<string, unknown> = {};

  if (indicators.ma) {
    payload.ma = {
      periods: indicators.ma.periods,
    };
  }

  if (indicators.macd) {
    payload.macd = {
      fast: indicators.macd.fast,
      slow: indicators.macd.slow,
      signal: indicators.macd.signal,
    };
  }

  if (indicators.kdj) {
    payload.kdj = {
      n: indicators.kdj.n,
      k: indicators.kdj.k,
      d: indicators.kdj.d,
    };
  }

  if (indicators.boll) {
    payload.boll = {
      period: indicators.boll.period,
      stddev: indicators.boll.stddev,
    };
  }

  return payload;
}

function buildRunRequestPayload(request: StrategyBacktestRequest): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    code: request.code,
    start_date: request.startDate,
    end_date: request.endDate,
    initial_cash: request.initialCash,
    indicators: buildIndicatorConfigPayload(request.indicators),
    buy_rules: request.buyRules,
    sell_rules: request.sellRules,
  };

  if (request.commissionRate != null) {
    payload.commission_rate = request.commissionRate;
  }

  if (request.slippageRate != null) {
    payload.slippage_rate = request.slippageRate;
  }

  if (request.executionMode) {
    payload.execution_mode = request.executionMode;
  }

  return payload;
}

function normalizeRunDetail(data: StrategyBacktestRunDetailApiResponse): StrategyBacktestRunDetail {
  const { equity, equityCurve, trades, ...run } = data;

  return {
    ...run,
    trades: trades ?? [],
    equity: equity ?? equityCurve ?? [],
  };
}

export const strategyBacktestApi = {
  run: async (request: StrategyBacktestRequest): Promise<StrategyBacktestRunResponse> => {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/strategy-backtest/run',
      buildRunRequestPayload(request),
    );
    return toCamelCase<StrategyBacktestRunResponse>(response.data);
  },

  getHistory: async (
    params: { code?: string; limit?: number } = {},
  ): Promise<StrategyBacktestRunResponse[]> => {
    const queryParams: Record<string, string | number> = {};

    if (params.code) {
      queryParams.code = params.code;
    }

    if (params.limit != null) {
      queryParams.limit = params.limit;
    }

    const response = await apiClient.get<Record<string, unknown>[]>(
      '/api/v1/strategy-backtest/history',
      { params: queryParams },
    );
    return toCamelCase<StrategyBacktestRunResponse[]>(response.data);
  },

  getDetail: async (runId: number): Promise<StrategyBacktestRunDetail> => {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/strategy-backtest/${runId}`,
    );
    const data = toCamelCase<StrategyBacktestRunDetailApiResponse>(response.data);
    return normalizeRunDetail(data);
  },
};

export async function runStrategyBacktest(
  request: StrategyBacktestRequest,
): Promise<StrategyBacktestRunResponse> {
  return strategyBacktestApi.run(request);
}

export async function getRunHistory(
  code?: string,
  limit?: number,
): Promise<StrategyBacktestRunResponse[]> {
  return strategyBacktestApi.getHistory({ code, limit });
}

export async function getRunDetail(runId: number): Promise<StrategyBacktestRunDetail> {
  return strategyBacktestApi.getDetail(runId);
}
