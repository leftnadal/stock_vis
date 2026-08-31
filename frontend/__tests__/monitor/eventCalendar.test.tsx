// 이벤트 캘린더 페이지 (EVT-IMPL-4 STEP 3) — 렌더 · 유형/범위 필터 · stale 기본 숨김 ·
// session 뱃지(값 있을 때만) · 휴장 행 · 서프라이즈 부호(beat/miss).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { EventFeed, EventItem } from '@/types/eventCalendar'

vi.mock('@/components/auth/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

const getCalendar = vi.fn()
vi.mock('@/services/eventCalendarService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/eventCalendarService')>()
  return {
    ...actual,
    eventCalendarService: {
      ...actual.eventCalendarService,
      getCalendar: (...a: unknown[]) => getCalendar(...a),
    },
  }
})

import EventCalendarPage from '@/app/monitor/calendar/page'

function item(overrides: Partial<EventItem>): EventItem {
  return {
    kind: 'macro',
    symbol: null,
    title: '거시 지표',
    event_date_et: '2026-09-11',
    event_time_et: null,
    session: null,
    event_dt_kst: null,
    d_day: 11,
    badges: [],
    detail: {},
    surprise: null,
    date_trust: null,
    date_observed_count: null,
    sources: [],
    status: 'scheduled',
    ...overrides,
  }
}

function makeFeed(items: EventItem[]): EventFeed {
  return {
    as_of: '2026-08-31T17:45:00-04:00',
    start: '2026-08-24',
    end: '2026-11-29',
    scope: 'monitor',
    symbols: { monitor: ['AVGO', 'AAPL'], watchlist: ['TSM'] },
    counts: { earnings: 4, dividend: 0, split: 0, split_effective: 0, macro: 1, holiday: 1 },
    items,
  }
}

const HOLIDAY = item({
  kind: 'holiday',
  title: 'NYSE 휴장',
  event_date_et: '2026-09-01',
  d_day: 1,
  detail: { name: null, next_trading_day: '2026-09-02' },
})

const MACRO_CRITICAL = item({
  kind: 'macro',
  title: 'CPI (8월)',
  event_date_et: '2026-09-11',
  d_day: 11,
  badges: ['critical'],
  detail: { importance: 'critical', forecast_value: '2.9%', previous_value: '2.7%', actual_value: null, country: 'US' },
})

const EARNINGS_WITH_SESSION = item({
  kind: 'earnings',
  symbol: 'AVGO',
  title: 'AVGO 어닝',
  event_date_et: '2026-09-04',
  d_day: 4,
  session: 'AMC',
  event_dt_kst: '2026-09-05T05:30:00+09:00',
  date_trust: 'stable',
  date_observed_count: 6,
  sources: ['monitor'],
  detail: { eps_estimated: 1.66, eps_actual: null, revenue_estimated: 15_800_000_000, revenue_actual: null },
})

const EARNINGS_NO_SESSION = item({
  kind: 'earnings',
  symbol: 'ADTX',
  title: 'ADTX 어닝',
  event_date_et: '2026-09-02',
  d_day: 2,
  session: null,
  date_trust: 'fluid',
  date_observed_count: 2,
  sources: ['monitor'],
  detail: { eps_estimated: null, eps_actual: null, revenue_estimated: 1_200_000, revenue_actual: null },
})

const EARNINGS_BEAT = item({
  kind: 'earnings',
  symbol: 'NVDA',
  title: 'NVDA 어닝',
  event_date_et: '2026-08-27',
  d_day: -4,
  status: 'occurred',
  sources: ['monitor'],
  surprise: { pct: 7.1, direction: 'beat' },
  detail: { eps_estimated: 0.98, eps_actual: 1.05, revenue_estimated: 45_900_000_000, revenue_actual: 46_700_000_000 },
})

const EARNINGS_MISS = item({
  kind: 'earnings',
  symbol: 'CRM',
  title: 'CRM 어닝',
  event_date_et: '2026-08-27',
  d_day: -4,
  status: 'occurred',
  sources: ['monitor'],
  surprise: { pct: -2.5, direction: 'miss' },
  detail: { eps_estimated: 2.78, eps_actual: 2.71, revenue_estimated: null, revenue_actual: null },
})

