import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ThemeHeatCard from '@/components/chainsight/ThemeHeatCard';

vi.mock('@/services/chainsightService', () => ({ fetchThemeHeatCard: vi.fn() }));
vi.mock('lucide-react', () => ({ Info: () => <span data-testid="icon-info" /> }));

import { fetchThemeHeatCard } from '@/services/chainsightService';

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const baseCard = {
  theme: 'Financial Services', as_of: '2026-07-12', status: 'computed', score: 55,
  band: 'warning', band_display: '가열', delta_1d: -12, z_mode: 'time_series',
  confidence: { present: 6, total: 8, missing: ['C4', 'C8'], renorm_divisor: 0.8 },
  components: [
    { id: 'C1', label_surface: '몸값 부담', label_technical: '밸류에이션', z: 0.14, w: 0.18, s: 0.53, z_mode: 'time_series', status: 'computed' },
    { id: 'C8', label_surface: '실적 안 따라옴', label_technical: '추정치 괴리', z: null, w: 0.08, s: null, z_mode: null, status: 'coldstart' },
  ],
  quadrant: { heat: 55, dss: null, dss_status: 'coldstart', dss_eta: 'Cycle 2 (DSS 미가동)' },
  history: { values: [67, 55], capacity: 60, filled: 2 },
};

describe('ThemeHeatCard', () => {
  beforeEach(() => vi.clearAllMocks());

  it('전환일: driver 보류 렌더 + 온도·delta는 노출(결정29)', async () => {
    (fetchThemeHeatCard as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...baseCard,
      driver: { held: true, reason: 'methodology_revision', marker: '2026-07-12', note: '계산 방식 개선일' },
    });
    wrap(<ThemeHeatCard theme="Financial Services" />);
    expect(await screen.findByTestId('heat-score')).toHaveTextContent('55');
    expect(screen.getByTestId('heat-delta')).toHaveTextContent('-12');
    expect(screen.getByTestId('driver-held')).toHaveTextContent('산출 보류');
    expect(screen.queryByTestId('driver-active')).toBeNull();
  });

  it('정상일: driver 방향+기여율 렌더(결정27=B)', async () => {
    (fetchThemeHeatCard as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...baseCard,
      driver: { held: false, component: 'C3', label_surface: '이야기 밀도', z: 0.9, contribution_pct: 86.1, basis: 'delta', direction: 'down' },
    });
    wrap(<ThemeHeatCard theme="Financial Services" />);
    const chip = await screen.findByTestId('driver-active');
    expect(chip).toHaveTextContent('냉각');
    expect(chip).toHaveTextContent('이야기 밀도');
    expect(chip).toHaveTextContent('86%');
  });

  it('전환일: delta 원값 옆 "개정일 재산출" 중립 마커(결정31=C)', async () => {
    (fetchThemeHeatCard as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...baseCard,
      driver: { held: true, reason: 'methodology_revision', marker: '2026-07-12' },
    });
    wrap(<ThemeHeatCard theme="Financial Services" />);
    expect(await screen.findByTestId('heat-delta')).toHaveTextContent('-12'); // 원값 유지
    expect(screen.getByTestId('revision-marker')).toHaveTextContent('개정일 재산출');
  });

  it('정상일: 개정일 마커 부재', async () => {
    (fetchThemeHeatCard as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...baseCard,
      driver: { held: false, component: 'C3', label_surface: '이야기 밀도', contribution_pct: 86.1, basis: 'delta', direction: 'down' },
    });
    wrap(<ThemeHeatCard theme="Financial Services" />);
    await screen.findByTestId('heat-score');
    expect(screen.queryByTestId('revision-marker')).toBeNull();
  });

  it('펼치면 의미 레이어에 z_mode 근거 문구(3년 자기 이력 대비)', async () => {
    (fetchThemeHeatCard as ReturnType<typeof vi.fn>).mockResolvedValue({ ...baseCard, driver: { held: true } });
    wrap(<ThemeHeatCard theme="Financial Services" />);
    fireEvent.click(await screen.findByTestId('expand-toggle'));
    const ml = screen.getByTestId('meaning-layer');
    expect(ml).toHaveTextContent('3년 자기 이력 대비'); // C1 time_series
    expect(ml).toHaveTextContent('수집 대기');           // C8 coldstart
  });
});
