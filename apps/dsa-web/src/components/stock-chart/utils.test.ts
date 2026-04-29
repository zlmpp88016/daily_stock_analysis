import { describe, expect, it } from 'vitest';
import { formatMaPeriodsInput, normalizeMaPeriods, parseMaPeriodsInput, tryParseMaPeriodsInput } from './utils';

describe('stock-chart utils', () => {
  it('normalizes and deduplicates ma periods', () => {
    expect(normalizeMaPeriods([5, 10, 10, -1, 30])).toEqual([5, 10, 30]);
  });

  it('falls back to default ma periods when empty', () => {
    expect(normalizeMaPeriods([])).toEqual([5, 10, 30, 200]);
    expect(formatMaPeriodsInput(undefined)).toBe('5, 10, 30, 200');
  });

  it('parses ma periods from mixed separators', () => {
    expect(parseMaPeriodsInput('5, 10，22  200')).toEqual([5, 10, 22, 200]);
  });

  it('returns undefined for invalid ma input in tolerant parser', () => {
    expect(tryParseMaPeriodsInput('5, bad')).toBeUndefined();
  });
});
