/**
 * MPS-2 — StressCard 렌더 회귀 (목업 부재 → §부록 렌더 스펙 + D-MPS-COLOR 안 1).
 *
 * 커버리지(6상태): stable · severe · 괴리(가격 상승 ∧ 스트레스 악화) · available:false ·
 *   loading · error. band_provisional 미표시 · 금지 어휘 부재 · 색=stressAlert 토큰(하드코딩 0).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse, delay } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { StressCard } from '@/app/market-pulse-v2/cards/StressCard'
import { StressCardContainer } from '@/app/market-pulse-v2/cards/StressCardContainer'
import { MP_V2_BASE, type RegimeStressPayload } from '@/lib/api/marketPulseV2'

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

function payload(over: Partial<RegimeStressPayload> = {}): RegimeStressPayload {
  return {
    available: true,
    as_of: '2026-08-13',
    score: 1.62,
    level_band: 'severe',
    percentile: { value: 94, window_days: 803 },
    direction: {
      stress: { d5: 0.2, d20: 0.4, state: 'worsening' },
      price: { vs_ma20: 'above', vs_ma60: 'above', state: 'uptrend' },
    },
    categories: [
      { key: 'volatility', z: 1.1, d5: 0.2 },
      { key: 'credit', z: 0.8, d5: 0.1 },
      { key: 'curve', z: 1.3, d5: 0.05 },
      { key: 'financial_conditions', z: 0.9, d5: 0.3 },
      { key: 'price', z: 0.2, d5: -0.1 },
    ],
    meta: { population: 683, band_thresholds: { low: 0.5, high: 1.5 }, band_provisional: true },
    ...over,
  }
}

function stableP(): RegimeStressPayload {
  return payload({
    score: -0.18,
    level_band: 'stable',
    percentile: { value: 35.1, window_days: 803 },
    direction: {
      stress: { d5: -0.08, d20: 0.05, state: 'mixed' },
      price: { vs_ma20: 'above', vs_ma60: 'above', state: 'uptrend' },
    },
  })
}

describe('StressCard 뷰(payload 구동)', () => {
  it('severe: 심화 문구 + 상위 6% + 카테고리 5 + "위기" 부재', () => {
    render(<StressCard data={payload()} />)
    expect(screen.getByTestId('stress-card')).toBeInTheDocument()
    expect(screen.getByText(/심화/)).toBeInTheDocument()
    expect(screen.getByText(/상위 6%/)).toBeInTheDocument()
    // 카테고리 5종
    expect(screen.getAllByTestId('stress-category-row')).toHaveLength(5)
    // 금지 어휘 부재(FE 렌더 짝)
    expect(screen.getByTestId('stress-card').textContent).not.toMatch(/위기|crisis/i)
  })

  it('괴리(가격 상승 ∧ 스트레스 악화): 전용 강조 배지', () => {
    render(<StressCard data={payload()} />)
    expect(screen.getByTestId('stress-divergence-badge')).toBeInTheDocument()
    expect(screen.getByText(/괴리/)).toBeInTheDocument()
  })

  it('stable: 낮은 수준(상위% 미생성) + band_provisional 미표시', () => {
    render(<StressCard data={stableP()} />)
    expect(screen.getByText(/낮은 수준/)).toBeInTheDocument()
    expect(screen.getByTestId('stress-card').textContent).not.toMatch(/상위/)
    expect(screen.queryByTestId('stress-divergence-badge')).toBeNull()
    // band_provisional은 내부 메타 — 화면 미노출
    expect(screen.getByTestId('stress-card').textContent).not.toMatch(/잠정|provisional/i)
  })

  it('available:false: 미표시 placeholder', () => {
    render(<StressCard data={{ available: false } as RegimeStressPayload} />)
    expect(screen.getByTestId('stress-unavailable')).toBeInTheDocument()
  })
})

describe('StressCardContainer(fetch 분기)', () => {
  it('loading', () => {
    server.use(
      http.get(`${MP_V2_BASE}/regime/stress`, async () => {
        await delay(100)
        return HttpResponse.json({ _meta: {}, data: payload() })
      }),
    )
    wrap(<StressCardContainer />)
    expect(screen.getByTestId('stress-loading')).toBeInTheDocument()
  })

  it('error', async () => {
    server.use(
      http.get(`${MP_V2_BASE}/regime/stress`, () => HttpResponse.json({}, { status: 500 })),
    )
    wrap(<StressCardContainer />)
    await waitFor(() => expect(screen.getByTestId('stress-error')).toBeInTheDocument())
  })

  it('populated: 봉투 언랩 후 뷰 렌더', async () => {
    server.use(
      http.get(`${MP_V2_BASE}/regime/stress`, () =>
        HttpResponse.json({ _meta: { generated_at: 'x', latency_ms: 1, cache: 'MISS' }, data: payload() }),
      ),
    )
    wrap(<StressCardContainer />)
    await waitFor(() => expect(screen.getByTestId('stress-card')).toBeInTheDocument())
    expect(screen.getByText(/심화/)).toBeInTheDocument()
  })
})
