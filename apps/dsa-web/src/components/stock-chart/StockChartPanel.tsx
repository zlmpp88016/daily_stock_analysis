import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import type { ParsedApiError } from '../../api/error';
import { getParsedApiError } from '../../api/error';
import { stockChartApi } from '../../api/stockChart';
import type {
  StockChartIndicator,
  StockChartKlineItem,
  StockChartPeriod,
  StockChartResponse,
} from '../../types/stockChart';
import { ApiErrorAlert, Badge, Card, Loading } from '../common';
import { KLineChart } from './KLineChart';
import { formatMaPeriodsInput, normalizeMaPeriods, parseMaPeriodsInput } from './utils';

interface StockChartPanelProps {
  defaultCode?: string;
  defaultMaPeriods?: number[];
  className?: string;
}

type ChartInfo = Pick<StockChartResponse, 'code' | 'name' | 'period'>;

const PERIOD_OPTIONS: Array<{ label: string; value: StockChartPeriod }> = [
  { label: '日K', value: 'daily' },
  { label: '周K', value: 'weekly' },
  { label: '月K', value: 'monthly' },
];

const INDICATOR_OPTIONS: Array<{ label: string; value: StockChartIndicator }> = [
  { label: 'MACD', value: 'macd' },
  { label: 'KDJ', value: 'kdj' },
  { label: 'BOLL', value: 'boll' },
  { label: 'VOL', value: 'vol' },
];

const PERIOD_LABEL_MAP: Record<StockChartPeriod, string> = {
  daily: '日K',
  weekly: '周K',
  monthly: '月K',
};

