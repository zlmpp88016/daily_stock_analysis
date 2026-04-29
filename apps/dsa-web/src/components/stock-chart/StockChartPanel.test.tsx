import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StockChartPanel } from './StockChartPanel';

const { mockGetKlineData, mockKLineChart } = vi.hoisted(() => ({
  mockGetKlineData: vi.fn(),
  mockKLineChart: vi.fn(),
}));

vi.mock('../../api/stockChart', () => ({
  stockChartApi: {
    getKlineData: mockGetKlineData,
  },
}));

vi.mock('./KLineChart', () => ({
  KLineChart: (props: { indicators: string[]; maPeriods?: number[] }) => {
    mockKLineChart(props);
    return (
      <div
        data-testid="kline-chart"
        data-indicators={props.indicators.join(',')}
        data-ma-periods={(props.maPeriods ?? []).join(',')}
      />
    );
  },
}));

describe('StockChartPanel', () => {
  beforeEach(() => {
    mockGetKlineData.mockReset();
    mockKLineChart.mockReset();
    mockGetKlineData.mockResolvedValue({
      code: '600519',
      name: '贵州茅台',
      period: 'daily',
      bars: [
        { date: '2024-01-02', open: 1, high: 2, low: 1, close: 2, volume: 100 },
        { date: '2024-01-03', open: 2, high: 3, low: 2, close: 3, volume: 120 },
      ],
    });
  });

  it('loads default code and passes configured ma periods to the chart', async () => {
    render(<StockChartPanel defaultCode="600519" defaultMaPeriods={[5, 20, 30]} />);

    await waitFor(() => {
      expect(mockGetKlineData).toHaveBeenCalledWith({ code: '600519', period: 'daily' });
    });

    expect(await screen.findByText('贵州茅台')).toBeInTheDocument();
    expect(screen.getByDisplayValue('5, 20, 30')).toBeInTheDocument();
    expect(screen.getByTestId('kline-chart')).toHaveAttribute('data-ma-periods', '5,20,30');
  });

  it('switches period and updates indicator toggles', async () => {
    render(<StockChartPanel defaultCode="600519" />);

    await waitFor(() => {
      expect(mockGetKlineData).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole('tab', { name: '周K' }));

    await waitFor(() => {
      expect(mockGetKlineData).toHaveBeenLastCalledWith({ code: '600519', period: 'weekly' });
    });

    fireEvent.click(screen.getByRole('button', { name: 'MACD' }));

    await waitFor(() => {
      expect(screen.getByTestId('kline-chart')).toHaveAttribute('data-indicators', expect.stringContaining('macd'));
    });
  });

  it('shows validation feedback for invalid ma input and keeps the previous chart config', async () => {
    render(<StockChartPanel defaultCode="600519" defaultMaPeriods={[5, 10, 30, 200]} />);

    await waitFor(() => {
      expect(mockGetKlineData).toHaveBeenCalled();
    });

    fireEvent.change(screen.getByPlaceholderText('例如 5, 10, 30, 200'), {
      target: { value: '5, xx' },
    });

    expect(screen.getByText('MA 周期必须是正整数，多个值请用逗号分隔。')).toBeInTheDocument();
    expect(screen.getByTestId('kline-chart')).toHaveAttribute('data-ma-periods', '5,10,30,200');
  });
});
