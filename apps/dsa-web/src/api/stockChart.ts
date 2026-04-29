import apiClient from './index';
import { toCamelCase } from './utils';
import type { StockChartParams, StockChartResponse } from '../types/stockChart';

function buildKlineQueryParams(params: StockChartParams): Record<string, string> {
  const queryParams: Record<string, string> = {
    period: params.period,
  };

  if (params.startDate) {
    queryParams.start_date = params.startDate;
  }

  if (params.endDate) {
    queryParams.end_date = params.endDate;
  }

  return queryParams;
}

export const stockChartApi = {
  getKlineData: async (params: StockChartParams): Promise<StockChartResponse> => {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/kline/${encodeURIComponent(params.code)}`,
      {
        params: buildKlineQueryParams(params),
      },
    );

    return toCamelCase<StockChartResponse>(response.data);
  },
};

export async function getStockChartKlineData(params: StockChartParams): Promise<StockChartResponse> {
  return stockChartApi.getKlineData(params);
}
