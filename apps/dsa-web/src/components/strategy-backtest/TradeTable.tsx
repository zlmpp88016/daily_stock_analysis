import type React from 'react';
import { useState } from 'react';
import { Badge, Card } from '../common';
import type { StrategyBacktestTrade } from '../../types/strategyBacktest';

interface TradeTableProps {
  trades: StrategyBacktestTrade[];
}

type SortKey = 'tradeType' | 'tradeDate' | 'price' | 'shares' | 'commission' | 'profit' | 'profitRate';
type SortDirection = 'asc' | 'desc';

const currencyFormatter = new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
  maximumFractionDigits: 2,
});

const numberFormatter = new Intl.NumberFormat('zh-CN', {
  maximumFractionDigits: 0,
});

function formatCurrency(value?: number | null): string {
  if (value == null) {
    return '--';
  }
  return currencyFormatter.format(value);
}

function formatPercent(value?: number | null): string {
  if (value == null) {
    return '--';
  }
  return `${(value * 100).toFixed(2)}%`;
}

function getTradeTypeLabel(value: string): string {
  return value === 'buy' ? '买' : value === 'sell' ? '卖' : value;
}

function getNextDirection(currentKey: SortKey, currentDirection: SortDirection, nextKey: SortKey): SortDirection {
  if (currentKey !== nextKey) {
    return nextKey === 'tradeDate' ? 'desc' : 'asc';
  }
  return currentDirection === 'asc' ? 'desc' : 'asc';
}

export const TradeTable: React.FC<TradeTableProps> = ({ trades }) => {
  const [sortKey, setSortKey] = useState<SortKey>('tradeDate');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const sortedTrades = [...trades].sort((left, right) => {
    const leftValue = left[sortKey];
    const rightValue = right[sortKey];

    if (leftValue == null && rightValue == null) {
      return 0;
    }

    if (leftValue == null) {
      return 1;
    }

    if (rightValue == null) {
      return -1;
    }

    let result = 0;
    if (typeof leftValue === 'string' && typeof rightValue === 'string') {
      result = leftValue.localeCompare(rightValue, 'zh-CN');
    } else {
      result = Number(leftValue) - Number(rightValue);
    }

    return sortDirection === 'asc' ? result : -result;
  });

  const handleSort = (nextKey: SortKey) => {
    const nextDirection = getNextDirection(sortKey, sortDirection, nextKey);
    setSortKey(nextKey);
    setSortDirection(nextDirection);
  };

  return (
    <Card padding="lg" className="h-full">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-white">交易明细</h3>
          <p className="mt-1 text-xs text-muted">点击表头可按字段排序，快速查看买卖记录与收益表现。</p>
        </div>
        <Badge variant="default">{trades.length} 笔</Badge>
      </div>

      {trades.length === 0 ? (
        <div className="mt-4 flex min-h-[260px] items-center justify-center rounded-xl border border-dashed border-white/10 bg-black/10">
          <div className="max-w-xs text-center">
            <p className="text-sm text-secondary">暂无交易记录</p>
            <p className="mt-2 text-xs text-muted">策略未触发买卖时，这里会保留为空状态。</p>
          </div>
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-xl border border-white/5">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-elevated text-left">
                {[
                  { key: 'tradeType', label: '类型' },
                  { key: 'tradeDate', label: '日期' },
                  { key: 'price', label: '成交价' },
                  { key: 'shares', label: '股数' },
                  { key: 'commission', label: '手续费' },
                  { key: 'profit', label: '盈亏' },
                  { key: 'profitRate', label: '收益率' },
                ].map((column) => {
                  const isActive = sortKey === column.key;
                  const indicator = isActive ? (sortDirection === 'asc' ? '↑' : '↓') : '↕';

                  return (
                    <th
                      key={column.key}
                      className={`px-3 py-2.5 text-xs font-medium uppercase tracking-wider ${
                        column.key === 'profit' || column.key === 'profitRate' ? 'text-right' : 'text-secondary'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => handleSort(column.key as SortKey)}
                        className={`inline-flex items-center gap-1 transition-colors ${
                          isActive ? 'text-cyan' : 'text-secondary hover:text-white'
                        }`}
                      >
                        <span>{column.label}</span>
                        <span className="text-[10px]">{indicator}</span>
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {sortedTrades.map((trade) => {
                const profitTone = trade.profit != null
                  ? trade.profit > 0 ? 'text-emerald-400' : trade.profit < 0 ? 'text-red-400' : 'text-secondary'
                  : 'text-muted';
                const profitRateTone = trade.profitRate != null
                  ? trade.profitRate > 0 ? 'text-emerald-400' : trade.profitRate < 0 ? 'text-red-400' : 'text-secondary'
                  : 'text-muted';

                return (
                  <tr key={trade.id} className="border-t border-white/5 transition-colors hover:bg-hover">
                    <td className="px-3 py-2 text-xs font-medium text-white">
                      <span className={trade.tradeType === 'buy' ? 'text-cyan' : 'text-amber-400'}>
                        {getTradeTypeLabel(trade.tradeType)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-secondary">{trade.tradeDate}</td>
                    <td className="px-3 py-2 text-xs font-mono text-white">{formatCurrency(trade.price)}</td>
                    <td className="px-3 py-2 text-xs font-mono text-secondary">{numberFormatter.format(trade.shares)}</td>
                    <td className="px-3 py-2 text-xs font-mono text-secondary">{formatCurrency(trade.commission)}</td>
                    <td className={`px-3 py-2 text-right text-xs font-mono ${profitTone}`}>{formatCurrency(trade.profit)}</td>
                    <td className={`px-3 py-2 text-right text-xs font-mono ${profitRateTone}`}>{formatPercent(trade.profitRate)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};
