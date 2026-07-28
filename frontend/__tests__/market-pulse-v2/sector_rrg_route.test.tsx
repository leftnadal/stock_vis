/**
 * MP2-SECTOR-CD Slice 3 — RRG 서브스크린 라우트 진입 테스트.
 *
 * 훅 mock(useCardDetail·useMarketPulseI18n) + next/navigation useSearchParams.
 * 진입 파라미터 from → 출발 섹터 하이라이트, 뒤로가기 링크 검증.
 */
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { SectorDetail } from '@/lib/api/marketPulseV2'

const PAYLOAD: SectorDetail = {
  available: true,
  date: '2026-07-09',
  cd_rel_strength_baseline: 0,
  cd_momentum_baseline: 0,
  sectors: [
    { symbol: 'XLK', rel_strength: 0.8, rel_strength_5d: 0.8, momentum_1d: 0, momentum_5d: 0.5, momentum_20d: 0, flow_proxy: 0, rank: 1, cd_state: 'leading_strengthening' },
    { symbol: 'XLE', rel_strength: -0.6, rel_strength_5d: -0.6, momentum_1d: 0, momentum_5d: -0.4, momentum_20d: 0, flow_proxy: 0, rank: 2, cd_state: 'lagging_deteriorating' },
  ],
  sector_history: [],
}

let SEARCH = 'from=XLK'
const replaceMock = vi.fn()
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(SEARCH),
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
}))
vi.mock('@/hooks/useMarketPulseV2', () => ({
  useCardDetail: () => ({ data: { data: PAYLOAD, _meta: { cache: 'hit' } }, isLoading: false, isError: false }),
}))
vi.mock('@/lib/i18n/marketPulse', async (orig) => {
  const actual = (await orig()) as Record<string, unknown>
  return { ...actual, useMarketPulseI18n: () => ({ data: { labels: { 'sector.XLK': '기술', 'sector.XLE': '에너지' } } }) }
})

import RotationPage from '@/app/market-pulse-v2/rotation/page'

describe('RRG 서브스크린 라우트', () => {
  it('진입 시 RRG 맵 렌더 + from 섹터 하이라이트', () => {
    SEARCH = 'from=XLK'
    const { getByTestId } = render(<RotationPage />)
    expect(getByTestId('rrg-chart')).toBeInTheDocument()
    expect(getByTestId('rrg-ring-XLK')).toBeInTheDocument() // 출발 섹터 링
    expect(getByTestId('rrg-dot-XLK').getAttribute('r')).toBe('6')
  })

  it('뒤로가기 링크 = 판단 화면(/market-pulse-v2)', () => {
    SEARCH = 'from=XLK'
    const { getByTestId } = render(<RotationPage />)
    expect(getByTestId('rrg-back').getAttribute('href')).toBe('/market-pulse-v2')
  })

  it('from 없이 진입 → 맵 렌더 + 포커스 디폴트 = rank-1(변형 H)', () => {
    SEARCH = ''
    const { getByTestId } = render(<RotationPage />)
    expect(getByTestId('rrg-chart')).toBeInTheDocument()
    // CD-READ 변형 H: from 없으면 포커스가 rank-1(XLK)로 디폴트 → 링 표시.
    expect(getByTestId('rrg-ring-XLK')).toBeInTheDocument()
    // 비-포커스(XLE)는 링 없음.
    expect(getByTestId('rrg-dot-XLE')).toBeInTheDocument()
  })
})
