// 관계망 이벤트 컴포넌트 (EVT-CHAIN-1/1B) — RelationBadge 라벨 · 상단 밴드(pill·앵커) ·
// 타임라인 이웃 0 비표시 · 접힘 카운트 · 부호 중립(방향 색상 클래스 부재).
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { ChainTimeline } from '@/components/monitor/chain/ChainTimeline'
import { RelationBadge } from '@/components/monitor/chain/RelationBadge'
import type { ChainEventItem, ChainFeed } from '@/types/chainFeed'
import type { EventItem } from '@/types/eventCalendar'

// 밴드는 useChainFeed를 직접 호출 → mock으로 제어(ChainTimeline/RelationBadge는 미사용).
const useChainFeedMock = vi.fn()
vi.mock('@/hooks/useEventCalendar', () => ({
  useChainFeed: () => useChainFeedMock(),
}))
// 밴드는 mock 이후 import(호이스팅 안전).
import { UpcomingEventsBand } from '@/components/monitor/chain/UpcomingEventsBand'

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
  return {
    ...evt({}),
    relation: { type: 'SUPPLIES_TO', truth_score: 0.93, role: 'supplier' },
    ...overrides,
  }
}

function feed(overrides: Partial<ChainFeed>): ChainFeed {
  return {
    seed: 'IREN',
    as_of: '2026-09-03T00:00:00-04:00',
    seed_events: [],
    seed_next_event: { kind: 'earnings', event_date_et: '2026-11-04', d_day: 62 },
    seed_earnings_event: { kind: 'earnings', event_date_et: '2026-11-04', d_day: 62 },
    window_end: '2026-11-04',
    neighbors: [{ symbol: 'NBR', relation_type: 'SUPPLIES_TO', truth_score: 0.93, role: 'supplier' }],
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

  it('CHAIN-1a: 역할(방향성 도출) 우선 — supplier=공급사·customer=고객', () => {
    const { rerender } = render(
      <RelationBadge relationType="SUPPLIES_TO" truthScore={0.9} role="supplier" />,
    )
    expect(screen.getByTestId('relation-badge-SUPPLIES_TO')).toHaveTextContent('공급사')
    rerender(<RelationBadge relationType="SUPPLIES_TO" truthScore={0.9} role="customer" />)
    expect(screen.getByTestId('relation-badge-SUPPLIES_TO')).toHaveTextContent('고객')
  })

  it('CHAIN-1a: role=null → 관계 유형 중립 라벨 폴백', () => {
    render(<RelationBadge relationType="SUPPLIES_TO" truthScore={0.9} role={null} />)
    expect(screen.getByTestId('relation-badge-SUPPLIES_TO')).toHaveTextContent('공급망')
  })
})

describe('UpcomingEventsBand (EVT-CHAIN-1B)', () => {
  beforeEach(() => useChainFeedMock.mockReset())

  it('이벤트 없음(어닝·배당·이웃 전무) → 밴드 비표시', () => {
    useChainFeedMock.mockReturnValue({
      data: feed({ seed_events: [], neighbors: [], items: [] }),
      isError: false,
    })
    const { container } = render(<UpcomingEventsBand symbol="IREN" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('어닝 pill + 관계망 N pill 렌더', () => {
    useChainFeedMock.mockReturnValue({
      data: feed({ seed_events: [evt({ symbol: 'IREN', d_day: 63 })] }),
      isError: false,
    })
    render(<UpcomingEventsBand symbol="IREN" />)
    expect(screen.getByTestId('upcoming-band')).toBeInTheDocument()
    expect(screen.getByTestId('band-earnings-pill')).toHaveTextContent('D-63')
    expect(screen.getByTestId('chain-anchor-pill')).toHaveTextContent('관계망 1')
  })

  it('관계망 pill 클릭 → 하단 타임라인 앵커로 스크롤', () => {
    useChainFeedMock.mockReturnValue({ data: feed({}), isError: false })
    const scrollSpy = vi.fn()
    const getByIdSpy = vi
      .spyOn(document, 'getElementById')
      .mockReturnValue({ scrollIntoView: scrollSpy } as unknown as HTMLElement)
    render(<UpcomingEventsBand symbol="IREN" />)
    fireEvent.click(screen.getByTestId('chain-anchor-pill'))
    expect(getByIdSpy).toHaveBeenCalledWith('chain-timeline')
    expect(scrollSpy).toHaveBeenCalled()
    getByIdSpy.mockRestore()
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
