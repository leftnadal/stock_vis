/**
 * P1-E — useE1Coach 데이터 레이어 테스트 (MSW 기반).
 *
 * 화면 통합 테스트는 Part 3에서. 여기서는 훅 자체의 행동만 검증:
 *   1. happy-path: 200 응답 → mutation.data가 E1Response (봉투) 형태
 *   2. error-path: 500 응답 → mutation.error가 노출
 *
 * 셋업: react-query 표준 — 매 테스트 fresh QueryClient + Provider로 격리.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE1ServerError, mockE1Success } from '../mocks/handlers'
import { useE1Coach } from '@/lib/coach/hooks'
import type { E1Request, E1Response } from '@/lib/coach/types'

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

const validRequest: E1Request = {
  portfolio_id: 'pf-test-1',
  fetched_at: '2026-05-25T00:00:00Z',
  preset: 'growth',
  entry_point: 'e1',
  holdings: [
    { ticker: 'AAPL', weight: 0.4, sector: 'Tech', asset_class: 'stock', name: 'Apple' },
    { ticker: 'MSFT', weight: 0.6, sector: 'Tech', asset_class: 'stock', name: 'Microsoft' },
  ],
  garp_metrics: {
    AAPL: { eps_growth_rate: 0.12, pe_ratio: 18, peg_ratio: 1.5 },
    MSFT: { eps_growth_rate: 0.15, pe_ratio: 22, peg_ratio: 1.4 },
  },
}

describe('useE1Coach', () => {
  it('happy-path: 200 응답이 E1Response 봉투 형태로 도착', async () => {
    server.use(
      mockE1Success({
        output: {
          summary: 'test summary',
          confidence: 'high',
          metrics_table: '',
        },
      }),
    )

    const { result } = renderHook(() => useE1Coach(), { wrapper: createWrapper() })

    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })

    const data: E1Response | undefined = result.current.data
    expect(data).toBeDefined()
    // 봉투 형태 검증 — output + llm_metadata 필수
    expect(data!.output.summary).toBe('test summary')
    expect(data!.output.confidence).toBe('high')
    expect(data!.llm_metadata).toBeDefined()
    expect(data!.llm_metadata.provider).toBe('haiku')
  })

  it('error-path: 500 응답에서 error가 노출되고 data는 undefined', async () => {
    server.use(mockE1ServerError())

    const { result } = renderHook(() => useE1Coach(), { wrapper: createWrapper() })

    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 })

    expect(result.current.error).toBeDefined()
    expect(result.current.error?.response?.status).toBe(500)
    expect(result.current.data).toBeUndefined()
  })
})
