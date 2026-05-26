/**
 * Slice 16 Part 4 — useE5Coach 데이터 레이어 테스트.
 *
 * E3 패턴 복제 + E5 특수 (extraction_targets + time_series_context).
 * 2건 (happy + error).
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE5ServerError, mockE5Success } from '../mocks/handlers'
import { useE5Coach } from '@/lib/coach/hooks'
import type { E5Request, E5Response } from '@/lib/coach/types'

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

const validRequest: E5Request = {
  portfolio_id: 'pf-test-e5',
  fetched_at: '2026-05-26T00:00:00Z',
  preset: 'garp',
  entry_point: 'e5',
  holdings: [
    { ticker: 'AAPL', weight: 0.5, sector: 'Tech', asset_class: 'stock', name: 'Apple' },
    { ticker: 'JNJ', weight: 0.5, sector: 'Healthcare', asset_class: 'stock', name: 'Johnson' },
  ],
  extraction_targets: ['dividend_yield', 'beta'],
  time_series_context: {
    current: '3.45',
    window_1q: '3.40',
    window_4q: '3.30',
    window_12q: '3.15',
  },
}

describe('useE5Coach', () => {
  it('happy-path: 200 → 봉투 + action_items + quoted_metrics', async () => {
    server.use(
      mockE5Success({
        output: {
          summary: '배당수익률 3.45% 우상향',
          confidence: 'high',
          action_items: [
            {
              title: '배당 성장 모니터링',
              description: '4분기 변화율 추적',
              priority: 'medium',
              category: 'monitor',
            },
          ],
          quoted_metrics: { dividend_yield: '3.45%', beta: '1.12' },
        },
      }),
    )

    const { result } = renderHook(() => useE5Coach(), { wrapper: createWrapper() })
    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })

    const data: E5Response | undefined = result.current.data
    expect(data).toBeDefined()
    expect(data!.output.summary).toBe('배당수익률 3.45% 우상향')
    expect(data!.output.action_items).toHaveLength(1)
    expect((data!.output.quoted_metrics as Record<string, unknown>).dividend_yield).toBe('3.45%')
    expect(data!.llm_metadata).toBeDefined()
  })

  it('time_series_context = null 으로도 호출 가능 (optional)', async () => {
    server.use(mockE5Success())

    const requestWithoutTs: E5Request = { ...validRequest, time_series_context: null }
    const { result } = renderHook(() => useE5Coach(), { wrapper: createWrapper() })
    result.current.mutate(requestWithoutTs)

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })
    expect(result.current.data).toBeDefined()
  })

  it('error-path: 500 → error 노출 + data undefined', async () => {
    server.use(mockE5ServerError())

    const { result } = renderHook(() => useE5Coach(), { wrapper: createWrapper() })
    result.current.mutate(validRequest)

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 })

    expect(result.current.error?.response?.status).toBe(500)
    expect(result.current.data).toBeUndefined()
  })
})
