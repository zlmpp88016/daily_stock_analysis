import type React from 'react';
import { useEffect, useState } from 'react';
import { Badge, Button } from '../common';

interface RuleBuilderProps {
  value: string[];
  onChange: (rules: string[]) => void;
  label: string;
}

type RuleOperator = 'cross_over' | 'cross_under' | '>' | '<';
type LogicalOperator = 'and' | 'or';
type OperandMode = 'indicator' | 'constant';

interface RuleRow {
  id: string;
  connector: LogicalOperator;
  left: string;
  operator: RuleOperator;
  rightMode: OperandMode;
  rightIndicator: string;
  rightConstant: string;
}

const INDICATOR_OPTIONS = [
  { value: 'close', label: '收盘价 close' },
  { value: 'ma_5', label: 'MA 5' },
  { value: 'ma_10', label: 'MA 10' },
  { value: 'ma_20', label: 'MA 20' },
  { value: 'ma_30', label: 'MA 30' },
  { value: 'ma_60', label: 'MA 60' },
  { value: 'macd_dif', label: 'MACD DIF' },
  { value: 'macd_dea', label: 'MACD DEA' },
  { value: 'macd_hist', label: 'MACD HIST' },
  { value: 'kdj_k', label: 'KDJ K' },
  { value: 'kdj_d', label: 'KDJ D' },
  { value: 'kdj_j', label: 'KDJ J' },
  { value: 'boll_upper', label: 'BOLL 上轨' },
  { value: 'boll_middle', label: 'BOLL 中轨' },
  { value: 'boll_lower', label: 'BOLL 下轨' },
];

const CONDITION_OPERATOR_OPTIONS = [
  { value: 'cross_over', label: 'cross_over' },
  { value: 'cross_under', label: 'cross_under' },
  { value: '>', label: '>' },
  { value: '<', label: '<' },
];

function createRow(overrides: Partial<RuleRow> = {}): RuleRow {
  return {
    id: `rule-${Math.random().toString(36).slice(2, 10)}`,
    connector: 'and',
    left: 'ma_5',
    operator: 'cross_over',
    rightMode: 'indicator',
    rightIndicator: 'ma_20',
    rightConstant: '',
    ...overrides,
  };
}

function isNumericLiteral(value: string): boolean {
  return /^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(value.trim());
}

function parseSingleExpression(expression: string): Omit<RuleRow, 'id'> | null {
  const trimmed = expression.trim().replace(/^\((.*)\)$/, '$1');
  if (!trimmed) {
    return null;
  }

  const crossoverMatch = trimmed.match(
    /^(cross_over|cross_under)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([A-Za-z_][A-Za-z0-9_]*|-?(?:\d+(?:\.\d*)?|\.\d+))\s*\)$/,
  );
  if (crossoverMatch) {
    const [, operator, left, right] = crossoverMatch;
    return {
      connector: 'and',
      left,
      operator: operator as RuleOperator,
      rightMode: isNumericLiteral(right) ? 'constant' : 'indicator',
      rightIndicator: isNumericLiteral(right) ? 'ma_20' : right,
      rightConstant: isNumericLiteral(right) ? right : '',
    };
  }

  const comparisonMatch = trimmed.match(
    /^([A-Za-z_][A-Za-z0-9_]*)\s*(>|<)\s*([A-Za-z_][A-Za-z0-9_]*|-?(?:\d+(?:\.\d*)?|\.\d+))$/,
  );
  if (comparisonMatch) {
    const [, left, operator, right] = comparisonMatch;
    return {
      connector: 'and',
      left,
      operator: operator as RuleOperator,
      rightMode: isNumericLiteral(right) ? 'constant' : 'indicator',
      rightIndicator: isNumericLiteral(right) ? 'ma_20' : right,
      rightConstant: isNumericLiteral(right) ? right : '',
    };
  }

  return null;
}

