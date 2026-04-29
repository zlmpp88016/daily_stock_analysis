/**
 * Stock chart API type definitions.
 * Mirrors the frontend K-line payload contract.
 */

// ============ K-Line Records ============

export interface StockChartKlineItem {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount?: number;
  pctChg?: number;
}

export type StockChartPeriod = 'daily' | 'weekly' | 'monthly';

export type StockChartIndicator = 'macd' | 'kdj' | 'boll' | 'vol';

export interface StockChartMainIndicatorConfig {
  maPeriods: number[];
}

// ============ Request / Response ============

export interface StockChartResponse {
  code: string;
  name: string;
  period: StockChartPeriod;
  bars: StockChartKlineItem[];
}

export interface StockChartParams {
  code: string;
  period: StockChartPeriod;
  startDate?: string;
  endDate?: string;
}
