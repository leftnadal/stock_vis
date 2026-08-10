// 일지 계약 (MON-DETAIL-P1 T2 + MON-P4-LA T3): buildJournal 정렬·delta·advisor +
// kind 레지스트리 전방 호환 + AdvisorEntry 펼침(D3, 사용자 조작 > 자동).
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { JournalFeed } from '@/components/monitor/journal/JournalFeed'
import { buildJournal, type AdvisorPayload, type JournalEntry } from '@/lib/monitor/journal'
import type { AdvisorNote, AlertEvent, Claim, Monitor, SnapshotSeriesResponse } from '@/types/monitor'

beforeEach(() => {
  window.localStorage.clear()
})

const monitor = {
  id: 'm1',
  name: '애플',
  scope: 'stock',
  created_at: '2026-07-01T00:00:00Z',
} as unknown as Monitor

const snapshots: SnapshotSeriesResponse = {
  series: [
    { asof: '2026-08-01', score: 0.1, delta: null },
    { asof: '2026-08-02', score: 0.25, delta: 0.15 },
  ],
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

// BE 응답 = 최신순(order_by('-asof')) — 0번째가 최신.
const advisorNotes: AdvisorNote[] = [
  {
    id: 'n2',
    asof: '2026-08-05',
    surface: 'L-A',
    headline: '오늘도 강세 흐름 유지',
    body: '거래량비·모멘텀 지표가 함께 개선되며 추세가 이어지고 있어요.',
    coverage_n: 5,
    coverage_total: 6,
    model_id: 'gemini-2.5-flash',
    prompt_version: 'v1',
    created_at: '2026-08-05T22:00:00Z',
  },
  {
    id: 'n1',
    asof: '2026-08-03',
    surface: 'L-A',
    headline: '변동성 확대 구간 진입',
    body: '단기 변동성이 커지며 손절 여유가 줄었어요.',
    coverage_n: 4,
    coverage_total: 6,
    model_id: 'gemini-2.5-flash',
    prompt_version: 'v1',
    created_at: '2026-08-03T22:00:00Z',
  },
]

describe('buildJournal', () => {
  it('asof desc 정렬 · 동일 asof는 transition>snapshot · open 최하단', () => {
    const j = buildJournal({ snapshots, alerts, monitor, claims: [claim] })
    // 08-02 transition, 08-02 snapshot, 08-01 snapshot, open(07-01)
    expect(j.map((e) => e.kind)).toEqual(['transition', 'snapshot', 'snapshot', 'open'])
    expect(j[j.length - 1].kind).toBe('open') // open 항상 최하단
  })

  it('snapshot delta = snapshots.series의 BE 계산값 그대로(재계산 금지, 첫 점 null)', () => {
    const j = buildJournal({ snapshots, alerts: [], monitor, claims: [] })
    const snaps = j.filter((e) => e.kind === 'snapshot')
    // desc 정렬이라 [08-02(delta +0.15), 08-01(delta null)]
    expect((snaps[0].payload as { delta: number | null }).delta).toBeCloseTo(0.15, 4)
    expect((snaps[1].payload as { delta: number | null }).delta).toBeNull()
  })

  it('delta=0(±0 변화)도 유효값으로 통과시킨다(무표시 금지)', () => {
    const zeroDeltaSnapshots: SnapshotSeriesResponse = {
      series: [
        { asof: '2026-08-01', score: 0.1, delta: null },
        { asof: '2026-08-02', score: 0.1, delta: 0 },
      ],
      window: 30,
    }
    const j = buildJournal({ snapshots: zeroDeltaSnapshots, alerts: [], monitor, claims: [] })
    const latest = j.find((e) => e.kind === 'snapshot' && e.asof === '2026-08-02')!
    expect((latest.payload as { delta: number | null }).delta).toBe(0)
  })

  it('open payload는 첫 claim 사전 커밋 요약(hold=매입 앵커)', () => {
    const j = buildJournal({ snapshots: null, alerts: [], monitor, claims: [claim] })
    const open = j.find((e) => e.kind === 'open')!
    expect((open.payload as { scenario_type: string }).scenario_type).toBe('hold')
    expect((open.payload as { purchase_price: string }).purchase_price).toBe('100')
  })

  it('advisor ← advisor_notes(BE 최신순) — 0번째 원소만 is_latest=true', () => {
    const j = buildJournal({ snapshots: null, alerts: [], monitor, claims: [], advisorNotes })
    const advisorEntries = j.filter((e) => e.kind === 'advisor')
    expect(advisorEntries).toHaveLength(2)
    const byId = new Map(
      advisorEntries.map((e) => [(e.payload as AdvisorPayload).id, e.payload as AdvisorPayload])
    )
    expect(byId.get('n2')!.is_latest).toBe(true) // BE 배열 0번째(최신)
    expect(byId.get('n1')!.is_latest).toBe(false)
    expect(byId.get('n2')!.headline).toBe('오늘도 강세 흐름 유지')
    expect(byId.get('n2')!.asof).toBe('2026-08-05')
  })

  it('동일 asof에서 transition > snapshot > advisor 순서(advisor는 뒤)', () => {
    const sameDaySnapshots: SnapshotSeriesResponse = {
      series: [{ asof: '2026-08-05', score: 0.2, delta: 0.05 }],
      window: 30,
    }
    const sameDayAlerts: AlertEvent[] = [
      { ...alerts[0], asof: '2026-08-05' },
    ]
    const j = buildJournal({
      snapshots: sameDaySnapshots,
      alerts: sameDayAlerts,
      monitor,
      claims: [],
      advisorNotes: [advisorNotes[0]], // asof=2026-08-05
    })
    const sameDay = j.filter((e) => e.asof === '2026-08-05')
    expect(sameDay.map((e) => e.kind)).toEqual(['transition', 'snapshot', 'advisor'])
  })
})

describe('JournalFeed 전방 호환', () => {
  it('예약/미등록 kind(theme·memo)는 안전 무시 — advisor는 P4-LA 구현 완료로 정상 렌더', () => {
    const entries: JournalEntry[] = [
      {
        kind: 'advisor',
        asof: '2026-08-03',
        payload: {
          id: 'n1',
          headline: '변동성 확대 구간 진입',
          body: '단기 변동성이 커지며 손절 여유가 줄었어요.',
          coverage_n: 4,
          coverage_total: 6,
          model_id: 'gemini-2.5-flash',
          asof: '2026-08-03',
          is_latest: false,
        } satisfies AdvisorPayload,
      },
      { kind: 'theme', asof: '2026-08-03', payload: {} },
      { kind: 'memo', asof: '2026-08-03', payload: {} },
      { kind: 'transition', asof: '2026-08-02', payload: { from_label: '활성', to_label: '강화', is_deterioration: false, is_suppressed: false } },
    ]
    render(<JournalFeed entries={entries} />)
    // 등록된 transition·advisor만 렌더, 예약 kind(theme·memo)는 없음
    expect(screen.getByTestId('journal-entry-transition')).toBeInTheDocument()
    expect(screen.getByTestId('journal-entry-advisor')).toBeInTheDocument()
    expect(screen.queryByTestId('journal-entry-theme')).not.toBeInTheDocument()
    expect(screen.queryByTestId('journal-entry-memo')).not.toBeInTheDocument()
  })

  it('등록 kind가 하나도 없으면 빈 상태 안내', () => {
    render(<JournalFeed entries={[{ kind: 'theme', asof: '2026-08-03', payload: {} }]} />)
    expect(screen.getByTestId('journal-empty')).toBeInTheDocument()
  })
})

describe('AdvisorEntry (MON-P4-LA T3) — 배지·headline·펼침(D3)', () => {
  function advisorEntry(overrides: Partial<AdvisorPayload> = {}): JournalEntry {
    return {
      kind: 'advisor',
      asof: '2026-08-05',
      payload: {
        id: 'n2',
        headline: '오늘도 강세 흐름 유지',
        body: '거래량비·모멘텀 지표가 함께 개선되며 추세가 이어지고 있어요.',
        coverage_n: 5,
        coverage_total: 6,
        model_id: 'gemini-2.5-flash',
        asof: '2026-08-05',
        is_latest: false,
        ...overrides,
      } satisfies AdvisorPayload,
    }
  }

  it('행 = 보라 배지 "비서" + headline 1줄(기본 접힘 — body 미표시)', () => {
    render(<JournalFeed entries={[advisorEntry({ is_latest: false })]} />)
    expect(screen.getByTestId('journal-advisor')).toHaveTextContent('비서')
    expect(screen.getByTestId('journal-advisor')).toHaveTextContent('오늘도 강세 흐름 유지')
    expect(screen.queryByTestId('journal-advisor-body')).not.toBeInTheDocument()
  })

  it('D3: 최신 1건(is_latest=true)만 자동 펼침 — 나머지는 접힘', () => {
    render(
      <JournalFeed
        entries={[
          advisorEntry({ id: 'latest', is_latest: true }),
          advisorEntry({ id: 'older', is_latest: false, asof: '2026-08-03' }),
        ]}
      />
    )
    const bodies = screen.getAllByTestId('journal-advisor-body')
    expect(bodies).toHaveLength(1) // 최신 1건만 펼침
  })

  it('클릭 시 펼침 + body/meta 표기(근거 지표 n/total · MonitorSnapshot asof · model_id)', () => {
    render(<JournalFeed entries={[advisorEntry({ is_latest: false })]} />)
    expect(screen.queryByTestId('journal-advisor-body')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('journal-advisor').querySelector('button')!)
    expect(screen.getByTestId('journal-advisor-body')).toBeInTheDocument()
    expect(screen.getByTestId('journal-advisor-meta')).toHaveTextContent(
      '근거 지표 5/6 · MonitorSnapshot 2026-08-05 · gemini-2.5-flash'
    )
    expect(window.localStorage.getItem('monitor-detail:journal:advisor:n2')).toBe('1')
  })

  it('사용자 조작 > 자동 — 최신 1건을 사용자가 명시적으로 접으면 재마운트해도 접힘 유지', () => {
    const { unmount } = render(<JournalFeed entries={[advisorEntry({ is_latest: true })]} />)
    // 자동 펼침 확인 후 사용자가 명시적으로 접음
    expect(screen.getByTestId('journal-advisor-body')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('journal-advisor').querySelector('button')!)
    expect(screen.queryByTestId('journal-advisor-body')).not.toBeInTheDocument()
    expect(window.localStorage.getItem('monitor-detail:journal:advisor:n2')).toBe('0')
    unmount()

    // 재마운트(새로고침 복원 시뮬레이션) — is_latest=true라도 사용자의 명시적 접힘이 자동 펼침을 이긴다
    render(<JournalFeed entries={[advisorEntry({ is_latest: true })]} />)
    expect(screen.queryByTestId('journal-advisor-body')).not.toBeInTheDocument()
  })
})