const STALE_EARNINGS = item({
  kind: 'earnings',
  symbol: 'ORCL',
  title: 'ORCL 어닝',
  event_date_et: '2026-09-11',
  d_day: 11,
  status: 'stale',
  date_trust: 'unconfirmed',
  sources: ['monitor'],
})

const ALL_ITEMS = [
  HOLIDAY,
  MACRO_CRITICAL,
  EARNINGS_WITH_SESSION,
  EARNINGS_NO_SESSION,
  EARNINGS_BEAT,
  EARNINGS_MISS,
  STALE_EARNINGS,
]

beforeEach(() => {
  getCalendar.mockReset()
  getCalendar.mockResolvedValue(makeFeed(ALL_ITEMS))
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <EventCalendarPage />
    </QueryClientProvider>,
  )
}

describe('EventCalendarPage', () => {
  it('렌더: 헤더·과거 발표·날짜 그룹이 보인다', async () => {
    renderPage()
    await screen.findByTestId('event-row-earnings-NVDA')
    // scope=monitor 기본 → symbols.monitor=[AVGO,AAPL] → 2.
    expect(screen.getByTestId('calendar-header-sub')).toHaveTextContent('관심종목 2')
    expect(screen.getByText('지난 7일 발표됨')).toBeInTheDocument()
    expect(screen.getByTestId('date-group-2026-09-04')).toBeInTheDocument()
  })

  it('유형 필터: "어닝" 칩 클릭 시 휴장/거시 행이 사라진다', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByTestId('event-row-holiday-na')).toBeInTheDocument())

    fireEvent.click(screen.getByTestId('kind-chip-earnings'))

    expect(screen.queryByTestId('event-row-holiday-na')).not.toBeInTheDocument()
    expect(screen.queryByTestId('event-row-macro-na')).not.toBeInTheDocument()
    expect(screen.getByTestId('event-row-earnings-AVGO')).toBeInTheDocument()
  })

  it('범위 칩: 클릭 시 새 scope로 재조회한다', async () => {
    renderPage()
    await screen.findByTestId('scope-chip-watchlist')
    expect(getCalendar).toHaveBeenCalledWith({ scope: 'monitor' })

    fireEvent.click(screen.getByTestId('scope-chip-watchlist'))

    await waitFor(() => expect(getCalendar).toHaveBeenCalledWith({ scope: 'watchlist' }))
  })

  it('stale 행은 기본 숨김이며, 토글을 켜면 나타난다', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByTestId('event-row-earnings-AVGO')).toBeInTheDocument())
    expect(screen.queryByTestId('event-row-earnings-ORCL')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('stale-toggle'))

    await waitFor(() => expect(screen.getByTestId('event-row-earnings-ORCL')).toBeInTheDocument())
  })

  it('session null이면 b-ses 뱃지를 렌더하지 않고, 값이 있으면 렌더한다', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByTestId('event-row-earnings-AVGO')).toBeInTheDocument())

    const withSession = screen.getByTestId('event-row-earnings-AVGO')
    expect(within(withSession).getByTestId('session-badge')).toHaveTextContent('AMC')

    const noSession = screen.getByTestId('event-row-earnings-ADTX')
    expect(within(noSession).queryByTestId('session-badge')).not.toBeInTheDocument()
  })

  it('휴장 행이 렌더되고 다음 거래일 안내를 포함한다', async () => {
    renderPage()
    const row = await screen.findByTestId('event-row-holiday-na')
    expect(within(row).getByTestId('kind-badge-holiday')).toBeInTheDocument()
    expect(within(row).getByText(/다음 거래일/)).toBeInTheDocument()
  })

  it('서프라이즈 부호(beat/miss)를 뱃지로 렌더한다', async () => {
    renderPage()
    const beatRow = await screen.findByTestId('event-row-earnings-NVDA')
    expect(within(beatRow).getByTestId('surprise-badge-beat')).toHaveTextContent('beat')

    const missRow = screen.getByTestId('event-row-earnings-CRM')
    expect(within(missRow).getByTestId('surprise-badge-miss')).toHaveTextContent('miss')
  })
})
