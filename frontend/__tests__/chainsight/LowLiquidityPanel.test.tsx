import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import LowLiquidityPanel from '@/components/chainsight/LowLiquidityPanel';
import type { EventRankingItem } from '@/types/chainsight';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  ChevronDown: () => <span data-testid="chevron-down" />,
  ChevronUp: () => <span data-testid="chevron-up" />,
  AlertTriangle: () => <span data-testid="alert-triangle" />,
}));

const lowLiquidityItem: EventRankingItem = {
  symbol: 'SMCI',
  name: 'Super Micro Computer',
  score: 41.0,
  raw_return: 0.025,
  volume_z: 0.82,
  volatility_pct: 0.718,
  is_low_liquidity: true,
};

const negativeReturnItem: EventRankingItem = {
  ...lowLiquidityItem,
  raw_return: -0.031,
};

describe('LowLiquidityPanel', () => {
  it('초기 상태: 패널이 닫혀 있다 (상세 내용 미표시)', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    expect(screen.queryByText('점수 분해')).not.toBeInTheDocument();
    expect(screen.queryByText(/거래량이 얕아/)).not.toBeInTheDocument();
  });

  it('토글 버튼 클릭 시 패널이 열린다', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    const toggleBtn = screen.getByRole('button', { name: /저유동성 상세/ });
    fireEvent.click(toggleBtn);
    expect(screen.getByText('점수 분해')).toBeInTheDocument();
  });

  it('열린 상태에서 다시 클릭하면 닫힌다', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    const toggleBtn = screen.getByRole('button', { name: /저유동성 상세/ });
    fireEvent.click(toggleBtn);
    expect(screen.getByText('점수 분해')).toBeInTheDocument();
    fireEvent.click(toggleBtn);
    expect(screen.queryByText('점수 분해')).not.toBeInTheDocument();
  });

  it('패널 열림 시 volume_z 값을 소수점 2자리로 표시한다', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('0.82')).toBeInTheDocument();
  });

  it('패널 열림 시 volatility_pct를 퍼센트로 변환해 표시한다', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('71.8%')).toBeInTheDocument();
  });

  it('패널 열림 시 raw_return 양수를 +로 표시한다', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('+2.50%')).toBeInTheDocument();
  });

  it('패널 열림 시 raw_return 음수를 -로 표시한다', () => {
    render(<LowLiquidityPanel item={negativeReturnItem} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('-3.10%')).toBeInTheDocument();
  });

  it('경고 메시지를 표시한다', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText(/거래량이 얕아 체결·청산이 불리할 수 있습니다/)).toBeInTheDocument();
    expect(screen.getByText(/진입 전 호가 확인/)).toBeInTheDocument();
  });

  it('ADV(평균 거래대금) 텍스트가 없다 (데이터 없음)', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText(/ADV/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/평균 거래대금/)).not.toBeInTheDocument();
  });

  it('스프레드 텍스트가 없다 (데이터 없음)', () => {
    render(<LowLiquidityPanel item={lowLiquidityItem} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText(/스프레드/)).not.toBeInTheDocument();
    expect(screen.queryByText(/spread/i)).not.toBeInTheDocument();
  });
});
