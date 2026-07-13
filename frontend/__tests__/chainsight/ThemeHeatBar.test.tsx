import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ThemeHeatBar from '@/components/chainsight/ThemeHeatBar';

vi.mock('@/services/chainsightService', () => ({ fetchThemeHeatBar: vi.fn() }));
import { fetchThemeHeatBar } from '@/services/chainsightService';

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const items = [
  { theme: 'Energy', status: 'computed', score: 58, band: 'warning', band_display: '가열', delta_1d: 0, days: 43, days_required: 26, eta_days: null, universe_stale: false },
  { theme: 'Financial Services', status: 'computed', score: 55, band: 'warning', band_display: '가열', delta_1d: -12, days: 44, days_required: 26, eta_days: null, universe_stale: false },
  { theme: 'Healthcare', status: 'accumulating', score: null, band: null, band_display: null, delta_1d: null, days: 25, days_required: 26, eta_days: null, universe_stale: false },
  { theme: 'Real Estate', status: 'accumulating', score: null, band: null, band_display: null, delta_1d: null, days: 5, days_required: 26, eta_days: 12, universe_stale: false },
];

describe('ThemeHeatBar', () => {
  beforeEach(() => vi.clearAllMocks());

  it('computed 버튼 + accumulating 진행바 분리 렌더(결정23=B)', async () => {
    (fetchThemeHeatBar as ReturnType<typeof vi.fn>).mockResolvedValue(items);
    wrap(<ThemeHeatBar />);
    expect(await screen.findByTestId('computed-Energy')).toHaveTextContent('58');
    expect(screen.getByTestId('computed-Financial Services')).toHaveTextContent('55');
    expect(screen.getByTestId('accumulating-Healthcare')).toHaveTextContent('25/26');
  });

  it('eta_days 있으면 D-n 라벨(조건부), 없으면 미표시', async () => {
    (fetchThemeHeatBar as ReturnType<typeof vi.fn>).mockResolvedValue(items);
    wrap(<ThemeHeatBar />);
    expect(await screen.findByTestId('accumulating-Real Estate')).toHaveTextContent('D-12');
    expect(screen.getByTestId('accumulating-Healthcare')).not.toHaveTextContent('D-');
  });

  it('클릭 시 onSelect 콜백', async () => {
    (fetchThemeHeatBar as ReturnType<typeof vi.fn>).mockResolvedValue(items);
    const onSelect = vi.fn();
    wrap(<ThemeHeatBar onSelect={onSelect} />);
    fireEvent.click(await screen.findByTestId('computed-Energy'));
    expect(onSelect).toHaveBeenCalledWith('Energy');
  });
});
