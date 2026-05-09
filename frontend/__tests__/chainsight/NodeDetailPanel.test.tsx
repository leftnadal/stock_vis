import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import NodeDetailPanel from '@/components/chainsight/NodeDetailPanel';

// next/link mock
vi.mock('next/link', () => ({
  default: ({ children, href, ...rest }: { children: React.ReactNode; href: string; [k: string]: unknown }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

const sampleNode = {
  ticker: 'MSFT',
  name: 'Microsoft Corp.',
  sector: 'Technology',
  industry: 'Software',
  growth_stage: 'Mature',
  capital_dna: 'Cash Cow',
};

describe('NodeDetailPanel', () => {
  it('node가 null이면 안내 문구를 표시한다', () => {
    render(
      <NodeDetailPanel
        node={null}
        centerSymbol="AAPL"
        onExploreHere={vi.fn()}
        onStartTrace={vi.fn()}
      />,
    );

    expect(screen.getByText(/노드를 클릭하면 상세 정보가 표시됩니다/)).toBeInTheDocument();
  });

  it('노드 상세 정보(ticker, name, sector, industry)를 렌더링한다', () => {
    render(
      <NodeDetailPanel
        node={sampleNode}
        centerSymbol="AAPL"
        relationLabel="경쟁"
        onExploreHere={vi.fn()}
        onStartTrace={vi.fn()}
      />,
    );

    expect(screen.getByText('MSFT')).toBeInTheDocument();
    expect(screen.getByText('Microsoft Corp.')).toBeInTheDocument();
    expect(screen.getByText('Technology')).toBeInTheDocument();
    expect(screen.getByText('Software')).toBeInTheDocument();
    expect(screen.getByText('Mature')).toBeInTheDocument();
    expect(screen.getByText('Cash Cow')).toBeInTheDocument();
    expect(screen.getByText('경쟁')).toBeInTheDocument();
  });

  it('center 노드일 때 CTA 버튼을 숨긴다', () => {
    render(
      <NodeDetailPanel
        node={{ ...sampleNode, ticker: 'AAPL' }}
        centerSymbol="AAPL"
        onExploreHere={vi.fn()}
        onStartTrace={vi.fn()}
      />,
    );

    expect(screen.queryByText('가설 생성')).not.toBeInTheDocument();
    expect(screen.queryByText('Validation 보기')).not.toBeInTheDocument();
    expect(screen.queryByText(/여기서 탐색 시작/)).not.toBeInTheDocument();
  });

  it('비-center 노드에서 CTA 버튼 클릭이 콜백을 호출한다', () => {
    const onExploreHere = vi.fn();
    const onStartTrace = vi.fn();

    render(
      <NodeDetailPanel
        node={sampleNode}
        centerSymbol="AAPL"
        onExploreHere={onExploreHere}
        onStartTrace={onStartTrace}
      />,
    );

    // CTA 버튼 존재
    expect(screen.getByText('가설 생성')).toBeInTheDocument();
    expect(screen.getByText('Validation 보기')).toBeInTheDocument();

    fireEvent.click(screen.getByText('여기서 탐색 시작'));
    expect(onExploreHere).toHaveBeenCalledWith('MSFT');

    fireEvent.click(screen.getByText(/경로 찾기/));
    expect(onStartTrace).toHaveBeenCalledWith('MSFT');
  });

  it('센터 노드일 때는 relationLabel을 표시하지 않는다', () => {
    render(
      <NodeDetailPanel
        node={{ ...sampleNode, ticker: 'AAPL' }}
        centerSymbol="AAPL"
        relationLabel="경쟁"
        onExploreHere={vi.fn()}
        onStartTrace={vi.fn()}
      />,
    );

    expect(screen.queryByText('경쟁')).not.toBeInTheDocument();
  });

  it('industry/growth_stage/capital_dna 등 옵션 필드가 누락돼도 렌더링된다', () => {
    const minimalNode = {
      ticker: 'XYZ',
      name: 'Unknown Co',
    };

    render(
      <NodeDetailPanel
        node={minimalNode}
        centerSymbol="AAPL"
        onExploreHere={vi.fn()}
        onStartTrace={vi.fn()}
      />,
    );

    expect(screen.getByText('XYZ')).toBeInTheDocument();
    expect(screen.getByText('Unknown Co')).toBeInTheDocument();
    // 옵션 필드 라벨이 표시되지 않아야 함
    expect(screen.queryByText('섹터')).not.toBeInTheDocument();
    expect(screen.queryByText('산업')).not.toBeInTheDocument();
    expect(screen.queryByText('GrowthStage')).not.toBeInTheDocument();
    expect(screen.queryByText('CapitalDNA')).not.toBeInTheDocument();
  });
});
