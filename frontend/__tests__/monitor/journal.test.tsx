// 일지 계약 (MON-DETAIL-P1 T2): buildJournal 정렬·delta + kind 레지스트리 전방 호환.
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { JournalFeed } from '@/components/monitor/journal/JournalFeed'
import { buildJournal, type JournalEntry } from '@/lib/monitor/journal'
import type { AlertEvent, Claim, Monitor, SparklineResponse } from '@/types/monitor'

const monitor = {
  id: 'm1',
  name: '애플',
  scope: 'stock',
  created_at: '2026-07-01T00:00:00Z',
} as unknown as Monitor

const spark: SparklineResponse = {
  series: [
    { asof: '2026-08-01', score: 0.1 },
    { asof: '2026-08-02', score: 0.25 },
  ],
  bands: [],
  transitions: [],
  delta_5d: null,
  window: 30,
}

const alerts: AlertEvent[] = [
  {
    id: 'a1',
    monitor: 'm1',
    monitor_name: '애플',
    target_ref: 'AAPL',
    from_state: 'active',
    to_state: 'strengthening',
    from_label: '활성',
    to_label: '강화',
    asof: '2026-08-02',
    score: 0.3,
    is_deterioration: false,
    is_suppressed: false,
    read: false,
    created_at: '2026-08-02T22:45:00Z',
  },
]

const claim = {
  id: 'c1',
  monitor: 'm1',
  assertion: '보유 관리',
  scenario_type: 'hold',
  purchase_price: '100',
  target_price: '120',
  stop_price: '90',
  entry_price: null,
} as unknown as Claim

describe('buildJournal', () => {
  it('asof desc 정렬 · 동일 asof는 transition>snapshot · open 최하단', () => {
    const j = buildJournal({ sparkline: spark, alerts, monitor, claims: [claim] })
    // 08-02 transition, 08-02 snapshot, 08-01 snapshot, open(07-01)
    expect(j.map((e) => e.kind)).toEqual(['transition', 'snapshot', 'snapshot', 'open'])
    expect(j[j.length - 1].kind).toBe('open') // open 항상 최하단
  })

  it('snapshot delta = 직전 점 대비 (첫 점 null)', () => {
    const j = buildJournal({ sparkline: spark, alerts: [], monitor, claims: [] })
    const snaps = j.filter((e) => e.kind === 'snapshot')
    // desc 정렬이라 [08-02(delta +0.15), 08-01(delta null)]
    expect((snaps[0].payload as { delta: number | null }).delta).toBeCloseTo(0.15, 4)
    expect((snaps[1].payload as { delta: number | null }).delta).toBeNull()
  })

  it('open payload는 첫 claim 사전 커밋 요약(hold=매입 앵커)', () => {
    const j = buildJournal({ sparkline: null, alerts: [], monitor, claims: [claim] })
    const open = j.find((e) => e.kind === 'open')!
    expect((open.payload as { scenario_type: string }).scenario_type).toBe('hold')
    expect((open.payload as { purchase_price: string }).purchase_price).toBe('100')
  })
})

describe('JournalFeed 전방 호환', () => {
  it('예약/미등록 kind(advisor·theme·memo)는 안전 무시', () => {
    const entries: JournalEntry[] = [
      { kind: 'advisor', asof: '2026-08-03', payload: {} },
      { kind: 'theme', asof: '2026-08-03', payload: {} },
      { kind: 'memo', asof: '2026-08-03', payload: {} },
      { kind: 'transition', asof: '2026-08-02', payload: { from_label: '활성', to_label: '강화', is_deterioration: false, is_suppressed: false } },
    ]
    render(<JournalFeed entries={entries} />)
    // 등록된 transition만 렌더, 예약 kind는 없음
    expect(screen.getByTestId('journal-entry-transition')).toBeInTheDocument()
    expect(screen.queryByTestId('journal-entry-advisor')).not.toBeInTheDocument()
    expect(screen.queryByTestId('journal-entry-theme')).not.toBeInTheDocument()
    expect(screen.queryByTestId('journal-entry-memo')).not.toBeInTheDocument()
  })

  it('등록 kind가 하나도 없으면 빈 상태 안내', () => {
    render(<JournalFeed entries={[{ kind: 'advisor', asof: '2026-08-03', payload: {} }]} />)
    expect(screen.getByTestId('journal-empty')).toBeInTheDocument()
  })
})