export const StockChartPanel: React.FC<StockChartPanelProps> = ({
  defaultCode = '',
  defaultMaPeriods,
  className = '',
}) => {
  const normalizedDefaultCode = defaultCode.trim().toUpperCase();
  const normalizedDefaultMaPeriods = normalizeMaPeriods(defaultMaPeriods);
  const [code, setCode] = useState(normalizedDefaultCode);
  const [period, setPeriod] = useState<StockChartPeriod>('daily');
  const [enabledIndicators, setEnabledIndicators] = useState<Set<StockChartIndicator>>(
    () => new Set(['vol']),
  );
  const [maInput, setMaInput] = useState(() => formatMaPeriodsInput(normalizedDefaultMaPeriods));
  const [maPeriods, setMaPeriods] = useState<number[]>(() => normalizedDefaultMaPeriods);
  const [maInputError, setMaInputError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<StockChartKlineItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [chartInfo, setChartInfo] = useState<ChartInfo | null>(null);
  const lastDefaultCodeRef = useRef(normalizedDefaultCode);
  const lastDefaultMaPeriodsRef = useRef(formatMaPeriodsInput(normalizedDefaultMaPeriods));
  const requestIdRef = useRef(0);

  useEffect(() => {
    if (normalizedDefaultCode === lastDefaultCodeRef.current) {
      return;
    }

    lastDefaultCodeRef.current = normalizedDefaultCode;
    queueMicrotask(() => {
      setCode(normalizedDefaultCode);
    });
  }, [normalizedDefaultCode]);

  useEffect(() => {
    const serializedPeriods = formatMaPeriodsInput(normalizedDefaultMaPeriods);
    if (serializedPeriods === lastDefaultMaPeriodsRef.current) {
      return;
    }

    lastDefaultMaPeriodsRef.current = serializedPeriods;
    queueMicrotask(() => {
      setMaInput(serializedPeriods);
      setMaPeriods(normalizedDefaultMaPeriods);
      setMaInputError(null);
    });
  }, [normalizedDefaultMaPeriods]);

  useEffect(() => {
    const normalizedCode = code.trim().toUpperCase();

    if (!normalizedCode) {
      requestIdRef.current += 1;
      queueMicrotask(() => {
        setChartData([]);
        setChartInfo(null);
        setError(null);
        setIsLoading(false);
      });
      return;
    }

    const requestId = ++requestIdRef.current;
    const timer = window.setTimeout(() => {
      setIsLoading(true);
      setError(null);
      setChartData([]);
      setChartInfo(null);

      void stockChartApi.getKlineData({
        code: normalizedCode,
        period,
      })
        .then((response) => {
          if (requestId !== requestIdRef.current) {
            return;
          }

          setChartData(response.bars ?? []);
          setChartInfo({
            code: response.code,
            name: response.name,
            period: response.period,
          });
        })
        .catch((requestError) => {
          if (requestId !== requestIdRef.current) {
            return;
          }

          setError(getParsedApiError(requestError));
          setChartData([]);
          setChartInfo(null);
        })
        .finally(() => {
          if (requestId === requestIdRef.current) {
            setIsLoading(false);
          }
        });
    }, 360);

    return () => {
      window.clearTimeout(timer);
    };
  }, [code, period]);

  const normalizedCode = code.trim().toUpperCase();
  const indicatorList = INDICATOR_OPTIONS
    .filter((option) => enabledIndicators.has(option.value))
    .map((option) => option.value);

  const toggleIndicator = (indicator: StockChartIndicator) => {
    setEnabledIndicators((previous) => {
      const next = new Set(previous);

      if (next.has(indicator)) {
        next.delete(indicator);
      } else {
        next.add(indicator);
      }

      return next;
    });
  };

  const handleMaInputChange = (value: string) => {
    setMaInput(value);

    try {
      const nextPeriods = parseMaPeriodsInput(value);
      setMaPeriods(nextPeriods);
      setMaInputError(null);
    } catch (validationError) {
      setMaInputError(validationError instanceof Error ? validationError.message : 'MA 周期格式不正确。');
    }
  };

  return (
    <div className={`flex flex-col gap-4 ${className}`.trim()}>
      <Card variant="gradient" padding="lg">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <span className="label-uppercase">Chart</span>
              <h2 className="mt-2 text-lg font-semibold text-white">个股看盘</h2>
              <p className="mt-1 text-sm text-secondary">
                切换周期并叠加常用技术指标，快速查看个股 K 线走势。
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {chartInfo?.code ? (
                <Badge variant="info" glow>
                  {chartInfo.code}
                </Badge>
              ) : (
                <Badge variant="default">待输入</Badge>
              )}
              {chartInfo?.name ? <Badge variant="default">{chartInfo.name}</Badge> : null}
              {chartInfo ? <Badge variant="default">{PERIOD_LABEL_MAP[chartInfo.period]}</Badge> : null}
              {chartData.length > 0 ? <Badge variant="default">{chartData.length} 根K线</Badge> : null}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(220px,260px)_minmax(0,1fr)]">
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-secondary">股票代码</span>
              <input
                type="text"
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\s+/g, '').toUpperCase())}
                placeholder="请输入股票代码"
                className="input-terminal w-full"
              />
            </label>

            <div className="grid gap-3">
              <div>
                <span className="block text-xs font-medium text-secondary">周期</span>
                <div className="mt-2 flex flex-wrap gap-2">
                  {PERIOD_OPTIONS.map((option) => {
                    const isActive = period === option.value;

                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setPeriod(option.value)}
                        className="transition-transform hover:-translate-y-0.5"
                        role="tab"
                        aria-selected={isActive}
                      >
                        <Badge
                          variant={isActive ? 'info' : 'default'}
                          glow={isActive}
                          size="md"
                          className="pointer-events-none"
                        >
                          {option.label}
                        </Badge>
                      </button>
                    );
                  })}
                </div>
              </div>

              <label className="block">
                <span className="block text-xs font-medium text-secondary">均线配置</span>
                <input
                  type="text"
                  value={maInput}
                  onChange={(event) => handleMaInputChange(event.target.value)}
                  placeholder="例如 5, 10, 30, 200"
                  className="input-terminal mt-2 w-full"
                />
                <span className="mt-1 block text-[11px] text-muted">
                  可自定义多条 MA，例如 5、10、30、200 或手动输入 22。
                </span>
                {maInputError ? <span className="mt-1 block text-[11px] text-red-400">{maInputError}</span> : null}
              </label>

              <div>
                <span className="block text-xs font-medium text-secondary">指标</span>
                <div className="mt-2 flex flex-wrap gap-2">
                  {INDICATOR_OPTIONS.map((option) => {
                    const isActive = enabledIndicators.has(option.value);

                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => toggleIndicator(option.value)}
                        className="transition-transform hover:-translate-y-0.5"
                        aria-pressed={isActive}
                      >
                        <Badge
                          variant={isActive ? 'info' : 'default'}
                          glow={isActive}
                          size="md"
                          className="pointer-events-none"
                        >
                          {option.label}
                        </Badge>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {error ? <ApiErrorAlert error={error} /> : null}

      <Card padding="lg" className="min-h-[620px]">
        {!normalizedCode ? (
          <div className="flex min-h-[540px] flex-col items-center justify-center text-center">
            <p className="text-sm font-medium text-white">输入股票代码后查看 K 线</p>
            <p className="mt-2 text-xs text-muted">
              支持切换日 K、周 K、月 K，并叠加 MACD / KDJ / BOLL / VOL。
            </p>
          </div>
        ) : isLoading ? (
          <div className="flex min-h-[540px] flex-col items-center justify-center">
            <Loading />
            <p className="mt-3 text-sm text-secondary">加载 K 线数据中...</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="default">MA {maPeriods.join(' / ')}</Badge>
              {indicatorList.length > 0 ? (
                indicatorList.map((indicator) => (
                  <Badge key={indicator} variant="default">
                    {indicator.toUpperCase()}
                  </Badge>
                ))
              ) : (
                <Badge variant="default">无附加指标</Badge>
              )}
            </div>

            <KLineChart
              data={chartData}
              indicators={indicatorList}
              maPeriods={maPeriods}
              height={540}
              className="rounded-2xl border border-white/5 bg-base/60"
            />

            {chartData.length === 0 ? (
              <p className="text-center text-xs text-muted">当前条件下暂无 K 线数据。</p>
            ) : null}
          </div>
        )}
      </Card>
    </div>
  );
};
