/**
 * MP2-SUBPAGES S1 — 거시 허브 페이지 로직 테스트(탭 필터·구조·로딩/에러).
 * 위젯 4종은 stub(recharts 렌더 배제) — 허브의 라우팅/필터 로직에 집중.
 */
import { fireEvent, render, screen } from '@testing-library/react'
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
import MacroHubPage, { staleMinutes } from '@/app/market-pulse-v2/macro/page'

const mockedPulse = vi.mocked(useMarketPulse)
const mockedParams = vi.mocked(useSearchParams)

const refetchSpy = vi.fn()

function setup(
  tab: string | null,
  state: 'ok' | 'loading' | 'error' = 'ok',
  dataOverride?: unknown,
) {
  mockedParams.mockReturnValue({ get: (k: string) => (k === 'tab' ? tab : null) } as unknown as ReturnType<typeof useSearchParams>)
  mockedPulse.mockReturnValue({
    data: state === 'ok' ? (dataOverride ?? macroPulseFixture) : undefined,
    isLoading: state === 'loading',
    isError: state === 'error',
    refetch: refetchSpy,
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

  it('에러 상태 — 준비 중 안내 + 다시 시도 버튼(refetch 호출)', () => {
    setup(null, 'error')
    render(<MacroHubPage />)
    expect(
      screen.getByText('거시 데이터를 준비 중입니다 — 잠시 후 자동으로 다시 시도합니다.'),
    ).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: '다시 시도' })
    fireEvent.click(retry)
    expect(refetchSpy).toHaveBeenCalledTimes(1)
  })

  it('허브는 useMarketPulse에 timeoutMs=20000 전달(v1 훅 기본은 불변)', () => {
    setup('all')
    render(<MacroHubPage />)
    expect(mockedPulse).toHaveBeenCalledWith({ timeoutMs: 20000 })
  })

  it('나이 배지 — last_updated가 오래되면 "N분 전 데이터" 노출', () => {
    const old = new Date(Date.now() - 30 * 60000).toISOString() // 30분 전
    setup('all', 'ok', { ...macroPulseFixture, last_updated: old })
    render(<MacroHubPage />)
    expect(screen.getByText(/분 전 데이터$/)).toBeInTheDocument()
  })

  it('나이 배지 — 최신 데이터(1분 전)면 배지 숨김', () => {
    const fresh = new Date(Date.now() - 60000).toISOString() // 1분 전
    setup('all', 'ok', { ...macroPulseFixture, last_updated: fresh })
    render(<MacroHubPage />)
    expect(screen.queryByText(/분 전 데이터$/)).toBeNull()
  })
})

describe('staleMinutes (나이 계산 — 5분 경계)', () => {
  const now = Date.parse('2026-08-31T12:00:00Z')
  it('정확히 5분 전 → 5(배지 문턱 > 5이므로 비노출)', () => {
    expect(staleMinutes('2026-08-31T11:55:00Z', now)).toBe(5)
  })
  it('6분 전 → 6(노출)', () => {
    expect(staleMinutes('2026-08-31T11:54:00Z', now)).toBe(6)
  })
  it('미래 시각 → null', () => {
    expect(staleMinutes('2026-08-31T12:05:00Z', now)).toBeNull()
  })
  it('undefined/파싱불가 → null', () => {
    expect(staleMinutes(undefined, now)).toBeNull()
    expect(staleMinutes('not-a-date', now)).toBeNull()
  })
})
