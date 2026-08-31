/**
 * MP2-SUBPAGES S1 — 거시 허브 페이지 로직 테스트(탭 필터·구조·로딩/에러).
 * 위젯 4종은 stub(recharts 렌더 배제) — 허브의 라우팅/필터 로직에 집중.
 */
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/hooks/useMarketPulse', () => ({ useMarketPulse: vi.fn() }))
vi.mock('next/navigation', () => ({ useSearchParams: vi.fn() }))
vi.mock('@/components/macro/FearGreedGauge', () => ({ default: () => <div data-testid="w-sentiment" /> }))
vi.mock('@/components/macro/YieldCurveChart', () => ({ default: () => <div data-testid="w-rates" /> }))
vi.mock('@/components/macro/EconomicIndicators', () => ({ default: () => <div data-testid="w-economy" /> }))
vi.mock('@/components/macro/GlobalMarketsCard', () => ({ default: () => <div data-testid="w-global" /> }))

import { useMarketPulse } from '@/hooks/useMarketPulse'
import { useSearchParams } from 'next/navigation'
import { macroPulseFixture } from '@/e2e/fixtures/macroPulse'
import MacroHubPage from '@/app/market-pulse-v2/macro/page'

const mockedPulse = vi.mocked(useMarketPulse)
const mockedParams = vi.mocked(useSearchParams)

function setup(tab: string | null, state: 'ok' | 'loading' | 'error' = 'ok') {
  mockedParams.mockReturnValue({ get: (k: string) => (k === 'tab' ? tab : null) } as unknown as ReturnType<typeof useSearchParams>)
  mockedPulse.mockReturnValue({
    data: state === 'ok' ? macroPulseFixture : undefined,
    isLoading: state === 'loading',
    isError: state === 'error',
  } as unknown as ReturnType<typeof useMarketPulse>)
}

afterEach(() => vi.clearAllMocks())

describe('MacroHubPage (MP2-SUBPAGES S1)', () => {
  it('전체 탭 — 4위젯 전부 표시 + 헤더', () => {
    setup('all')
    const { container } = render(<MacroHubPage />)
    expect(screen.getByRole('heading', { name: '거시 근거' })).toBeInTheDocument()
    for (const a of ['sentiment', 'rates', 'economy', 'global']) {
      expect(container.querySelector(`[data-guide="marketPulse.macro.${a}"]`)).toBeTruthy()
    }
  })

  it('tab=rates — 금리·지표만(심리·글로벌 숨김)', () => {
    setup('rates')
    const { container } = render(<MacroHubPage />)
    expect(container.querySelector('[data-guide="marketPulse.macro.rates"]')).toBeTruthy()
    expect(container.querySelector('[data-guide="marketPulse.macro.economy"]')).toBeTruthy()
    expect(container.querySelector('[data-guide="marketPulse.macro.sentiment"]')).toBeNull()
    expect(container.querySelector('[data-guide="marketPulse.macro.global"]')).toBeNull()
  })

  it('tab=sentiment — 심리만', () => {
    setup('sentiment')
    const { container } = render(<MacroHubPage />)
    expect(container.querySelector('[data-guide="marketPulse.macro.sentiment"]')).toBeTruthy()
    expect(container.querySelector('[data-guide="marketPulse.macro.rates"]')).toBeNull()
  })

  it('잘못된 tab → all 폴백', () => {
    setup('bogus')
    const { container } = render(<MacroHubPage />)
    expect(container.querySelector('[data-guide="marketPulse.macro.global"]')).toBeTruthy()
  })

  it('무버스 탭 = 준비 중(비활성)', () => {
    setup('all')
    render(<MacroHubPage />)
    expect(screen.getByText('준비 중')).toBeInTheDocument()
  })

  it('로딩 상태', () => {
    setup(null, 'loading')
    render(<MacroHubPage />)
    expect(screen.getByText('불러오는 중…')).toBeInTheDocument()
  })

  it('에러 상태', () => {
    setup(null, 'error')
    render(<MacroHubPage />)
    expect(screen.getByText('불러오지 못했습니다.')).toBeInTheDocument()
  })
})
