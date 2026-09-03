// 관계망 이벤트 컴포넌트 (EVT-CHAIN-1 STEP 3) — RelationBadge 라벨 매핑 · 위젯 빈/pill 상태 ·
// 타임라인 이웃 0 비표시 · 접힘 카운트 · 부호 중립(방향 색상 클래스 부재).
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ChainTimeline } from '@/components/monitor/chain/ChainTimeline'
import { RelationBadge } from '@/components/monitor/chain/RelationBadge'
import { UpcomingEventsWidget } from '@/components/monitor/chain/UpcomingEventsWidget'
import type { ChainEventItem, ChainFeed } from '@/types/chainFeed'
import type { EventItem } from '@/types/eventCalendar'

function evt(overrides: Partial<EventItem>): EventItem {
  return {
    kind: 'earnings',
    symbol: 'NBR',
    title: 'NBR 어닝',
    event_date_et: '2026-10-28',
    event_time_et: null,
    session: null,
    event_dt_kst: null,
    d_day: 55,
    badges: [],
    detail: { eps_estimated: 3.22, eps_actual: null, revenue_estimated: 75_500_000_000, revenue_actual: null },
    surprise: null,
    date_trust: 'stable',
    date_observed_count: 8,
    sources: [],
    status: 'scheduled',
    ...overrides,
  }
}

function chainItem(overrides: Partial<ChainEventItem>): ChainEventItem {
  return { ...evt({}), relation: { type: 'SUPPLIES_TO', truth_score: 0.93 }, ...overrides }
}

function feed(overrides: Partial<ChainFeed>): ChainFeed {
  return {
    seed: 'IREN',
    as_of: '2026-09-03T00:00:00-04:00',
    seed_events: [],
    seed_next_event: { kind: 'earnings', event_date_et: '2026-11-04', d_day: 62 },
    neighbors: [{ symbol: 'NBR', relation_type: 'SUPPLIES_TO', truth_score: 0.93 }],
    items: [chainItem({})],
    after_count: 0,
    params: {},
    ...overrides,
  }
}

describe('RelationBadge', () => {
  it('실측 choices → 중립 한글 라벨', () => {
    render(<RelationBadge relationType="SUPPLIES_TO" truthScore={0.93} />)
    expect(screen.getByTestId('relation-badge-SUPPLIES_TO')).toHaveTextContent('공급망')
    expect(screen.getByTestId('truth-badge')).toHaveTextContent('truth 93')
  })

  it('미지 유형 → 원문 코드(날조 금지)', () => {
    render(<RelationBadge relationType="MYSTERY_REL" truthScore={0.5} />)
    expect(screen.getByTestId('relation-badge-MYSTERY_REL')).toHaveTextContent('MYSTERY_REL')
  })
})

describe('UpcomingEventsWidget', () => {
  it('시드 이벤트 없음 → "예정 이벤트 없음"', () => {
    render(<UpcomingEventsWidget seedEvents={[]} />)
    expect(screen.getByTestId('widget-empty')).toHaveTextContent('예정 이벤트 없음')
  })

  it('시드 어닝 있음 → 어닝 pill', () => {
    render(<UpcomingEventsWidget seedEvents={[evt({ symbol: 'IREN', d_day: 63 })]} />)
    expect(screen.getByTestId('widget-earnings-pill')).toBeInTheDocument()
    expect(screen.getByTestId('widget-earnings-pill')).toHaveTextContent('D-63')
  })
})

describe('ChainTimeline', () => {
  it('이웃 0 → 섹션 자체 비표시(null)', () => {
    const { container } = render(<ChainTimeline feed={feed({ neighbors: [], items: [] })} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('이웃 있음 → 이웃 행 + 시드 행 렌더', () => {
    render(<ChainTimeline feed={feed({})} />)
    expect(screen.getByTestId('chain-timeline')).toBeInTheDocument()
    expect(screen.getAllByTestId('chain-row')).toHaveLength(1)
    expect(screen.getByTestId('chain-seed-row')).toHaveTextContent('IREN')
  })

  it('after_count > 0 → 접힘 카운트 표기', () => {
    render(<ChainTimeline feed={feed({ after_count: 4 })} />)
    expect(screen.getByTestId('chain-after-count')).toHaveTextContent('이후 4건 더')
  })

  it('부호 중립 — 방향(beat/miss) 색상 클래스 부재', () => {
    const { container } = render(<ChainTimeline feed={feed({})} />)
    const html = container.innerHTML
    // 서프라이즈 방향 색(beat=green-700 / miss=red-700)이 어디에도 없어야 한다.
    expect(html).not.toContain('text-green-700')
    expect(html).not.toContain('text-red-700')
  })
})