function parseRules(value: string[]): RuleRow[] {
  const rows: RuleRow[] = [];

  value.forEach((rule, ruleIndex) => {
    const fragments = rule
      .trim()
      .split(/\s+(and|or)\s+/)
      .map((fragment) => fragment.trim())
      .filter(Boolean);

    let pendingConnector: LogicalOperator = ruleIndex === 0 ? 'and' : 'and';

    fragments.forEach((fragment, fragmentIndex) => {
      if (fragment === 'and' || fragment === 'or') {
        pendingConnector = fragment;
        return;
      }

      const parsed = parseSingleExpression(fragment);
      if (!parsed) {
        return;
      }

      rows.push(
        createRow({
          ...parsed,
          connector: rows.length === 0 ? 'and' : fragmentIndex === 0 && ruleIndex > 0 ? 'and' : pendingConnector,
        }),
      );
      pendingConnector = 'and';
    });
  });

  return rows.length > 0 ? rows : [createRow()];
}

function stringifyRow(row: RuleRow): string | null {
  const left = row.left.trim();
  const right = row.rightMode === 'indicator' ? row.rightIndicator.trim() : row.rightConstant.trim();

  if (!left || !right) {
    return null;
  }

  if (row.operator === 'cross_over' || row.operator === 'cross_under') {
    return `${row.operator}(${left}, ${right})`;
  }

  return `${left} ${row.operator} ${right}`;
}

function rowsToRules(rows: RuleRow[]): string[] {
  const expressions = rows.map((row) => stringifyRow(row));
  const groups: string[] = [];
  let currentGroup = '';

  expressions.forEach((expression, index) => {
    if (!expression) {
      return;
    }

    if (index === 0) {
      currentGroup = expression;
      return;
    }

    if (rows[index].connector === 'or') {
      currentGroup = currentGroup ? `${currentGroup} or ${expression}` : expression;
      return;
    }

    if (currentGroup) {
      groups.push(currentGroup);
    }
    currentGroup = expression;
  });

  if (currentGroup) {
    groups.push(currentGroup);
  }

  return groups;
}

function selectClasses(): string {
  return [
    'w-full appearance-none rounded-lg border border-cyan-500/20 bg-slate-800/50 px-3 py-2.5 text-sm text-gray-200',
    'transition-all duration-200 hover:border-cyan-500/30 focus:border-cyan-500/40 focus:outline-none',
    'focus:ring-2 focus:ring-cyan-500/40 disabled:cursor-not-allowed disabled:opacity-50',
  ].join(' ');
}

function inputClasses(): string {
  return [
    'w-full rounded-lg border border-cyan-500/20 bg-slate-800/50 px-3 py-2.5 text-sm text-gray-200',
    'transition-all duration-200 hover:border-cyan-500/30 focus:border-cyan-500/40 focus:outline-none',
    'focus:ring-2 focus:ring-cyan-500/40 disabled:cursor-not-allowed disabled:opacity-50',
  ].join(' ');
}

