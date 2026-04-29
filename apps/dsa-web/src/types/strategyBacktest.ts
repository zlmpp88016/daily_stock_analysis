/**
 * Strategy backtest API type definitions.
 * Mirrors api/v1/schemas/strategy_backtest.py.
 */

// ============ Indicator Config ============

export interface MAConfig {
  periods: number[];
}

export interface MACDConfig {
  fast: number;
  slow: number;
  signal: number;
}

export interface KDJConfig {
  n: number;
  k: number;
  d: number;
}

export interface BollConfig {
  period: number;
  stddev: number;
}

export interface IndicatorConfig {
  ma?: MAConfig;
  macd?: MACDConfig;
  kdj?: KDJConfig;
  boll?: BollConfig;
}

// ============ Request / Response ============

export interface StrategyBacktestRequest {
  code: string;
  startDate: string;
  endDate: string;
  initialCash: number;
  commissionRate?: number;
  slippageRate?: number;
  executionMode?: string;
  indicators: IndicatorConfig;
  buyRules: string[];
  sellRules: string[];
}

export interface StrategyBacktestSummary {
  totalReturn?: number;
  maxDrawdown?: number;
  winRate?: number;
  tradeCount: number;
  avgHoldingDays?: number;
}

export interface StrategyBacktestRunResponse extends StrategyBacktestSummary {
  id: number;
  code: string;
  startDate: string;
  endDate: string;
  initialCash: number;
  commissionRate: number;
  slippageRate: number;
  executionMode: string;
  indicators: IndicatorConfig;
  buyRules: string[];
  sellRules: string[];
  status: string;
  createdAt: string;
}

// ============ Detail Records ============

export interface StrategyBacktestTrade {
  id: number;
  runId: number;
  tradeType: string;
  tradeDate: string;
  price: number;
  shares: number;
  commission: number;
  profit?: number;
  profitRate?: number;
}

export interface StrategyBacktestEquity {
  id: number;
  runId: number;
  date: string;
  equity: number;
  cash: number;
  positionValue: number;
  drawdown?: number;
}

export interface StrategyBacktestRunDetail extends StrategyBacktestRunResponse {
  trades: StrategyBacktestTrade[];
  equity: StrategyBacktestEquity[];
}
