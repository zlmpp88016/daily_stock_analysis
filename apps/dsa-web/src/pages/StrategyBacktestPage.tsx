import type React from 'react';
import { useState } from 'react';
import { strategyBacktestApi } from '../api/strategyBacktest';
import type { ParsedApiError } from '../api/error';
import { createParsedApiError, getParsedApiError } from '../api/error';
import { ApiErrorAlert, Badge, Card, Collapsible } from '../components/common';
import { StockChartPanel } from '../components/stock-chart';
import { tryParseMaPeriodsInput } from '../components/stock-chart/utils';
import { EquityCurve, RuleBuilder, TradeTable } from '../components/strategy-backtest';
import type {
  IndicatorConfig,
  StrategyBacktestRequest,
  StrategyBacktestRunDetail,
  StrategyBacktestRunResponse,
} from '../types/strategyBacktest';
import { formatDateTime, getRecentStartDate, getTodayInShanghai } from '../utils/format';

type FormState = {
  code: string;
  startDate: string;
  endDate: string;
  initialCash: string;
  commissionRate: string;
  slippageRate: string;
  maPeriods: string;
  macdFast: string;
  macdSlow: string;
  macdSignal: string;
  kdjN: string;
  kdjK: string;
  kdjD: string;
  bollPeriod: string;
  bollStddev: string;
  buyRules: string[];
  sellRules: string[];
};

const currencyFormatter = new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
  maximumFractionDigits: 2,
});

function createDefaultFormState(): FormState {
  return {
    code: '',
    startDate: getRecentStartDate(365),
    endDate: getTodayInShanghai(),
    initialCash: '100000',
    commissionRate: '0.0003',
    slippageRate: '0.0005',
    maPeriods: '5, 20, 30',
    macdFast: '12',
    macdSlow: '26',
    macdSignal: '9',
    kdjN: '9',
    kdjK: '3',
    kdjD: '3',
    bollPeriod: '20',
    bollStddev: '2',
    buyRules: ['cross_over(ma_5, ma_20)', 'macd_dif > macd_dea'],
    sellRules: ['cross_under(ma_5, ma_20)', 'close < boll_lower'],
  };
}

function failValidation(message: string): never {
  throw createParsedApiError({
    title: '表单校验失败',
    message,
    rawMessage: message,
    category: 'missing_params',
  });
}

function parsePercent(value?: number | null): string {
  if (value == null) {
    return '--';
  }
  return `${(value * 100).toFixed(2)}%`;
}

function formatCurrency(value?: number | null): string {
  if (value == null) {
    return '--';
  }
  return currencyFormatter.format(value);
}

function parsePositiveNumber(
  value: string,
  label: string,
  options: { allowZero?: boolean; integer?: boolean; maxExclusive?: number } = {},
): number {
  const parsed = Number(value);
  const { allowZero = false, integer = false, maxExclusive } = options;

  if (!Number.isFinite(parsed)) {
    failValidation(`${label}必须是有效数字。`);
  }

  if (integer && !Number.isInteger(parsed)) {
    failValidation(`${label}必须是整数。`);
  }

  if (allowZero ? parsed < 0 : parsed <= 0) {
    failValidation(`${label}${allowZero ? '不能小于 0。' : '必须大于 0。'}`);
  }

  if (maxExclusive != null && parsed >= maxExclusive) {
    failValidation(`${label}必须小于 ${maxExclusive}。`);
  }

  return parsed;
}

