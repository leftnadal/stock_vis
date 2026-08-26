/**
 * INC-P16-1 Part B — PlaybookCardContainer lazy-load 테스트.
 * 뷰포트 진입 전 fetch 0 / 진입 후 fetch 1, 진입 후 렌더는 1.6-S1과 동일(요약 줄 표시).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PlaybookCardContainer } from '@/app/market-pulse-v2/cards/PlaybookCardContainer'
import { fetchPlaybook, type PlaybookPayload } from '@/lib/api/marketPulseV2'

// fetchPlaybook만 목 — 실제 usePlaybook 쿼리 경로(enabled 게이팅)를 통과시켜 fetch 호출 수를 관측.
vi.mock('@/lib/api/marketPulseV2', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/marketPulseV2')>()
  return { ...actual, fetchPlaybook: vi.fn() }
})

const PAYLOAD: PlaybookPayload = {
  chains: [
    { id: 'risk_off', name: '위험회피', narrative: '위험회피 국면', cadence: 'daily', lit_count: 1, total: 3, state: 'partial', data_as_of: '2026-08-24' },
  ],
  summary: { total: 1, total_lit: 1, top_chain: { id: 'risk_off', name: '위험회피' } },
}

// IntersectionObserver 목 — 관측 콜백을 잡아 수동 트리거.
let ioInstances: MockIO[] = []
class MockIO {
  cb: IntersectionObserverCallback
  constructor(cb: IntersectionObserverCallback) {
    this.cb = cb
    ioInstances.push(this)
  }
  observe() {}
  unobserve() {}
  disconnect() {}
  enter() {
    this.cb(
      [{ isIntersecting: true, intersectionRatio: 1 } as IntersectionObserverEntry],
      this as unknown as IntersectionObserver,
    )
  }
}

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

const mockedFetch = vi.mocked(fetchPlaybook)

beforeEach(() => {
  ioInstances = []
  vi.stubGlobal('IntersectionObserver', MockIO as unknown as typeof IntersectionObserver)
  mockedFetch.mockResolvedValue({ data: PAYLOAD } as Awaited<ReturnType<typeof fetchPlaybook>>)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('PlaybookCardContainer lazy-load (INC-P16-1 Part B)', () => {
  it('뷰포트 진입 전에는 fetch 하지 않고 자리표시만 렌더', () => {
    render(<PlaybookCardContainer />, { wrapper })
    expect(mockedFetch).not.toHaveBeenCalled()
    expect(screen.getByText('불러오는 중…')).toBeInTheDocument()
  })

  it('뷰포트 진입 시 fetch 1회 + 진입 후 렌더는 기존과 동일(요약 줄)', async () => {
    render(<PlaybookCardContainer />, { wrapper })
    expect(mockedFetch).not.toHaveBeenCalled()

    act(() => ioInstances[0].enter())

    await waitFor(() => expect(mockedFetch).toHaveBeenCalledTimes(1))
    // 진입 후 데이터 렌더 — PlaybookCard(1.6-S1) 결과가 그대로 나타남
    await waitFor(() =>
      expect(screen.getByTestId('playbook-summary')).toBeInTheDocument(),
    )
  })
})
