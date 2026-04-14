import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import PeerContextBar from '@/components/validation/PeerContextBar';
import type { PeerInfo, PresetInfo } from '@/types/validation';

const basePeerInfo: PeerInfo = {
  industry: 'Software',
  peer_count: 12,
  confidence: 'high',
  benchmark_basis: 'industry_size',
  size_bucket: 'large',
  basis_description: 'Software - Large Cap',
  top_peers: ['MSFT', 'GOOGL', 'META'],
  industry_leader: { symbol: 'AAPL', name: 'Apple Inc.', market_cap: 3000000000000 },
};

const presets: PresetInfo[] = [
  {
    preset_key: 'industry_size',
    display_name: '업종+규모',
    logic_summary: '동일 업종, 유사 시가총액',
    peer_count: 12,
    confidence_score: 0.85,
    confidence_label: '높음',
    is_selected: true,
    is_default: true,
  },
  {
    preset_key: 'sector',
    display_name: '섹터 전체',
    logic_summary: '동일 섹터 전체',
    peer_count: 45,
    confidence_score: 0.6,
    confidence_label: '보통',
    is_selected: false,
    is_default: false,
  },
];

describe('PeerContextBar', () => {
  it('peer 정보와 신뢰도 배지를 렌더링한다', () => {
    render(<PeerContextBar peerInfo={basePeerInfo} fiscalYear={2025} />);

    expect(screen.getByText(/Software - Large Cap/)).toBeInTheDocument();
    expect(screen.getByText(/12개/)).toBeInTheDocument();
    expect(screen.getByText(/비교 신뢰도: 높음/)).toBeInTheDocument();
    expect(screen.getByText(/2025 FY/)).toBeInTheDocument();
  });

  it('프리셋 탭을 렌더링하고 클릭 시 onSelectPreset을 호출한다', () => {
    const onSelectPreset = vi.fn();

    render(
      <PeerContextBar
        peerInfo={basePeerInfo}
        fiscalYear={2025}
        presets={presets}
        onSelectPreset={onSelectPreset}
      />,
    );

    const sectorBtn = screen.getByText('섹터 전체', { exact: false });
    expect(sectorBtn).toBeInTheDocument();
    fireEvent.click(sectorBtn);
    expect(onSelectPreset).toHaveBeenCalledWith('sector');
  });

  it('peer 목록 보기/접기를 토글한다', () => {
    render(<PeerContextBar peerInfo={basePeerInfo} fiscalYear={2025} />);

    const toggleBtn = screen.getByText(/peer 목록 보기/);
    fireEvent.click(toggleBtn);

    expect(screen.getByText('MSFT')).toBeInTheDocument();
    expect(screen.getByText('GOOGL')).toBeInTheDocument();
    expect(screen.getByText('META')).toBeInTheDocument();

    fireEvent.click(screen.getByText(/peer 목록 접기/));
    expect(screen.queryByText('MSFT')).not.toBeInTheDocument();
  });

  it('커스텀 입력에서 2개 미만 심볼 입력 시 onSetCustomPeers를 호출하지 않는다', () => {
    const onSetCustomPeers = vi.fn();

    render(
      <PeerContextBar
        peerInfo={basePeerInfo}
        fiscalYear={2025}
        presets={presets}
        onSelectPreset={vi.fn()}
        onSetCustomPeers={onSetCustomPeers}
      />,
    );

    fireEvent.click(screen.getByText('직접 설정'));

    const input = screen.getByPlaceholderText(/심볼 입력/);
    fireEvent.change(input, { target: { value: 'TSLA' } });
    fireEvent.click(screen.getByText('적용'));

    expect(onSetCustomPeers).not.toHaveBeenCalled();

    // 2개 이상 입력하면 호출
    fireEvent.change(input, { target: { value: 'TSLA, NVDA' } });
    fireEvent.click(screen.getByText('적용'));

    expect(onSetCustomPeers).toHaveBeenCalledWith(['TSLA', 'NVDA']);
  });
});
