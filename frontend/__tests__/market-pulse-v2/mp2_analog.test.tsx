/**
 * MP2-ANALOG Slice B — 유사 국면 카드 렌더 회귀.
 *
 * 커버리지: 오늘 4축 z 막대 / ②C 경보 상태 / ①C 팬 + 지평별 N·n_eff / 이웃 리스트 /
 *   label 슬롯 비활성(cat_slot·why = Slice C 연결점) / 빈·unavailable 상태.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AnalogCard } from '@/app/market-pulse-v2/details/AnalogCard'
import type { RegimeAnalogPayload } from '@/lib/api/marketPulseV2'

const AXES: RegimeAnalogPayload['today_axes'] = [
  { axis: 'stress', z: 0.5 },
  { axis: 'financial', z: -1.2 },
  { axis: 'return_1d_pct', z: 0.3 },
  { axis: 'vol_20d_pct', z: null },
]

function alertPayload(): RegimeAnalogPayload {
  return {
    available: true,
    as_of: '2026-07-13',
    today_axes: AXES,
    today_category: null,
    neighbors: [],
    fan: [1, 5, 10, 20, 60].map((h) => ({ horizon: h, median: null, lo: null, hi: null, n: 0, n_eff: 0 })),
    alert: { on: true, nearest_dist: 1.02 },
    meta: { tau_alert: 0.8 },
  }
}

function populatedPayload(): RegimeAnalogPayload {
  return {
    available: true,
    as_of: '2026-07-13',
    today_axes: AXES,
    today_category: { key: 'LATE_BULL', label: '상승 후반 경계' },
    neighbors: [
      { date: '2024-08-05', dist: 0.31, cat_slot: '위기', cat_key: 'CRISIS', why: null, fwd: { '20': 0.042 } },
      { date: '2025-04-03', dist: 0.48, cat_slot: null, cat_key: null, why: null, fwd: { '20': -0.015 } },
    ],
    fan: [
      { horizon: 1, median: 0.001, lo: -0.002, hi: 0.004, n: 2, n_eff: 2 },
      { horizon: 5, median: 0.005, lo: -0.01, hi: 0.02, n: 2, n_eff: 2 },
      { horizon: 10, median: 0.008, lo: -0.02, hi: 0.03, n: 2, n_eff: 2 },
      { horizon: 20, median: 0.013, lo: -0.03, hi: 0.05, n: 2, n_eff: 1 },
      { horizon: 60, median: 0.02, lo: -0.05, hi: 0.09, n: 1, n_eff: 1 },
    ],
    alert: { on: false, nearest_dist: 0.31 },
    meta: { tau_alert: 0.8 },
  }
}

describe('AnalogCard', () => {
  it('오늘 4축 z 막대 렌더(null 축 회색)', () => {
    render(<AnalogCard payload={alertPayload()} />)
    const axes = screen.getByTestId('analog-axes')
    expect(axes).toBeInTheDocument()
    expect(screen.getByTestId('axis-dot-stress')).toBeInTheDocument()
    expect(screen.getByTestId('axis-dot-vol_20d_pct').className).toContain('bg-slate-300')
  })

  it('②C 경보 상태 — 배너 노출·팬 섹션 없음', () => {
    render(<AnalogCard payload={alertPayload()} />)
    expect(screen.getByTestId('analog-alert')).toHaveTextContent('전례 희박')
    // 경보 시 팬·이웃 섹션 전체 미렌더
    expect(screen.queryByTestId('analog-fan')).not.toBeInTheDocument()
    expect(screen.queryByTestId('analog-fan-empty')).not.toBeInTheDocument()
    expect(screen.queryByTestId('analog-fan-legend')).not.toBeInTheDocument()
  })

  it('populated — 팬 + 지평별 N·n_eff + 이웃 리스트', () => {
    render(<AnalogCard payload={populatedPayload()} />)
    expect(screen.queryByTestId('analog-alert')).not.toBeInTheDocument()
    expect(screen.getByTestId('analog-fan')).toBeInTheDocument()
    expect(screen.getByTestId('analog-fan-band')).toBeInTheDocument()
    const legend = screen.getByTestId('analog-fan-legend')
    expect(legend).toHaveTextContent('N2')
    expect(legend).toHaveTextContent('neff1') // 20d n_eff≠n
    expect(screen.getByTestId('analog-nb-2024-08-05')).toBeInTheDocument()
  })

  it('L2 카테고리 태그(C-core) — 이웃 cat_slot 라벨+톤 렌더, null은 —', () => {
    render(<AnalogCard payload={populatedPayload()} />)
    // 채워진 이웃: 사실 분류 라벨('위기') + 톤 클래스(regimeTone CRISIS)
    const cat = screen.getByTestId('analog-cat-2024-08-05')
    expect(cat).toHaveTextContent('위기')
    expect(cat).not.toHaveTextContent('유사') // CRISIS 게이트: 유사성 주장 카피 아님
    expect(cat.className).toContain('border')
    // 미커버 이웃: —
    expect(screen.getByTestId('analog-cat-2025-04-03')).toHaveTextContent('—')
  })

  it('오늘 국면 태그(C-core) — today_category 있으면 렌더', () => {
    render(<AnalogCard payload={populatedPayload()} />)
    expect(screen.getByTestId('analog-today-category')).toHaveTextContent('상승 후반 경계')
  })

  it('오늘 국면 태그(C-core) — today_category 없으면 미표시', () => {
    render(<AnalogCard payload={alertPayload()} />)
    expect(screen.queryByTestId('analog-today-category')).not.toBeInTheDocument()
  })

  it('"왜?"(L3) 슬롯 무접촉 — 여전히 disabled', () => {
    render(<AnalogCard payload={populatedPayload()} />)
    expect(screen.getByTestId('analog-why-slot')).toBeDisabled()
  })

  it('unavailable — 빈 상태', () => {
    render(<AnalogCard payload={{ available: false, today_axes: [], today_category: null, neighbors: [], fan: [], alert: { on: true, nearest_dist: null } }} />)
    expect(screen.getByTestId('analog-unavailable')).toBeInTheDocument()
  })
})
