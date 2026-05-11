import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MetricCard from '@/components/validation/MetricCard';
import type { MetricData } from '@/types/validation';

// 차트/툴팁 자식 컴포넌트 mock
vi.mock('@/components/validation/MetricBarChart', () => ({
  default: () => <div data-testid="metric-bar-chart" />,
}));
vi.mock('@/components/validation/MetricInfoTooltip', () => ({
  default: () => <span data-testid="metric-info-tooltip" />,
}));

const normalMetric: MetricData = {
  metric_code: 'roe',
  display_name: '자기자본이익률',
  display_name_en: 'ROE',
  unit: 'ratio',
  higher_is_better: true,
  current: { value: 0.25, fiscal_year: 2025, value_status: 'normal' },
  benchmark: {
    basis: 'industry_size',
    confidence: 'high',
    median: 0.15,
    p25: 0.10,
    p75: 0.22,
    percentile_rank: 82,
    rank: 3,
    total: 15,
  },
  history: [
    { fiscal_year: 2023, company_value: 0.20, peer_median: 0.14, peer_p25: 0.09, peer_p75: 0.20 },
  ],
  trend: 'improving',
  interpretation: 'ROE가 업종 상위권에 위치합니다.',
  interpretation_source: 'rule',
};

describe('MetricCard', () => {
  it('정상 지표의 현재값, 벤치마크, 해석을 렌더링한다', () => {
    render(<MetricCard metric={normalMetric} />);

    expect(screen.getByText('자기자본이익률')).toBeInTheDocument();
    expect(screen.getByText('ROE')).toBeInTheDocument();
    // 현재값: 0.25 * 100 = 25.0%
    expect(screen.getByText('25.0%')).toBeInTheDocument();
    // 업종 중앙값: 0.15 * 100 = 15.0%
    expect(screen.getByText('15.0%')).toBeInTheDocument();
    // 순위
    expect(screen.getByText('3/15')).toBeInTheDocument();
    // 백분위
    expect(screen.getByText('82%')).toBeInTheDocument();
    // 해석
    expect(screen.getByText(/ROE가 업종 상위권/)).toBeInTheDocument();
    // 차트 렌더링
    expect(screen.getByTestId('metric-bar-chart')).toBeInTheDocument();
  });

  it('not_applicable 상태에서 해당 없음 메시지를 표시한다', () => {
    const metric: MetricData = {
      ...normalMetric,
      current: { value: null, fiscal_year: 2025, value_status: 'not_applicable' },
      benchmark: null,
      history: [],
      interpretation: '금융업은 해당 지표를 적용하지 않습니다.',
    };

    render(<MetricCard metric={metric} />);

    expect(screen.getByText(/해당 없음/)).toBeInTheDocument();
    expect(screen.getByText(/금융업은 해당 지표를 적용하지 않습니다/)).toBeInTheDocument();
  });

  it('missing 상태에서 데이터 누락 메시지를 표시한다', () => {
    const metric: MetricData = {
      ...normalMetric,
      current: { value: null, fiscal_year: 2025, value_status: 'missing' },
      benchmark: null,
      history: [],
    };

    render(<MetricCard metric={metric} />);

    expect(screen.getByText('데이터 누락')).toBeInTheDocument();
  });

  it('unstable 상태에서 경고 배너를 표시한다', () => {
    const metric: MetricData = {
      ...normalMetric,
      current: { value: 0.25, fiscal_year: 2025, value_status: 'unstable' },
    };

    render(<MetricCard metric={metric} />);

    expect(screen.getByText(/값 변동이 크므로 해석 주의/)).toBeInTheDocument();
  });
});