function parseMaPeriods(value: string): number[] {
  const tokens = value
    .split(/[\s,，]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  if (tokens.length === 0) {
    failValidation('请至少填写一个 MA 周期。');
  }

  const periods = tokens.map((item) => Number(item));
  if (periods.some((item) => !Number.isInteger(item) || item <= 0)) {
    failValidation('MA 周期必须是正整数，多个值请用逗号分隔。');
  }

  return periods;
}

function parseRuleList(value: string[], label: string): string[] {
  const rules = value.map((item) => item.trim()).filter(Boolean);

  if (rules.length === 0) {
    failValidation(`请至少配置一条${label}。`);
  }

  return rules;
}

function buildRequest(form: FormState): StrategyBacktestRequest {
  const code = form.code.trim().toUpperCase();
  if (!code) {
    failValidation('请输入股票代码。');
  }

  if (!form.startDate) {
    failValidation('请选择开始日期。');
  }

  if (!form.endDate) {
    failValidation('请选择结束日期。');
  }

  if (form.startDate > form.endDate) {
    failValidation('开始日期不能晚于结束日期。');
  }

  return {
    code,
    startDate: form.startDate,
    endDate: form.endDate,
    initialCash: parsePositiveNumber(form.initialCash, '初始资金'),
    commissionRate: parsePositiveNumber(form.commissionRate, '手续费率', { allowZero: true, maxExclusive: 1 }),
    slippageRate: parsePositiveNumber(form.slippageRate, '滑点率', { allowZero: true, maxExclusive: 1 }),
    executionMode: 'next_open',
    indicators: {
      ma: {
        periods: parseMaPeriods(form.maPeriods),
      },
      macd: {
        fast: parsePositiveNumber(form.macdFast, 'MACD 快线', { integer: true }),
        slow: parsePositiveNumber(form.macdSlow, 'MACD 慢线', { integer: true }),
        signal: parsePositiveNumber(form.macdSignal, 'MACD 信号线', { integer: true }),
      },
      kdj: {
        n: parsePositiveNumber(form.kdjN, 'KDJ N', { integer: true }),
        k: parsePositiveNumber(form.kdjK, 'KDJ K', { integer: true }),
        d: parsePositiveNumber(form.kdjD, 'KDJ D', { integer: true }),
      },
      boll: {
        period: parsePositiveNumber(form.bollPeriod, 'BOLL 周期', { integer: true }),
        stddev: parsePositiveNumber(form.bollStddev, 'BOLL 标准差'),
      },
    },
    buyRules: parseRuleList(form.buyRules, '买入规则'),
    sellRules: parseRuleList(form.sellRules, '卖出规则'),
  };
}

function getStatusBadge(status?: string) {
  switch (status) {
    case 'completed':
      return (
        <Badge variant="success" glow>
          已完成
        </Badge>
      );
    case 'running':
      return (
        <Badge variant="info" glow>
          执行中
        </Badge>
      );
    case 'failed':
    case 'error':
      return (
        <Badge variant="danger" glow>
          执行失败
        </Badge>
      );
    default:
      return <Badge variant="default">{status || '待执行'}</Badge>;
  }
}

function getExecutionModeLabel(mode?: string): string {
  if (mode === 'next_open' || !mode) {
    return 'T+1 开盘成交';
  }
  return mode;
}

function getIndicatorSummary(indicators?: IndicatorConfig, form?: FormState): string[] {
  const ma = indicators?.ma?.periods?.join(', ') ?? form?.maPeriods ?? '--';
  const macd = indicators?.macd
    ? `${indicators.macd.fast}/${indicators.macd.slow}/${indicators.macd.signal}`
    : form
      ? `${form.macdFast}/${form.macdSlow}/${form.macdSignal}`
      : '--';
  const kdj = indicators?.kdj
    ? `${indicators.kdj.n}/${indicators.kdj.k}/${indicators.kdj.d}`
    : form
      ? `${form.kdjN}/${form.kdjK}/${form.kdjD}`
      : '--';
  const boll = indicators?.boll
    ? `${indicators.boll.period}/${indicators.boll.stddev}`
    : form
      ? `${form.bollPeriod}/${form.bollStddev}`
      : '--';

  return [
    `MA ${ma}`,
    `MACD ${macd}`,
    `KDJ ${kdj}`,
    `BOLL ${boll}`,
  ];
}

const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({
  label,
  hint,
  children,
}) => (
  <label className="block">
    <span className="mb-1.5 block text-xs font-medium text-secondary">{label}</span>
    {children}
    {hint ? <span className="mt-1 block text-[11px] text-muted">{hint}</span> : null}
  </label>
);

const SectionIntro: React.FC<{
  eyebrow?: string;
  title: string;
  description: string;
  trailing?: React.ReactNode;
}> = ({
  eyebrow,
  title,
  description,
  trailing,
}) => (
  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
    <div>
      {eyebrow ? <span className="label-uppercase">{eyebrow}</span> : null}
      <h2 className="mt-1 text-sm font-semibold text-white">{title}</h2>
      <p className="mt-1 text-xs text-muted">{description}</p>
    </div>
    {trailing ? <div className="flex flex-wrap items-center gap-2">{trailing}</div> : null}
  </div>
);

const SummaryItem: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="rounded-xl border border-white/5 bg-elevated/40 px-3 py-2.5">
    <p className="text-[11px] uppercase tracking-[0.18em] text-muted">{label}</p>
    <p className="mt-1 text-sm font-medium text-white">{value}</p>
  </div>
);

