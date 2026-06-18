import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import LowLiquidityPanel from '@/components/chainsight/LowLiquidityPanel';
import type { EventRankingItem } from '@/types/chainsight';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  AlertTriangle: () => <span data-testid="alert-triangle" />,
}));

const baseItem: Partial<EventRankingItem> = {
  symbol: 'SMCI',
  name: 'Super Micro Computer',
  score: 41.0,
  raw_return: 0.025,
  volume_z: 0.82,
  volatility_pct: 0.718,
  trend_quality: null,
  theme_alpha: null,
  theme_beta: null,
  up_capture: null,
  down_capture: null,
  capture_spread: null,
};

const lowLiquidityItem: EventRankingItem = {
  ...baseItem,
  is_low_liquidity: true,
  is_fallback: false,
} as EventRankingItem;

const fallbackOnlyItem: EventRankingItem = {
  ...baseItem,
  is_low_liquidity: false,
  is_fallback: true,
} as EventRankingItem;

const bothItem: EventRankingItem = {
  ...baseItem,
  is_low_liquidity: true,
  is_fallback: true,
} as EventRankingItem;

const neitherItem: EventRankingItem = {
  ...baseItem,
  is_low_liquidity: false,
  is_fallback: false,
} as EventRankingItem;

describe('LowLiquidityPanel', () => {
  // ── 상시 노출 (토글 없음) ──────────────────────────────────────────────

  it('토글 버튼이 없다 (상시 노출 구조)', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('저유동성 경고가 초기 렌더부터 바로 노출된다', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    expect(screen.getByText(/거래량이 얕아 체결·청산이 불리할 수 있습니다/)).toBeInTheDocument();
    expect(screen.getByText(/진입 전 호가 확인/)).toBeInTheDocument();
  });

  // ── 점수분해 제거 확인 ────────────────────────────────────────────────

  it('점수 분해 영역이 없다 (Slice 1로 이동됨)', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    expect(screen.queryByText('점수 분해')).not.toBeInTheDocument();
  });

  it('volume_z 수치 직접 표시가 없다 (펼침 영역으로 이동됨)', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    // 점수분해가 없으므로 "0.82" 같은 volume_z 숫자가 이 컴포넌트에서 렌더되지 않음
    expect(screen.queryByText('0.82')).not.toBeInTheDocument();
  });

  it('volatility_pct 수치 직접 표시가 없다 (펼침 영역으로 이동됨)', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    expect(screen.queryByText('71.8%')).not.toBeInTheDocument();
  });

  // ── is_fallback 경고 (R4) ─────────────────────────────────────────────

  it('is_fallback=true이면 "보정된 값" 경고가 노출된다', () => {
    render(<LowLiquidityPanel item={fallbackOnlyItem} />);
    expect(screen.getByText(/데이터가 부족해 보정된 값이에요/)).toBeInTheDocument();
  });

  it('is_fallback=false이면 "보정된 값" 경고가 없다', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    expect(screen.queryByText(/보정된 값/)).not.toBeInTheDocument();
  });

  it('is_low_liquidity=false, is_fallback=false이면 경고가 없다', () => {
    render(<LowLiquidityPanel item={neitherItem} />);
    expect(screen.queryByText(/거래량이 얕아/)).not.toBeInTheDocument();
    expect(screen.queryByText(/보정된 값/)).not.toBeInTheDocument();
  });

  // ── 두 경고 공존 ──────────────────────────────────────────────────────

  it('is_low_liquidity=true AND is_fallback=true이면 두 경고 모두 한 영역에 표시된다', () => {
    render(<LowLiquidityPanel item={bothItem} />);
    expect(screen.getByText(/거래량이 얕아 체결·청산이 불리할 수 있습니다/)).toBeInTheDocument();
    expect(screen.getByText(/데이터가 부족해 보정된 값이에요/)).toBeInTheDocument();
    // 두 AlertTriangle 아이콘이 렌더
    expect(screen.getAllByTestId('alert-triangle')).toHaveLength(2);
  });

  // ── 이전 잔재 부재 확인 ──────────────────────────────────────────────

  it('ADV(평균 거래대금) 텍스트가 없다 (데이터 없음)', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    expect(screen.queryByText(/ADV/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/평균 거래대금/)).not.toBeInTheDocument();
  });

  it('스프레드 텍스트가 없다 (데이터 없음)', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    expect(screen.queryByText(/스프레드/)).not.toBeInTheDocument();
    expect(screen.queryByText(/spread/i)).not.toBeInTheDocument();
  });
});
