import type React from 'react';
import { useEffect, useRef } from 'react';
import { dispose, init } from 'klinecharts';
import type { Chart, KLineData } from 'klinecharts';
import type { StockChartKlineItem } from '../../types/stockChart';
import { normalizeMaPeriods } from './utils';

interface KLineChartProps {
  data: StockChartKlineItem[];
  indicators: string[];
  maPeriods?: number[];
  height?: number;
  className?: string;
}

type IndicatorBinding = {
  id?: string;
  name: string;
  paneId?: string;
};

type CompatibleChart = Chart & {
  applyNewData?: (data: KLineData[]) => void;
};

const CANDLE_PANE_ID = 'candle_pane';
const SUB_PANE_HEIGHT = 96;
const SUB_PANE_MIN_HEIGHT = 72;
const CANDLE_PANE_MIN_HEIGHT = 260;

const INDICATOR_NAME_MAP: Record<string, string> = {
  macd: 'MACD',
  kdj: 'KDJ',
  boll: 'BOLL',
  vol: 'VOL',
};

const OVERLAY_INDICATORS = new Set(['MA', 'BOLL']);

function toChartData(data: StockChartKlineItem[]): KLineData[] {
  return data
    .map((item) => ({
      timestamp: new Date(item.date).getTime(),
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
      volume: item.volume,
      turnover: item.amount,
    }))
    .filter((item) => Number.isFinite(item.timestamp));
}

function normalizeIndicators(indicators: string[]): string[] {
  return [
    ...new Set(
      indicators
        .map((indicator) => INDICATOR_NAME_MAP[indicator.toLowerCase()] ?? indicator.toUpperCase())
        .filter(Boolean),
    ),
  ];
}

function removeIndicators(chart: CompatibleChart, bindings: IndicatorBinding[]): void {
  bindings.forEach(({ id, name, paneId }) => {
    if (id) {
      chart.removeIndicator({ id });
      return;
    }

    if (paneId) {
      chart.removeIndicator({ name, paneId });
      return;
    }

    chart.removeIndicator({ name });
  });
}

function createIndicators(chart: CompatibleChart, indicators: string[], maPeriods: number[]): IndicatorBinding[] {
  const normalizedIndicators = normalizeIndicators(indicators);
  const bindings: IndicatorBinding[] = [];

  if (maPeriods.length > 0) {
    const id = chart.createIndicator(
      {
        name: 'MA',
        calcParams: maPeriods,
      },
      false,
      { id: CANDLE_PANE_ID },
    ) ?? undefined;
    bindings.push({ id, name: 'MA', paneId: CANDLE_PANE_ID });
  }

  normalizedIndicators.forEach((name) => {
    if (OVERLAY_INDICATORS.has(name)) {
      const id = chart.createIndicator(name, false, { id: CANDLE_PANE_ID }) ?? undefined;
      bindings.push({ id, name, paneId: CANDLE_PANE_ID });
      return;
    }

    const id = chart.createIndicator(name, false, {
      height: SUB_PANE_HEIGHT,
      minHeight: SUB_PANE_MIN_HEIGHT,
    }) ?? undefined;
    bindings.push({ id, name });
  });

  return bindings;
}

function applyChartData(chart: CompatibleChart, data: KLineData[]): void {
  if (typeof chart.applyNewData === 'function') {
    chart.applyNewData(data);
    return;
  }

  chart.setDataLoader({
    getBars: ({ callback }) => {
      callback(data, false);
    },
  });
  chart.resetData();
}

export const KLineChart: React.FC<KLineChartProps> = ({
  data,
  indicators,
  maPeriods,
  height = 520,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<CompatibleChart | null>(null);
  const indicatorBindingsRef = useRef<IndicatorBinding[]>([]);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const chart = init(containerRef.current) as CompatibleChart | null;
    if (!chart) {
      return;
    }

    chart.setLocale('zh-CN');
    chart.setTimezone('Asia/Shanghai');
    chart.setSymbol({
      ticker: 'stock',
      pricePrecision: 2,
      volumePrecision: 0,
    });
    chart.setPeriod({
      type: 'day',
      span: 1,
    });
    chart.setPaneOptions({
      id: CANDLE_PANE_ID,
      minHeight: CANDLE_PANE_MIN_HEIGHT,
    });

    chartRef.current = chart;

    const resizeObserver = new ResizeObserver(() => {
      chart.resize();
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      removeIndicators(chart, indicatorBindingsRef.current);
      indicatorBindingsRef.current = [];
      chartRef.current = null;
      dispose(chart);
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) {
      return;
    }

    const chartData = toChartData(data);
    applyChartData(chart, chartData);

    if (chartData.length > 0) {
      chart.scrollToRealTime();
    }
  }, [data]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) {
      return;
    }

    removeIndicators(chart, indicatorBindingsRef.current);
    indicatorBindingsRef.current = createIndicators(chart, indicators, normalizeMaPeriods(maPeriods));
  }, [indicators, maPeriods]);

  return (
    <div className={className}>
      <div ref={containerRef} className="w-full" style={{ height }} />
    </div>
  );
};