const MetricCard: React.FC<{
  label: string;
  value: string;
  tone?: 'default' | 'positive' | 'negative' | 'accent';
  hint?: string;
}> = ({
  label,
  value,
  tone = 'default',
  hint,
}) => {
  const toneClass = {
    default: 'text-white',
    positive: 'text-emerald-400',
    negative: 'text-red-400',
    accent: 'text-cyan',
  }[tone];

  return (
    <Card variant="gradient" padding="md" className="min-h-[132px]">
      <span className="label-uppercase">{label}</span>
      <div className={`mt-4 text-3xl font-mono font-semibold ${toneClass}`}>{value}</div>
      {hint ? <p className="mt-3 text-xs text-muted">{hint}</p> : null}
    </Card>
  );
};

type ActiveTab = 'backtest' | 'chart';

const StrategyBacktestPage: React.FC = () => {
  const [form, setForm] = useState<FormState>(() => createDefaultFormState());
  const [isRunning, setIsRunning] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [runError, setRunError] = useState<ParsedApiError | null>(null);
  const [detailError, setDetailError] = useState<ParsedApiError | null>(null);
  const [runResult, setRunResult] = useState<StrategyBacktestRunResponse | null>(null);
  const [runDetail, setRunDetail] = useState<StrategyBacktestRunDetail | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('backtest');

  const displayResult = runDetail ?? runResult;
  const draftCode = form.code.trim().toUpperCase() || '未设置';
  const draftIndicators = getIndicatorSummary(undefined, form);
  const displayIndicators = getIndicatorSummary(displayResult?.indicators, form);
  const buyRuleCount = displayResult?.buyRules.length ?? form.buyRules.filter((item) => item.trim()).length;
  const sellRuleCount = displayResult?.sellRules.length ?? form.sellRules.filter((item) => item.trim()).length;

  const updateField = <Key extends keyof FormState>(field: Key, value: FormState[Key]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsRunning(true);
    setIsLoadingDetail(false);
    setRunError(null);
    setDetailError(null);
    setRunResult(null);
    setRunDetail(null);

    try {
      const request = buildRequest(form);
      const response = await strategyBacktestApi.run(request);
      setRunResult(response);
      setIsLoadingDetail(true);

      try {
        const detail = await strategyBacktestApi.getDetail(response.id);
        setRunDetail(detail);
      } catch (error) {
        setDetailError(getParsedApiError(error));
      } finally {
        setIsLoadingDetail(false);
      }
    } catch (error) {
      setRunError(getParsedApiError(error));
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex-shrink-0 border-b border-white/5 px-4 py-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-white">策略回测</h1>
            <p className="mt-1 text-sm text-secondary">
              配置技术指标与买卖规则，在历史行情上快速验证策略表现。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="info" glow>
              独立策略回测
            </Badge>
            <Badge variant="default">执行模式：T+1 开盘成交</Badge>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-hidden p-4">
        <div className="grid h-full gap-4 xl:grid-cols-[minmax(340px,380px)_minmax(0,1fr)]">
          <section className="min-h-0 overflow-y-auto pr-1">
            <form className="flex flex-col gap-4 pb-1" onSubmit={(event) => void handleSubmit(event)}>
              <Card variant="gradient" padding="md">
                <SectionIntro
                  eyebrow="Draft"
                  title="策略草案"
                  description="先在左侧整理参数，再运行回测查看收益、回撤与交易明细。"
                  trailing={<Badge variant="default">{draftCode}</Badge>}
                />

                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                  <SummaryItem label="回测区间" value={`${form.startDate} 至 ${form.endDate}`} />
                  <SummaryItem label="初始资金" value={formatCurrency(Number(form.initialCash) || undefined)} />
                  <SummaryItem label="买入规则" value={`${form.buyRules.filter((item) => item.trim()).length} 条`} />
                  <SummaryItem label="卖出规则" value={`${form.sellRules.filter((item) => item.trim()).length} 条`} />
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {draftIndicators.map((item) => (
                    <Badge key={item} variant="default">
                      {item}
                    </Badge>
                  ))}
                </div>
              </Card>

              <Card padding="md">
                <SectionIntro
                  eyebrow="Inputs"
                  title="基础配置"
                  description="设置标的、区间、资金规模与交易成本。"
                  trailing={<Badge variant="default">必填</Badge>}
                />

                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                  <Field label="股票代码" hint="示例：600519 / 000001">
                    <input
                      type="text"
                      value={form.code}
                      onChange={(event) => updateField('code', event.target.value.replace(/\s+/g, '').toUpperCase())}
                      disabled={isRunning}
                      placeholder="请输入股票代码"
                      className="input-terminal w-full"
                    />
                  </Field>

                  <Field label="开始日期">
                    <input
                      type="date"
                      value={form.startDate}
                      onChange={(event) => updateField('startDate', event.target.value)}
                      disabled={isRunning}
                      className="input-terminal w-full"
                    />
                  </Field>

                  <Field label="结束日期">
                    <input
                      type="date"
                      value={form.endDate}
                      onChange={(event) => updateField('endDate', event.target.value)}
                      disabled={isRunning}
                      className="input-terminal w-full"
                    />
                  </Field>

                  <Field label="初始资金">
                    <input
                      type="number"
                      min="1"
                      step="any"
                      value={form.initialCash}
                      onChange={(event) => updateField('initialCash', event.target.value)}
                      disabled={isRunning}
                      className="input-terminal w-full"
                    />
                  </Field>

                  <Field label="手续费率" hint="默认 0.0003">
                    <input
                      type="number"
                      min="0"
                      max="0.9999"
                      step="0.0001"
                      value={form.commissionRate}
                      onChange={(event) => updateField('commissionRate', event.target.value)}
                      disabled={isRunning}
                      className="input-terminal w-full"
                    />
                  </Field>

                  <Field label="滑点率" hint="默认 0.0005">
                    <input
                      type="number"
                      min="0"
                      max="0.9999"
                      step="0.0001"
                      value={form.slippageRate}
                      onChange={(event) => updateField('slippageRate', event.target.value)}
                      disabled={isRunning}
                      className="input-terminal w-full"
                    />
                  </Field>
                </div>
              </Card>

              <Card padding="md">
                <SectionIntro
                  eyebrow="Indicators"
                  title="指标参数"
                  description="保持和现有页面一致的卡片层级，把复杂参数收在折叠面板里。"
                />

                <div className="mt-4 space-y-3">
                  <Collapsible title="MA 均线参数" defaultOpen>
                    <Field label="均线周期" hint="多个周期用逗号分隔，例如 5, 20, 30">
                      <input
                        type="text"
                        value={form.maPeriods}
                        onChange={(event) => updateField('maPeriods', event.target.value)}
                        disabled={isRunning}
                        className="input-terminal w-full"
                      />
                    </Field>
                  </Collapsible>

                  <Collapsible title="MACD 参数">
                    <div className="grid gap-3 sm:grid-cols-3">
                      <Field label="快线">
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={form.macdFast}
                          onChange={(event) => updateField('macdFast', event.target.value)}
                          disabled={isRunning}
                          className="input-terminal w-full"
                        />
                      </Field>
                      <Field label="慢线">
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={form.macdSlow}
                          onChange={(event) => updateField('macdSlow', event.target.value)}
                          disabled={isRunning}
                          className="input-terminal w-full"
                        />
                      </Field>
                      <Field label="信号线">
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={form.macdSignal}
                          onChange={(event) => updateField('macdSignal', event.target.value)}
                          disabled={isRunning}
                          className="input-terminal w-full"
                        />
                      </Field>
                    </div>
                  </Collapsible>

                  <Collapsible title="KDJ 参数">
                    <div className="grid gap-3 sm:grid-cols-3">
                      <Field label="N">
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={form.kdjN}
                          onChange={(event) => updateField('kdjN', event.target.value)}
                          disabled={isRunning}
                          className="input-terminal w-full"
                        />
                      </Field>
                      <Field label="K">
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={form.kdjK}
                          onChange={(event) => updateField('kdjK', event.target.value)}
                          disabled={isRunning}
                          className="input-terminal w-full"
                        />
                      </Field>
                      <Field label="D">
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={form.kdjD}
                          onChange={(event) => updateField('kdjD', event.target.value)}
                          disabled={isRunning}
                          className="input-terminal w-full"
                        />
                      </Field>
                    </div>
                  </Collapsible>

                  <Collapsible title="BOLL 参数">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Field label="周期">
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={form.bollPeriod}
                          onChange={(event) => updateField('bollPeriod', event.target.value)}
                          disabled={isRunning}
                          className="input-terminal w-full"
                        />
                      </Field>
                      <Field label="标准差">
                        <input
                          type="number"
                          min="0.1"
                          step="0.1"
                          value={form.bollStddev}
                          onChange={(event) => updateField('bollStddev', event.target.value)}
                          disabled={isRunning}
                          className="input-terminal w-full"
                        />
                      </Field>
                    </div>
                  </Collapsible>
                </div>
              </Card>

              <Card padding="md">
                <SectionIntro
                  eyebrow="Rules"
                  title="规则配置"
                  description="通过结构化编辑生成后端可识别的规则表达式，避免窄栏里出现挤压错位。"
                  trailing={<Badge variant="info">结构化编辑</Badge>}
                />

                <div className="mt-4 space-y-3">
                  <RuleBuilder
                    label="买入规则"
                    value={form.buyRules}
                    onChange={(rules) => updateField('buyRules', rules)}
                  />
                  <RuleBuilder
                    label="卖出规则"
                    value={form.sellRules}
                    onChange={(rules) => updateField('sellRules', rules)}
                  />
                </div>
              </Card>

              <div className="xl:sticky xl:bottom-0 xl:z-10 xl:pt-2">
                <Card variant="gradient" padding="md">
                  <SectionIntro
                    eyebrow="Run"
                    title="执行回测"
                    description="提交当前参数后，右侧会刷新收益指标、权益曲线和交易明细。"
                    trailing={getStatusBadge(isRunning ? 'running' : displayResult?.status)}
                  />

                  <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                    <SummaryItem label="执行模式" value="T+1 开盘成交" />
                    <SummaryItem label="当前标的" value={displayResult?.code ?? draftCode} />
                  </div>

                  <button type="submit" disabled={isRunning} className="btn-primary mt-4 w-full">
                    {isRunning ? '正在执行策略回测...' : '运行策略回测'}
                  </button>
                </Card>
              </div>
            </form>
          </section>

          <section className="min-h-0 overflow-y-auto">
            <div className="flex flex-col gap-4 pb-1">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <span className="label-uppercase">Right Panel</span>
                  <h2 className="mt-2 text-lg font-semibold text-white">结果与看盘</h2>
                  <p className="mt-1 text-sm text-secondary">
                    默认保留回测结果面板，也可切换到个股 K 线看盘视图。
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="右侧面板切换">
                  <button
                    type="button"
                    onClick={() => setActiveTab('backtest')}
                    role="tab"
                    aria-selected={activeTab === 'backtest'}
                    className="transition-transform hover:-translate-y-0.5"
                  >
                    <Badge
                      variant={activeTab === 'backtest' ? 'info' : 'default'}
                      glow={activeTab === 'backtest'}
                      size="md"
                      className="pointer-events-none"
                    >
                      回测结果
                    </Badge>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab('chart')}
                    role="tab"
                    aria-selected={activeTab === 'chart'}
                    className="transition-transform hover:-translate-y-0.5"
                  >
                    <Badge
                      variant={activeTab === 'chart' ? 'info' : 'default'}
                      glow={activeTab === 'chart'}
                      size="md"
                      className="pointer-events-none"
                    >
                      个股看盘
                    </Badge>
                  </button>
                </div>
              </div>

              {activeTab === 'backtest' ? (
                <>
                  <Card variant="gradient" padding="lg">
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div>
                        <span className="label-uppercase">Latest Run</span>
                        <h2 className="mt-2 text-lg font-semibold text-white">回测结果面板</h2>
                        <p className="mt-1 text-sm text-secondary">
                          {displayResult
                            ? `${displayResult.code} · ${displayResult.startDate} 至 ${displayResult.endDate}`
                            : '填写左侧配置后运行策略回测，这里会显示最新一次执行结果和配置快照。'}
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        {getStatusBadge(isRunning ? 'running' : displayResult?.status)}
                        {isLoadingDetail ? <Badge variant="default">明细加载中</Badge> : null}
                        <Badge variant="default">{getExecutionModeLabel(displayResult?.executionMode)}</Badge>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 border-t border-white/5 pt-4 sm:grid-cols-2 xl:grid-cols-4">
                      <SummaryItem
                        label="创建时间"
                        value={displayResult ? formatDateTime(displayResult.createdAt) : '等待执行'}
                      />
                      <SummaryItem
                        label="初始资金"
                        value={formatCurrency(displayResult?.initialCash ?? (Number(form.initialCash) || undefined))}
                      />
                      <SummaryItem
                        label="成本设置"
                        value={`${parsePercent(displayResult?.commissionRate ?? (Number(form.commissionRate) || 0))} / ${parsePercent(displayResult?.slippageRate ?? (Number(form.slippageRate) || 0))}`}
                      />
                      <SummaryItem
                        label="规则数量"
                        value={`买入 ${buyRuleCount} 条 / 卖出 ${sellRuleCount} 条`}
                      />
                    </div>
                  </Card>

                  {runError ? <ApiErrorAlert error={runError} /> : null}
                  {detailError ? <ApiErrorAlert error={detailError} /> : null}

                  {isRunning ? (
                    <Card padding="lg">
                      <div className="flex min-h-[168px] flex-col items-center justify-center">
                        <div className="h-10 w-10 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
                        <p className="mt-4 text-sm font-medium text-white">正在执行策略回测</p>
                        <p className="mt-1 text-xs text-muted">
                          回测请求已提交，结果摘要和权益曲线会在明细返回后自动更新。
                        </p>
                      </div>
                    </Card>
                  ) : null}

                  <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
                    <MetricCard
                      label="总收益率"
                      value={parsePercent(displayResult?.totalReturn)}
                      tone={(displayResult?.totalReturn ?? 0) > 0 ? 'positive' : (displayResult?.totalReturn ?? 0) < 0 ? 'negative' : 'default'}
                      hint="总资产相对初始资金的变化比例"
                    />
                    <MetricCard
                      label="最大回撤"
                      value={parsePercent(displayResult?.maxDrawdown)}
                      tone={displayResult?.maxDrawdown ? 'negative' : 'default'}
                      hint="历史净值曲线中的最大回撤幅度"
                    />
                    <MetricCard
                      label="胜率"
                      value={parsePercent(displayResult?.winRate)}
                      tone={displayResult?.winRate != null && displayResult.winRate >= 0.5 ? 'positive' : 'accent'}
                      hint="已闭合交易中盈利交易的占比"
                    />
                    <MetricCard
                      label="交易次数"
                      value={displayResult ? String(displayResult.tradeCount) : '--'}
                      tone="accent"
                      hint={
                        displayResult?.avgHoldingDays != null
                          ? `平均持仓 ${displayResult.avgHoldingDays.toFixed(1)} 天`
                          : '尚无足够交易记录计算平均持仓'
                      }
                    />
                  </div>

                  <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
                    <EquityCurve equity={runDetail?.equity ?? []} />

                    <Card padding="lg" className="h-full">
                      <SectionIntro
                        eyebrow="Snapshot"
                        title="配置与执行快照"
                        description="把当前草案和最近一次执行结果集中展示，方便对照参数是否符合预期。"
                      />

                      <div className="mt-4 grid gap-3 sm:grid-cols-2 2xl:grid-cols-1">
                        <SummaryItem label="标的" value={displayResult?.code ?? draftCode} />
                        <SummaryItem
                          label="回测区间"
                          value={`${displayResult?.startDate ?? form.startDate} 至 ${displayResult?.endDate ?? form.endDate}`}
                        />
                        <SummaryItem
                          label="执行模式"
                          value={getExecutionModeLabel(displayResult?.executionMode)}
                        />
                        <SummaryItem
                          label="买入 / 卖出"
                          value={`${buyRuleCount} 条 / ${sellRuleCount} 条`}
                        />
                      </div>

                      <div className="mt-4 rounded-xl border border-white/5 bg-elevated/30 px-3 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-muted">指标摘要</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {displayIndicators.map((item) => (
                            <Badge key={item} variant="default">
                              {item}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      <div className="mt-4 rounded-xl border border-dashed border-white/10 bg-black/10 px-3 py-3">
                        <p className="text-sm font-medium text-white">
                          {displayResult ? '结果已就绪，可继续微调参数后再次执行。' : '当前还没有执行结果。'}
                        </p>
                        <p className="mt-1 text-xs text-muted">
                          {displayResult
                            ? '如果想比较不同参数组合，建议只调整一组指标或一套规则，再重新运行。'
                            : '先完成左侧参数配置，再发起回测。权益曲线和交易明细会在明细返回后自动填充。'}
                        </p>
                      </div>
                    </Card>
                  </div>

                  <TradeTable trades={runDetail?.trades ?? []} />
                </>
              ) : (
                <StockChartPanel
                  defaultCode={form.code.trim().toUpperCase()}
                  defaultMaPeriods={tryParseMaPeriodsInput(form.maPeriods)}
                />
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default StrategyBacktestPage;
