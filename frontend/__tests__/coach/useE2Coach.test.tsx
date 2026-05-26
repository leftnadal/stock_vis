/**
 * Slice 16 Part 1 — useE2Coach 데이터 레이어 테스트.
 *
 * E1 패턴(`useE1Coach.test.tsx`) 복제:
 *   1. happy-path: 200 응답 → mutation.data가 E2Response (봉투, quoted_metrics 포함)
 *   2. error-path: 500 응답 → mutation.error
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE2ServerError, mockE2Success } from '../mocks/handlers'
import { useE2Coach } from '@/lib/coach/hooks'
import type { E2Request, E2Response } from '@/lib/coach/types'

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

const validRequest: E2Request = {
  portfolio_id: 'pf-test-e2',
  fetched_at: '2026-05-26T00:00:00Z',
  preset: 'garp',
  entry_point: 'e2',
  holdings: [
    { ticker: 'AAPL', weight: 0.5, sector: 'Tech', asset_class: 'stock', name: 'Apple' },
    { ticker: 'JNJ', weight: 0.5, sector: 'Healthcare', asset_class: 'stock', name: 'Johnson' },
  ],
  portfolio_return_1y: 12.5,
  sector_allocation: { Tech: 0.5, Healthcare: 0.5 },
}

describe('useE2Coach', () => {
  it('happy-path: 200 응답이 E2Response 봉투 형태(quoted_metrics 포함)로 도착', async () => {
    server.use(
      mockE2Success({
        output: {
          summary: '균형 잡힌 2섹터 포트폴리오',
          confidence: 'high',
          quoted_metrics: { portfolio_return_1y: 12.5, tech_weight: 0.5 },
          metrics_table: '',
        },
      }),
    )

    const { result } = renderHook(() => useE2Coach(), { wrapper: createWrapper() })
    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })

    const data: E2Response | undefined = result.current.data
    expect(data).toBeDefined()
    expect(data!.output.summary).toBe('균형 잡힌 2섹터 포트폴리오')
    expect(data!.output.confidence).toBe('high')
    expect(data!.output.quoted_metrics).toBeDefined()
    expect((data!.output.quoted_metrics as Record<string, unknown>).tech_weight).toBe(0.5)
    expect(data!.llm_metadata).toBeDefined()
  })

  it('error-path: 500 응답에서 error 노출 + data undefined', async () => {
    server.use(mockE2ServerError())

    const { result } = renderHook(() => useE2Coach(), { wrapper: createWrapper() })
    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 })

    expect(result.current.error).toBeDefined()
    expect(result.current.error?.response?.status).toBe(500)
    expect(result.current.data).toBeUndefined()
  })
})