export const RuleBuilder: React.FC<RuleBuilderProps> = ({ value, onChange, label }) => {
  const [rows, setRows] = useState<RuleRow[]>(() => parseRules(value));
  const previewRules = rowsToRules(rows);

  useEffect(() => {
    setRows(parseRules(value));
  }, [value]);

  const applyRows = (nextRows: RuleRow[]) => {
    setRows(nextRows);
    onChange(rowsToRules(nextRows));
  };

  const updateRow = (rowId: string, updates: Partial<RuleRow>) => {
    applyRows(rows.map((row) => (row.id === rowId ? { ...row, ...updates } : row)));
  };

  const addRow = () => {
    applyRows([...rows, createRow({ connector: 'and' })]);
  };

  const removeRow = (rowId: string) => {
    const nextRows = rows.filter((row) => row.id !== rowId);
    applyRows(nextRows.length > 0 ? nextRows : [createRow()]);
  };

  return (
    <div className="rounded-xl border border-white/5 bg-black/10 p-4">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-white">{label}</h3>
            <p className="mt-1 text-xs text-muted">
              支持交叉、比较和多条件 and/or 组合，自动生成后端可识别的表达式。
            </p>
          </div>
          <Badge variant="info">结构化编辑</Badge>
        </div>

        <div className="rounded-lg border border-white/8 bg-elevated/40 px-3 py-2 text-xs text-secondary">
          当前表达式：
          <span className="ml-2 break-all font-mono text-white">
            {previewRules.length > 0 ? previewRules.join(' | ') : '待生成'}
          </span>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {rows.map((row, index) => (
          <div key={row.id} className="rounded-xl border border-white/8 bg-slate-900/60 p-3.5">
            {index > 0 ? (
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="text-[11px] uppercase tracking-[0.18em] text-muted">逻辑连接</span>
                <select
                  value={row.connector}
                  onChange={(event) => updateRow(row.id, { connector: event.target.value as LogicalOperator })}
                  className="rounded-md border border-white/10 bg-slate-800/80 px-2 py-1 text-xs text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
                >
                  <option value="and">and</option>
                  <option value="or">or</option>
                </select>
              </div>
            ) : null}

            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <span className="mb-1.5 block text-xs font-medium text-secondary">指标 1</span>
                <select
                  value={row.left}
                  onChange={(event) => updateRow(row.id, { left: event.target.value })}
                  className={selectClasses()}
                >
                  {INDICATOR_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value} className="bg-slate-800">
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <span className="mb-1.5 block text-xs font-medium text-secondary">操作符</span>
                <select
                  value={row.operator}
                  onChange={(event) => updateRow(row.id, { operator: event.target.value as RuleOperator })}
                  className={selectClasses()}
                >
                  {CONDITION_OPERATOR_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value} className="bg-slate-800">
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-medium text-secondary">指标 2 / 常量</span>
                  <div className="inline-flex rounded-md border border-white/10 bg-slate-800/80 p-1">
                    <button
                      type="button"
                      onClick={() => updateRow(row.id, { rightMode: 'indicator' })}
                      className={`rounded px-2 py-1 text-xs transition-colors ${
                        row.rightMode === 'indicator' ? 'bg-cyan/20 text-cyan' : 'text-muted hover:text-white'
                      }`}
                    >
                      指标
                    </button>
                    <button
                      type="button"
                      onClick={() => updateRow(row.id, { rightMode: 'constant' })}
                      className={`rounded px-2 py-1 text-xs transition-colors ${
                        row.rightMode === 'constant' ? 'bg-cyan/20 text-cyan' : 'text-muted hover:text-white'
                      }`}
                    >
                      常量
                    </button>
                  </div>
                </div>

                {row.rightMode === 'indicator' ? (
                  <select
                    value={row.rightIndicator}
                    onChange={(event) => updateRow(row.id, { rightIndicator: event.target.value })}
                    className={selectClasses()}
                  >
                    {INDICATOR_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value} className="bg-slate-800">
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    value={row.rightConstant}
                    onChange={(event) => updateRow(row.id, { rightConstant: event.target.value })}
                    placeholder="例如 0 或 100"
                    className={inputClasses()}
                  />
                )}
              </div>

              <div className="flex items-end">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => removeRow(row.id)}
                  className="w-full md:w-auto"
                >
                  删除条件
                </Button>
              </div>
            </div>

            <div className="mt-3 rounded-lg border border-emerald-500/10 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-300">
              {stringifyRow(row) ?? '请补全当前条件'}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-3 border-t border-white/5 pt-4 sm:flex-row sm:items-center sm:justify-between">
        <Button type="button" variant="secondary" onClick={addRow} className="sm:w-auto">
          添加条件
        </Button>
        <p className="text-left text-xs text-muted sm:text-right">
          当前输出：
          <span className="ml-2 break-all font-mono text-secondary">
            {previewRules.length > 0 ? JSON.stringify(previewRules) : '[]'}
          </span>
        </p>
      </div>
    </div>
  );
};
