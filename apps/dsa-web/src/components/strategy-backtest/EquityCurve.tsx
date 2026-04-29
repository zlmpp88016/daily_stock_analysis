import type React from 'react';
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card, Badge } from '../common';
import type { StrategyBacktestEquity } from '../../types/strategyBacktest';

interface EquityCurveProps {
  equity: StrategyBacktestEquity[];
}

const currencyFormatter = new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
  maximumFractionDigits: 2,
});

const percentFormatter = new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatCurrency(value: number): string {
  return currencyFormatter.format(value);
}

function formatDrawdown(value?: number | null): string {
  if (value == null) {
    return '--';
  }
  return `${percentFormatter.format(Math.abs(value) * 100)}%`;
}

export const EquityCurve: React.FC<EquityCurveProps> = ({ equity }) => {
  const chartData = equity.map((point) => ({
    date: point.date,
    equity: point.equity,
    drawdown: -Math.abs((point.drawdown ?? 0) * 100),
    rawDrawdown: point.drawdown ?? 0,
    cash: point.cash,
    positionValue: point.positionValue,
  }));

  return (
    <Card padding="lg" className="h-full">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-white">资金曲线</h3>
          <p className="mt-1 text-xs text-muted">展示账户净值变化，并用红色区域标记回撤幅度。</p>
        </div>
        <Badge variant="info">权益曲线</Badge>
      </div>

      {chartData.length === 0 ? (
        <div className="mt-4 flex min-h-[260px] items-center justify-center rounded-xl border border-dashed border-white/10 bg-black/10">
          <div className="max-w-xs text-center">
            <p className="text-sm text-secondary">暂无资金曲线数据</p>
            <p className="mt-2 text-xs text-muted">运行策略回测后，这里会显示每日净值与回撤变化。</p>
          </div>
        </div>
      ) : (
        <div className="mt-4 h-[320px] rounded-xl border border-white/5 bg-gray-800/70 p-3">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 12, right: 12, bottom: 8, left: 0 }}>
              <defs>
                <linearGradient id="equity-drawdown-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f87171" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#7f1d1d" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                tickLine={false}
                minTickGap={28}
              />
              <YAxis
                yAxisId="equity"
                tick={{ fill: '#e2e8f0', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={88}
                tickFormatter={(value: number) => formatCurrency(value)}
              />
              <YAxis
                yAxisId="drawdown"
                orientation="right"
                hide
                domain={[(dataMin: number) => Math.min(dataMin, -1), 0]}
              />
              <Tooltip
                cursor={{ stroke: 'rgba(16,185,129,0.3)', strokeWidth: 1 }}
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.96)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '12px',
                  boxShadow: '0 12px 40px rgba(2, 6, 23, 0.36)',
                }}
                labelStyle={{ color: '#f8fafc', fontWeight: 600, marginBottom: 8 }}
                formatter={(value, name, item) => {
                  const numericValue = typeof value === 'number' ? value : Number(value ?? 0);
                  if (name === 'equity') {
                    return [formatCurrency(numericValue), '总权益'];
                  }
                  const payload = item && 'payload' in item ? item.payload as { rawDrawdown?: number } : undefined;
                  return [formatDrawdown(payload?.rawDrawdown), '回撤'];
                }}
              />
              <Area
                yAxisId="drawdown"
                type="monotone"
                dataKey="drawdown"
                stroke="#f87171"
                strokeWidth={1}
                fill="url(#equity-drawdown-fill)"
                isAnimationActive={false}
              />
              <Line
                yAxisId="equity"
                type="monotone"
                dataKey="equity"
                stroke="#4ade80"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 4, stroke: '#022c22', strokeWidth: 2, fill: '#4ade80' }}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
};
