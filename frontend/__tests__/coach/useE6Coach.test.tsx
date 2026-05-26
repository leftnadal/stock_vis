/**
 * Slice 16 Part 2 — useE6Coach 데이터 레이어 테스트.
 *
 * E1/E2 패턴 복제:
 *   1. happy-path: 200 → 봉투 + risk_flags + quoted_metrics
 *   2. error-path: 500 → error
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE6ServerError, mockE6Success } from '../mocks/handlers'
import { useE6Coach } from '@/lib/coach/hooks'
import type { E6Request, E6Response } from '@/lib/coach/types'

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

const validRequest: E6Request = {
  portfolio_id: 'pf-test-e6',
  fetched_at: '2026-05-26T00:00:00Z',
  preset: 'garp',
  entry_point: 'e6',
  holdings: [
    { ticker: 'AAPL', weight: 0.5, sector: 'Tech', asset_class: 'stock', name: 'Apple' },
    { ticker: 'NVDA', weight: 0.5, sector: 'Tech', asset_class: 'stock', name: 'NVIDIA' },
  ],
  analysis_results: {
    AAPL: { score: 0.78, signal: 'bull', notes: 'PEG 1.3' },
    NVDA: { score: 0.42, signal: 'bear', notes: '과열' },
  },
}

describe('useE6Coach', () => {
  it('happy-path: 200 → 봉투 형태 + risk_flags/quoted_metrics 접근', async () => {
    server.use(
      mockE6Success({
        output: {
          summary: 'AAPL 매수, NVDA 차익실현',
          confidence: 'high',
          risk_flags: ['NVDA 변동성 ↑'],
          quoted_metrics: { avg_score: 0.6, bull_signals: 1 },
        },
      }),
    )

    const { result } = renderHook(() => useE6Coach(), { wrapper: createWrapper() })
    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })

    const data: E6Response | undefined = result.current.data
    expect(data).toBeDefined()
    expect(data!.output.summary).toBe('AAPL 매수, NVDA 차익실현')
    expect(data!.output.risk_flags).toEqual(['NVDA 변동성 ↑'])
    expect((data!.output.quoted_metrics as Record<string, unknown>).avg_score).toBe(0.6)
    expect(data!.llm_metadata).toBeDefined()
  })

  it('error-path: 500 → error 노출 + data undefined', async () => {
    server.use(mockE6ServerError())

    const { result } = renderHook(() => useE6Coach(), { wrapper: createWrapper() })
    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 })

    expect(result.current.error?.response?.status).toBe(500)
    expect(result.current.data).toBeUndefined()
  })
})
