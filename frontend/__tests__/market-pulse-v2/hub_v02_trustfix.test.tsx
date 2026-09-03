/**
 * HUB-V02-S1 신뢰 수리 FE — A-1 기준일 배지 · A-2 anomaly no_data 중립표기 · A-3 금/은 라벨.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { TickerBar } from '@/app/market-pulse-v2/components/TickerBar'
import { AnomalyPanel } from '@/app/market-pulse-v2/components/AnomalyPanel'
import { BreadthCardSummary } from '@/app/market-pulse-v2/cards/BreadthCardSummary'
import type { AnomalySection, BreadthCard, TickerItem } from '@/lib/api/marketPulseV2'

const BREADTH: BreadthCard = {
  universe: 'SPY',
  advance: 300,
  decline: 200,
  unchanged: 1,
  total: 501,
  new_high_52w: 18,
  new_low_52w: 14,
  ad_line: 42,
  ad_line_change: 100,
}

describe('A-1 Breadth 기준일 배지', () => {
  it('as_of_date 있으면 "기준일 MM-DD" 표기', () => {
    render(<BreadthCardSummary data={{ ...BREADTH, as_of_date: '2026-09-02' }} />)
    expect(screen.getByText(/기준일 09-02/)).toBeInTheDocument()
  })
  it('as_of_date 없으면 배지 미표기(구버전 응답 호환)', () => {
    render(<BreadthCardSummary data={BREADTH} />)
    expect(screen.queryByText(/기준일/)).toBeNull()
  })
})

describe('A-2 Anomaly no_data 중립표기', () => {
  const base: AnomalySection = {
    mode: 'CALM',
    overview: '',
    sector_highlight: '',
    portfolio_action: '',
    fired: [],
  }
  it('status=no_data → "판정 불가" + "정상과 다릅니다"(경보 아님)', () => {
    render(<AnomalyPanel data={{ ...base, status: 'no_data', overview: '판정 불가 — 입력 데이터 대기 중.' }} />)
    expect(screen.getByText('판정 불가')).toBeInTheDocument()
    expect(screen.getByText(/정상.*과 다릅니다/)).toBeInTheDocument()
  })
  it('status=evaluated CALM → 정상 범위 총평(기존 렌더)', () => {
    render(<AnomalyPanel data={{ ...base, status: 'evaluated', overview: '시장 정상 범위 — 발동 룰 없음.' }} />)
    expect(screen.getByText('시장 정상 범위 — 발동 룰 없음.')).toBeInTheDocument()
    expect(screen.queryByText('판정 불가')).toBeNull()
  })
})

describe('A-3 TickerBar 금/은 라벨', () => {
  it('GCUSD→금, SIUSD→은, 그 외는 심볼 그대로', () => {
    const items: TickerItem[] = [
      { symbol: 'GCUSD', last_close: 4435, change_pct: 0.5, sector_group: 'BENCHMARK' },
      { symbol: 'SIUSD', last_close: 65.9, change_pct: -0.3, sector_group: 'BENCHMARK' },
      { symbol: 'SPY', last_close: 769, change_pct: 0.1, sector_group: 'BENCHMARK' },
    ]
    render(<TickerBar items={items} />)
    expect(screen.getByText('금')).toBeInTheDocument()
    expect(screen.getByText('은')).toBeInTheDocument()
    expect(screen.getByText('SPY')).toBeInTheDocument()
  })
})
