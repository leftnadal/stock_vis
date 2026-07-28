/**
 * GraphStatePanel 상태 분기 렌더 (⑳-E S3/S4).
 *
 * 빈 캔버스 조용한 수렴 금지: 이웃 없음(a) vs 로드 실패(b) vs 섹터 불가(S4)를 구분 렌더.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import GraphStatePanel from '@/components/chainsight/GraphStatePanel';

describe('GraphStatePanel (⑳-E)', () => {
  it('empty-neighbors: 이웃 없음 안내 — 오류/재시도 아님', () => {
    render(<GraphStatePanel variant="empty-neighbors" symbol="NVDA" />);
    expect(screen.getByTestId('graph-state-empty-neighbors')).toBeInTheDocument();
    expect(screen.getByText(/확인된 관계가 없어요/)).toBeInTheDocument();
    expect(screen.getByText(/NVDA/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '다시 시도' })).not.toBeInTheDocument();
  });

  it('load-error: 오류 명시 + 재시도 버튼 동작', () => {
    const onRetry = vi.fn();
    render(<GraphStatePanel variant="load-error" symbol="NVDA" onRetry={onRetry} />);
    expect(screen.getByTestId('graph-state-load-error')).toBeInTheDocument();
    expect(screen.getByText(/불러오지 못했어요/)).toBeInTheDocument();
    const btn = screen.getByRole('button', { name: '다시 시도' });
    fireEvent.click(btn);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('sector-unavailable: 섹터 관계망 불가 명시 + 재시도', () => {
    const onRetry = vi.fn();
    render(<GraphStatePanel variant="sector-unavailable" onRetry={onRetry} />);
    expect(screen.getByTestId('graph-state-sector-unavailable')).toBeInTheDocument();
    expect(screen.getByText(/섹터 관계망은 현재 이용할 수 없어요/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('세 상태는 서로 다른 testId 로 구분된다 (조용한 수렴 금지)', () => {
    const { rerender } = render(<GraphStatePanel variant="empty-neighbors" symbol="X" />);
    expect(screen.getByTestId('graph-state-empty-neighbors')).toBeInTheDocument();
    rerender(<GraphStatePanel variant="load-error" symbol="X" onRetry={() => {}} />);
    expect(screen.getByTestId('graph-state-load-error')).toBeInTheDocument();
    rerender(<GraphStatePanel variant="sector-unavailable" onRetry={() => {}} />);
    expect(screen.getByTestId('graph-state-sector-unavailable')).toBeInTheDocument();
  });

  it('UX 용어 규약: "테마" 문구를 쓰지 않는다', () => {
    const { container, rerender } = render(<GraphStatePanel variant="empty-neighbors" symbol="X" />);
    expect(container.textContent).not.toContain('테마');
    rerender(<GraphStatePanel variant="load-error" symbol="X" onRetry={() => {}} />);
    expect(container.textContent).not.toContain('테마');
    rerender(<GraphStatePanel variant="sector-unavailable" onRetry={() => {}} />);
    expect(container.textContent).not.toContain('테마');
  });
});
