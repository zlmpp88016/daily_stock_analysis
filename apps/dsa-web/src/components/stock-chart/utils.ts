const FALLBACK_MA_PERIODS = [5, 10, 30, 200];

export function normalizeMaPeriods(periods?: number[] | null): number[] {
  const source = Array.isArray(periods) ? periods : [];
  const normalized = source.filter((period) => Number.isInteger(period) && period > 0);

  return normalized.length > 0 ? [...new Set(normalized)] : [...FALLBACK_MA_PERIODS];
}

export function formatMaPeriodsInput(periods?: number[] | null): string {
  return normalizeMaPeriods(periods).join(', ');
}

export function parseMaPeriodsInput(value: string): number[] {
  const tokens = value
    .split(/[\s,，]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  if (tokens.length === 0) {
    throw new Error('请至少填写一条 MA 周期。');
  }

  const periods = tokens.map((item) => Number(item));
  if (periods.some((item) => !Number.isInteger(item) || item <= 0)) {
    throw new Error('MA 周期必须是正整数，多个值请用逗号分隔。');
  }

  return normalizeMaPeriods(periods);
}

export function tryParseMaPeriodsInput(value: string): number[] | undefined {
  try {
    return parseMaPeriodsInput(value);
  } catch {
    return undefined;
  }
}
