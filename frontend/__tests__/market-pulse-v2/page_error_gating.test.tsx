/**
 * INC-P16-CLOSE Part 3 — market-pulse-v2 page.tsx 에러 원인 구분 게이팅.
 * 429/401/기타 3분기 렌더 + 기존 기본 문구 보존.
 *
 * 훅을 목해 에러 객체 shape(response.status)를 정확히 주입한다(MSW 경로는 401을
 * client 인터셉터가 refresh로 변형하므로 분기 단위 검증엔 부적합).
 */
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MarketPulseV2Page from '@/app/market-pulse-v2/page'

const refetch = vi.fn()

// 페이지가 마운트에 호출하는 훅 전부 목(에러 분기는 조기 반환이라 본문 미렌더).
vi.mock('@/hooks/useMarketPulseV2', () => ({
  useOverview: vi.fn(),
  useRegimeStress: () => ({ data: undefined }),
}))
vi.mock('@/lib/i18n/marketPulse', () => ({
  useMarketPulseI18n: () => ({ data: undefined }),
  translate: (k: string) => k,
}))

import { useOverview } from '@/hooks/useMarketPulseV2'
const mockedUseOverview = vi.mocked(useOverview)

function setError(status: number | undefined) {
  mockedUseOverview.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: true,
    error: status === undefined ? new Error('boom') : { response: { status } },
    refetch,
  } as unknown as ReturnType<typeof useOverview>)
}

afterEach(() => vi.clearAllMocks())

describe('MarketPulseV2Page 에러 원인 구분 (INC-P16-CLOSE Part 3)', () => {
  it('429 → 요청 제한 안내 + 다시 시도 (스로틀 등 기술용어 미노출)', () => {
    setError(429)
    render(<MarketPulseV2Page />)
    expect(screen.getByText('요청이 많아 잠시 제한됐어요. 잠시 후 다시 시도해 주세요.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '다시 시도' })).toBeInTheDocument()
    expect(screen.queryByText(/스로틀|throttle|429/i)).toBeNull()
  })

  it('401 → 로그인 필요 안내 + 로그인 이동', () => {
    setError(401)
    render(<MarketPulseV2Page />)
    expect(screen.getByText('로그인이 필요합니다.')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: '로그인' })
    expect(link).toHaveAttribute('href', '/login')
  })

  it('기타(500) → 기존 문구 유지', () => {
    setError(500)
    render(<MarketPulseV2Page />)
    expect(screen.getByText('데이터를 불러오지 못했습니다.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '다시 시도' })).toBeInTheDocument()
  })

  it('status 없는 에러(네트워크 등) → 기존 문구(기타 분기)', () => {
    setError(undefined)
    render(<MarketPulseV2Page />)
    expect(screen.getByText('데이터를 불러오지 못했습니다.')).toBeInTheDocument()
  })
})
