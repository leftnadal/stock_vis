import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SignalSummaryCard from '@/components/validation/SignalSummaryCard';
import type { CategorySignal } from '@/types/validation';

const signals: CategorySignal[] = [
  { category: 'profitability', display_name: '수익성', signal: 'green', description: '', metric_count: 3, signal_reason: '' },
  { category: 'growth', display_name: '성장성', signal: 'yellow', description: '', metric_count: 2, signal_reason: '' },
  { category: 'stability', display_name: '안정성', signal: 'red', description: '', metric_count: 2, signal_reason: '' },
  { category: 'valuation', display_name: '밸류에이션', signal: 'gray', description: '', metric_count: 1, signal_reason: '데이터 부족으로 평가 불가' },
];

describe('SignalSummaryCard', () => {
  it('회사명과 한줄 요약을 렌더링한다', () => {
    render(
      <SignalSummaryCard
        companyName="Apple Inc."
        categorySignals={signals}
        summaryText="전반적으로 양호한 재무 체질"
      />,
    );

    expect(screen.getByText('Apple Inc. 재무 체질 진단')).toBeInTheDocument();
    expect(screen.getByText('전반적으로 양호한 재무 체질')).toBeInTheDocument();
  });

  it('각 카테고리 신호등을 렌더링한다', () => {
    render(
      <SignalSummaryCard
        companyName="Apple Inc."
        categorySignals={signals}
        summaryText="요약"
      />,
    );

    expect(screen.getByText('수익성')).toBeInTheDocument();
    expect(screen.getByText('성장성')).toBeInTheDocument();
    expect(screen.getByText('안정성')).toBeInTheDocument();
    expect(screen.getByText('밸류에이션')).toBeInTheDocument();
  });

  it('gray 신호등 hover 시 사유 툴팁을 표시한다', () => {
    render(
      <SignalSummaryCard
        companyName="Apple Inc."
        categorySignals={signals}
        summaryText="요약"
      />,
    );

    // gray 카테고리(밸류에이션) 컨테이너에 hover
    const grayContainer = screen.getByText('밸류에이션').closest('div')!;
    fireEvent.mouseEnter(grayContainer);

    expect(screen.getByText('데이터 부족으로 평가 불가')).toBeInTheDocument();

    fireEvent.mouseLeave(grayContainer);
    expect(screen.queryByText('데이터 부족으로 평가 불가')).not.toBeInTheDocument();
  });

  it('gray가 아닌 신호등 hover 시에는 툴팁을 표시하지 않는다', () => {
    render(
      <SignalSummaryCard
        companyName="Apple Inc."
        categorySignals={signals}
        summaryText="요약"
      />,
    );

    // green 카테고리(수익성) 컨테이너에 hover
    const greenContainer = screen.getByText('수익성').closest('div')!;
    fireEvent.mouseEnter(greenContainer);

    // gray 사유 텍스트는 표시되지 않아야 함
    expect(screen.queryByText('데이터 부족으로 평가 불가')).not.toBeInTheDocument();
  });
});
