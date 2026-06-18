import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MetricInfoPopover from '@/components/chainsight/MetricInfoPopover';
import { METRIC_INFO, type MetricKey } from '@/constants/eventThemes';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  HelpCircle: () => <span data-testid="help-icon" />,
}));

describe('MetricInfoPopover', () => {
  it('초기 상태: 설명/예시가 표시되지 않는다', () => {
    render(<MetricInfoPopover metricKey="trend_quality" />);
    expect(screen.queryByText(METRIC_INFO.trend_quality.description)).not.toBeInTheDocument();
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('버튼 클릭 시 description·example·range가 렌더된다', () => {
    render(<MetricInfoPopover metricKey="trend_quality" />);
    fireEvent.click(screen.getByRole('button', { name: '추세강도 설명' }));
    expect(screen.getByText(METRIC_INFO.trend_quality.description)).toBeInTheDocument();
    expect(screen.getByText(METRIC_INFO.trend_quality.example)).toBeInTheDocument();
    expect(screen.getByText(METRIC_INFO.trend_quality.range)).toBeInTheDocument();
  });

  it('바깥 클릭 시 닫힌다', () => {
    render(
      <div>
        <MetricInfoPopover metricKey="theme_beta" />
        <button type="button">바깥</button>
      </div>,
    );
    fireEvent.click(screen.getByRole('button', { name: '그룹 민감도 설명' }));
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    // 바깥 영역 mousedown → 닫힘
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('metricKey별 올바른 label을 버튼 aria-label에 노출한다', () => {
    const { rerender } = render(<MetricInfoPopover metricKey="capture_spread" />);
    expect(screen.getByRole('button', { name: '주도우위 설명' })).toBeInTheDocument();
    rerender(<MetricInfoPopover metricKey="theme_alpha" />);
    expect(screen.getByRole('button', { name: '그룹 초과수익 설명' })).toBeInTheDocument();
  });
});

describe('METRIC_INFO 단일 출처', () => {
  const EXPECTED_KEYS: MetricKey[] = [
    'trend_quality',
    'theme_beta',
    'capture_spread',
    'theme_alpha',
    'up_capture',
    'down_capture',
  ];

  it('6개 지표 키가 전부 정의돼 있다 (누락 방지)', () => {
    expect(Object.keys(METRIC_INFO).sort()).toEqual([...EXPECTED_KEYS].sort());
  });

  it('각 항목이 필수 필드를 모두 갖는다', () => {
    for (const key of EXPECTED_KEYS) {
      const info = METRIC_INFO[key];
      expect(info.field).toBe(key);
      expect(info.label).toBeTruthy();
      expect(['primary', 'supplementary']).toContain(info.tier);
      expect(info.description).toBeTruthy();
      expect(info.example).toBeTruthy();
      expect(info.range).toBeTruthy();
    }
  });

  it('주신호 3·보조 3으로 분류된다', () => {
    const tiers = Object.values(METRIC_INFO).map((m) => m.tier);
    expect(tiers.filter((t) => t === 'primary')).toHaveLength(3);
    expect(tiers.filter((t) => t === 'supplementary')).toHaveLength(3);
  });
});
