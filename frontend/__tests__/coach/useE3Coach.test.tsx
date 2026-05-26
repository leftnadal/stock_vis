/**
 * Slice 16 Part 3 — useE3Coach 데이터 레이어 테스트.
 *
 * E1/E2/E6 패턴 복제. 2건 (happy + error).
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE3ServerError, mockE3Success } from '../mocks/handlers'
import { useE3Coach } from '@/lib/coach/hooks'
import type { E3Request, E3Response } from '@/lib/coach/types'

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

const validRequest: E3Request = {
  portfolio_id: 'pf-test-e3',
  fetched_at: '2026-05-26T00:00:00Z',
  preset: 'garp',
  entry_point: 'e3',
  holdings: [
    { ticker: 'AAPL', weight: 0.6, sector: 'Tech', asset_class: 'stock', name: 'Apple' },
    { ticker: 'MSFT', weight: 0.25, sector: 'Tech', asset_class: 'stock', name: 'Microsoft' },
    { ticker: 'NVDA', weight: 0.15, sector: 'Tech', asset_class: 'stock', name: 'NVIDIA' },
  ],
  concentration_metrics: {
    hhi: 0.52,
    top3_weight: 1.0,
    sector_concentration: 1.0,
    holding_count: 3,
  },
}

describe('useE3Coach', () => {
  it('happy-path: 200 → 봉투 + action_items + risk_flags', async () => {
    server.use(
      mockE3Success({
        output: {
          summary: 'AAPL 60% 집중 위험',
          confidence: 'high',
          action_items: [
            {
              title: 'AAPL 비중 축소',
              description: '60% → 40%',
              priority: 'high',
              category: 'rebalance',
            },
          ],
          risk_flags: ['단일 종목 집중도 60%'],
        },
      }),
    )

    const { result } = renderHook(() => useE3Coach(), { wrapper: createWrapper() })
    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })

    const data: E3Response | undefined = result.current.data
    expect(data).toBeDefined()
    expect(data!.output.summary).toBe('AAPL 60% 집중 위험')
    expect(data!.output.action_items).toHaveLength(1)
    expect(data!.output.action_items?.[0].priority).toBe('high')
    expect(data!.output.risk_flags).toEqual(['단일 종목 집중도 60%'])
    expect(data!.llm_metadata).toBeDefined()
  })

  it('error-path: 500 → error 노출 + data undefined', async () => {
    server.use(mockE3ServerError())

    const { result } = renderHook(() => useE3Coach(), { wrapper: createWrapper() })
    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 })

    expect(result.current.error?.response?.status).toBe(500)
    expect(result.current.data).toBeUndefined()
  })
})
