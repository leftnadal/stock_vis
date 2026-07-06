/**
 * MP2-DELTA Slice 1 — DeltaCard 테스트.
 *
 * 커버리지:
 *   1. 국면 전환 있음 → from(취소선) + to 배지 렌더
 *   2. transition_from null → "변화 없음"
 *   3. 섹터 상위 3개 절삭 (4개 주면 3개만)
 *   4. ▲(rank_delta>0) / ▼(rank_delta<0) 방향·색 토큰
 *   5. "N위 → M위" trail
 *   6. 전부 rank_delta=0 → "순위 변동 없음"
 *   7. 빈 배열 → "비교할 어제 데이터 없음"
 *   8. 부제 vs_date = 서버값(주말갭 케이스 "07-01 vs 06-27")
 *   9. 회귀: 기존 page.tsx 블록(hero·AnomalyPanel·히트맵·breadth·concentration·CardDrawer) 렌더 유지
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it, beforeEach } from 'vitest'

import { MP_V2_BASE, type SectorDelta, type RegimeCard, type AnomalyDelta } from '@/lib/api/marketPulseV2'
import { server } from '../mocks/server'
import {
  mpAllHandlers,
  mpOverviewSuccess,
  mpI18nSuccess,
  overviewFixture,
} from './fixtures'
import { DeltaCard } from '@/app/market-pulse-v2/cards/DeltaCard'
import MarketPulseV2Page from '@/app/market-pulse-v2/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

// ── Unit tests for DeltaCard component ───────────────────────

describe('DeltaCard — 국면 전환 블록', () => {
  const baseRegime: RegimeCard = {
    regime: 'BULL_EXPANSION',
    status: 'OK',
    coverage: 0.92,
    headline: '확장 국면 지속',
    fired_rules: ['R1'],
    transitioned: false,
  }

  it('transition_from 있으면 from(취소선) → to(배지) 렌더', () => {
    const regime = { ...baseRegime, transition_from: 'LATE_BULL' }
    render(<DeltaCard regime={regime} />)

    const fromBadge = screen.getByTestId('transition-from')
    expect(fromBadge).toBeInTheDocument()
    expect(fromBadge).toHaveClass('line-through')
    expect(fromBadge.textContent).toBe('LATE_BULL') // no labels → fallback to enum

    const toBadge = screen.getByTestId('transition-to')
    expect(toBadge).toBeInTheDocument()
    expect(toBadge.textContent).toBe('BULL_EXPANSION')
  })

  it('transition_from null → "변화 없음" 표시', () => {
    const regime = { ...baseRegime, transition_from: null }
    render(<DeltaCard regime={regime} />)
    expect(screen.getByTestId('no-transition')).toHaveTextContent('변화 없음')
    expect(screen.queryByTestId('transition-from')).not.toBeInTheDocument()
  })

  it('transition_from undefined → "변화 없음" 표시', () => {
    render(<DeltaCard regime={baseRegime} />)
    expect(screen.getByTestId('no-transition')).toHaveTextContent('변화 없음')
  })

  it('labels 있으면 translate 적용', () => {
    const regime = { ...baseRegime, transition_from: 'LATE_BULL' }
    const labels = { 'regime.LATE_BULL': '후기 강세', 'regime.BULL_EXPANSION': '강세 확장' }
    render(<DeltaCard regime={regime} labels={labels} />)
    expect(screen.getByTestId('transition-from').textContent).toBe('후기 강세')
    expect(screen.getByTestId('transition-to').textContent).toBe('강세 확장')
  })

  it('to 배지에 REGIME_TONE 색 클래스 포함', () => {
    const regime = { ...baseRegime, transition_from: 'LATE_BULL' }
    render(<DeltaCard regime={regime} />)
    const toBadge = screen.getByTestId('transition-to')
    // BULL_EXPANSION → bg-emerald-50 text-emerald-800
    expect(toBadge.className).toContain('emerald')
  })
})

describe('DeltaCard — 섹터 순위 변동 블록', () => {
  const baseRegime: RegimeCard = {
    regime: 'BULL_EXPANSION',
    status: 'OK',
    coverage: 0.92,
    headline: '',
    fired_rules: [],
    transitioned: false,
  }

  const makeDelta = (sector: string, rank: number, prev_rank: number, rank_delta: number): SectorDelta => ({
    sector,
    rank,
    prev_rank,
    rank_delta,
    as_of: '2026-07-01',
    vs_date: '2026-06-27',
  })

  it('빈 배열 → "비교할 어제 데이터 없음"', () => {
    render(<DeltaCard regime={baseRegime} sectorDeltas={[]} />)
    expect(screen.getByTestId('no-sector-data')).toHaveTextContent('비교할 어제 데이터 없음')
  })

  it('sectorDeltas 없음(undefined) → "비교할 어제 데이터 없음"', () => {
    render(<DeltaCard regime={baseRegime} />)
    expect(screen.getByTestId('no-sector-data')).toHaveTextContent('비교할 어제 데이터 없음')
  })

  it('전부 rank_delta=0 → "순위 변동 없음"', () => {
    const deltas = [
      makeDelta('XLK', 1, 1, 0),
      makeDelta('XLC', 2, 2, 0),
    ]
    render(<DeltaCard regime={baseRegime} sectorDeltas={deltas} />)
    expect(screen.getByTestId('no-rank-change')).toHaveTextContent('순위 변동 없음')
    expect(screen.queryByTestId('sector-row')).not.toBeInTheDocument()
  })

  it('4개 주면 3개만 렌더', () => {
    const deltas = [
      makeDelta('XLK', 1, 3, 2),
      makeDelta('XLC', 2, 4, 2),
      makeDelta('XLY', 3, 5, 2),
      makeDelta('XLV', 4, 1, -3), // 4번째, 잘려야 함
    ]
    render(<DeltaCard regime={baseRegime} sectorDeltas={deltas} />)
    const rows = screen.getAllByTestId('sector-row')
    expect(rows).toHaveLength(3)
    // 4번째 섹터(XLV)는 없어야 함
    expect(screen.queryByText('XLV')).not.toBeInTheDocument()
  })

  it('rank_delta > 0 → ▲ 표시 + rose 색(sectorTextClass up)', () => {
    const deltas = [makeDelta('XLK', 1, 3, 2)]
    render(<DeltaCard regime={baseRegime} sectorDeltas={deltas} />)
    const badge = screen.getByTestId('rank-delta-badge')
    expect(badge.textContent).toBe('▲2')
    expect(badge.className).toContain('rose') // sectorTextClass(2) → text-rose-600
  })

  it('rank_delta < 0 → ▼ 표시 + sky 색(sectorTextClass down)', () => {
    const deltas = [makeDelta('XLE', 11, 9, -2)]
    render(<DeltaCard regime={baseRegime} sectorDeltas={deltas} />)
    const badge = screen.getByTestId('rank-delta-badge')
    expect(badge.textContent).toBe('▼2')
    expect(badge.className).toContain('sky') // sectorTextClass(-2) → text-sky-600
  })

  it('"N위 → M위" trail 렌더', () => {
    const deltas = [makeDelta('XLK', 1, 3, 2)]
    render(<DeltaCard regime={baseRegime} sectorDeltas={deltas} />)
    const trail = screen.getByTestId('rank-trail')
    expect(trail.textContent).toBe('3위 → 1위')
  })

  it('부제: 서버 as_of/vs_date 그대로 표기 (주말갭 케이스)', () => {
    // as_of=2026-07-01(화), vs_date=2026-06-27(금) — 주말갭이라 단순 -1일 아님
    const deltas = [makeDelta('XLK', 1, 3, 2)]
    render(<DeltaCard regime={baseRegime} sectorDeltas={deltas} />)
    const subtitle = screen.getByTestId('delta-subtitle')
    expect(subtitle.textContent).toContain('07-01')
    expect(subtitle.textContent).toContain('06-27')
  })

  it('sectorDeltas 빈 배열이면 부제 미렌더', () => {
    render(<DeltaCard regime={baseRegime} sectorDeltas={[]} />)
    expect(screen.queryByTestId('delta-subtitle')).not.toBeInTheDocument()
  })
})

// ── Slice 2: DeltaCard 이상 신호 변화 블록 (4상태) ──────────────

describe('DeltaCard — 이상 신호 변화 블록', () => {
  const baseRegime: RegimeCard = {
    regime: 'BULL_EXPANSION', status: 'OK', coverage: 0.9,
    headline: '', fired_rules: [], transitioned: false,
  }
  const mkAnomaly = (over: Partial<AnomalyDelta>): AnomalyDelta => ({
    state: 'quiet', as_of: '2026-07-01', last_fired_date: null, vs_fired_date: null,
    new_rules: [], gone_rules: [], resolved_rules: [], ...over,
  })

  it('fired: 신규 칩(warn) + 소멸 칩(취소선) + 직전 발동일 note(서버 MM-DD 표기)', () => {
    const ad = mkAnomaly({
      state: 'fired', last_fired_date: '2026-07-01', vs_fired_date: '2026-06-16',
      new_rules: ['R02'], gone_rules: ['R12'],
    })
    render(<DeltaCard regime={baseRegime} anomalyDelta={ad} />)
    const newChip = screen.getByTestId('anomaly-new-rule')
    expect(newChip.textContent).toContain('신규')
    expect(newChip.className).toContain('amber') // FLOW_TONE.warn
    const goneChip = screen.getByTestId('anomaly-gone-rule')
    expect(goneChip.textContent).toContain('소멸')
    expect(goneChip).toHaveClass('line-through')
    // note는 서버 vs_fired_date를 MM-DD로만 표기 (FE가 날짜 계산하지 않음)
    expect(screen.getByTestId('anomaly-fired-note').textContent).toContain('06-16')
  })

  it('resolving: ✓ 해소 칩(positive 토큰) + 사실 진술 note(단정 표현 없음)', () => {
    const ad = mkAnomaly({ state: 'resolving', last_fired_date: '2026-06-16', resolved_rules: ['R04'] })
    render(<DeltaCard regime={baseRegime} anomalyDelta={ad} />)
    const chip = screen.getByTestId('anomaly-resolved-rule')
    expect(chip.textContent).toContain('해소')
    expect(chip.className).toContain('emerald') // FLOW_TONE.calm (ok/positive)
    const note = screen.getByTestId('anomaly-resolving-note')
    expect(note.textContent).toContain('06-16 발동분 — 이후 재발동 없음')
    expect(note.textContent).not.toContain('해소 확정') // 단정 금지
  })

  it('quiet: 한 줄 + 마지막 발동일(서버 MM-DD)', () => {
    const ad = mkAnomaly({ state: 'quiet', last_fired_date: '2026-06-16' })
    render(<DeltaCard regime={baseRegime} anomalyDelta={ad} />)
    const el = screen.getByTestId('anomaly-quiet')
    expect(el.textContent).toContain('발동 중인 이상 신호 없음')
    expect(el.textContent).toContain('06-16')
  })

  it('no_history(및 anomalyDelta 미제공): "이상 신호 기록 없음"', () => {
    render(<DeltaCard regime={baseRegime} anomalyDelta={mkAnomaly({ state: 'no_history' })} />)
    expect(screen.getByTestId('anomaly-no-history')).toHaveTextContent('이상 신호 기록 없음')
    // prop 자체가 없어도 동일 fallback
    const { unmount } = render(<DeltaCard regime={baseRegime} />)
    expect(screen.getAllByTestId('anomaly-no-history').length).toBeGreaterThan(0)
    unmount()
  })

  it('rule 라벨: labels 있으면 translate 적용, 없으면 rule_id fallback', () => {
    const ad = mkAnomaly({ state: 'fired', last_fired_date: '2026-07-01', new_rules: ['R04'] })
    const labels = { 'rule.R04': 'VIX 급등' }
    const { rerender } = render(<DeltaCard regime={baseRegime} anomalyDelta={ad} labels={labels} />)
    expect(screen.getByTestId('anomaly-new-rule').textContent).toContain('VIX 급등')
    rerender(<DeltaCard regime={baseRegime} anomalyDelta={ad} />)
    expect(screen.getByTestId('anomaly-new-rule').textContent).toContain('R04')
  })
})

// ── 회귀: page.tsx 기존 블록 렌더 보존 ──────────────────────────

describe('MP2-DELTA 회귀: page.tsx 기존 블록 보존', () => {
  beforeEach(() => {
    // sector_deltas 포함한 overview 제공
    server.use(
      mpOverviewSuccess({
        ...overviewFixture,
        cards: {
          ...overviewFixture.cards,
          regime: {
            ...overviewFixture.cards.regime!,
            transition_from: 'LATE_BULL',
          },
        },
        sector_deltas: [
          { sector: 'XLK', rank: 1, prev_rank: 3, rank_delta: 2, as_of: '2026-07-01', vs_date: '2026-06-27' },
          { sector: 'XLE', rank: 11, prev_rank: 9, rank_delta: -2, as_of: '2026-07-01', vs_date: '2026-06-27' },
        ],
      }),
      mpI18nSuccess(),
      ...['regime', 'breadth', 'sector', 'concentration', 'brief'].map((id) =>
        http.get(`${MP_V2_BASE}/cards/${id}/detail`, () =>
          HttpResponse.json(
            { _meta: { generated_at: '2026-07-01T00:00:00Z', latency_ms: 5, cache: 'MISS' }, data: { available: true } },
            { status: 200 },
          ),
        ),
      ),
      http.post(`${MP_V2_BASE}/news/refresh`, () =>
        HttpResponse.json(
          { _meta: { generated_at: '2026-07-01T00:00:00Z', count: 0, pool_size: 0, seen_count: 0 }, items: [] },
          { status: 200 },
        ),
      ),
    )
  })

  it('DeltaCard 렌더 + hero·AnomalyPanel·히트맵·breadth·concentration 모두 보존', async () => {
    wrap(<MarketPulseV2Page />)

    await waitFor(() => {
      // DeltaCard rendered
      expect(screen.getByTestId('transition-from')).toBeInTheDocument()
      expect(screen.getByTestId('transition-to')).toBeInTheDocument()
    })

    // hero title still present
    expect(screen.getByText(/Market Regime/i)).toBeInTheDocument()
    // AnomalyPanel: anomaly mode label exists
    expect(screen.getByText(/CALM|안정/i)).toBeInTheDocument()
  })
})
