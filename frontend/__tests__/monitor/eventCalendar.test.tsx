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

// ── EVT-4B STEP2 (FE-TUNE-1 T2) — 거시 접기. docs/design/evt_tune1_options.html T2.
describe('EventCalendarPage — 거시 접기(T2)', () => {
  const MACRO_A = item({
    kind: 'macro',
    title: 'ISM 제조업 PMI',
    event_date_et: '2026-09-02',
    event_time_et: '10:00',
    event_dt_kst: '2026-09-02T23:00:00+09:00',
    d_day: 2,
    badges: ['critical'],
    detail: {
      importance: 'critical',
      forecast_value: '48.5',
      previous_value: '48.0',
      actual_value: null,
      country: 'US',
    },
  })

  const MACRO_B = item({
    kind: 'macro',
    title: '건설 지출',
    event_date_et: '2026-09-02',
    event_time_et: '10:00',
    d_day: 2,
    badges: ['medium'],
    detail: {
      importance: 'medium',
      forecast_value: '0.2%',
      previous_value: '0.1%',
      actual_value: null,
      country: 'US',
    },
  })

  const AAPL_DIV = item({
    kind: 'dividend',
    symbol: 'AAPL',
    title: 'AAPL 배당락',
    event_date_et: '2026-09-02',
    d_day: 2,
    sources: ['watchlist'],
    detail: { dividend_amount: 0.26, payment_date: '2026-09-15', record_date: null, frequency: '분기' },
  })

  const HOLIDAY_SEP = item({
    kind: 'holiday',
    title: 'NYSE 휴장',
    event_date_et: '2026-09-07',
    d_day: 7,
    detail: { name: 'Labor Day', next_trading_day: '2026-09-08' },
  })

  function foldFeed(extra: EventItem[] = []) {
    return makeFeed([AAPL_DIV, MACRO_A, MACRO_B, HOLIDAY_SEP, ...extra])
  }

  beforeEach(() => {
    getCalendar.mockReset()
  })

  it('거시는 기본 접힘이며 "거시 N건" + CRITICAL 미리보기를 보여준다', async () => {
    getCalendar.mockResolvedValue(foldFeed())
    renderPage()

    const fold = await screen.findByTestId('macro-fold-2026-09-02')
    expect(fold).toHaveTextContent('거시 2건')
    expect(fold).toHaveTextContent('CRITICAL')
    expect(fold).toHaveTextContent('ISM 제조업 PMI')
    // 비-CRITICAL(건설 지출)은 미리보기에 노출되지 않는다.
    expect(fold).not.toHaveTextContent('건설 지출')
    // 접힘 상태에서는 개별 거시 행이 렌더되지 않는다.
    expect(screen.queryByTestId('event-row-macro-na')).not.toBeInTheDocument()
  })

  it('접힘 행을 클릭하면 펼쳐져 개별 거시 행이 보인다', async () => {
    getCalendar.mockResolvedValue(foldFeed())
    renderPage()

    const fold = await screen.findByTestId('macro-fold-2026-09-02')
    fireEvent.click(fold)

    await waitFor(() => expect(screen.getAllByTestId('event-row-macro-na')).toHaveLength(2))
    expect(screen.queryByTestId('macro-fold-2026-09-02')).not.toBeInTheDocument()
  })

  it('유형 필터가 거시 단독이면 접지 않고 바로 펼쳐서 보여준다', async () => {
    getCalendar.mockResolvedValue(foldFeed())
    renderPage()

    await screen.findByTestId('macro-fold-2026-09-02')
    fireEvent.click(screen.getByTestId('kind-chip-macro'))

    await waitFor(() => expect(screen.getAllByTestId('event-row-macro-na')).toHaveLength(2))
    expect(screen.queryByTestId('macro-fold-2026-09-02')).not.toBeInTheDocument()
    // 거시 단독 필터에서는 전역 토글도 의미가 없으므로 숨긴다.
    expect(screen.queryByTestId('macro-toggle-all')).not.toBeInTheDocument()
  })

  it('관심종목(배당락)·휴장 행은 거시 접힘 상태와 무관하게 항상 렌더된다', async () => {
    getCalendar.mockResolvedValue(foldFeed())
    renderPage()

    await screen.findByTestId('macro-fold-2026-09-02')
    expect(screen.getByTestId('event-row-dividend-AAPL')).toBeInTheDocument()
    expect(screen.getByTestId('event-row-holiday-na')).toBeInTheDocument()
  })

  it('"거시 모두 펼치기" 토글이 모든 그룹을 일괄 펼치고/접는다', async () => {
    const MACRO_LATER = item({
      kind: 'macro',
      title: 'FOMC 성명',
      event_date_et: '2026-09-17',
      event_time_et: '14:00',
      d_day: 17,
      badges: ['critical'],
      detail: { importance: 'critical', forecast_value: null, previous_value: null, actual_value: null, country: 'US' },
    })
    getCalendar.mockResolvedValue(foldFeed([MACRO_LATER]))
    renderPage()

    await screen.findByTestId('macro-fold-2026-09-02')
    expect(screen.getByTestId('macro-fold-2026-09-17')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('macro-toggle-all'))

    await waitFor(() => expect(screen.getAllByTestId('event-row-macro-na')).toHaveLength(3))
    expect(screen.getByTestId('macro-toggle-all')).toHaveTextContent('거시 모두 접기')

    fireEvent.click(screen.getByTestId('macro-toggle-all'))

    await waitFor(() => {
      expect(screen.getByTestId('macro-fold-2026-09-02')).toBeInTheDocument()
      expect(screen.getByTestId('macro-fold-2026-09-17')).toBeInTheDocument()
    })
    expect(screen.getByTestId('macro-toggle-all')).toHaveTextContent('거시 모두 펼치기')
  })

  it('세션·시각이 모두 없는 어닝 행은 "세션 미정" 대신 빈 칸을 보여준다', async () => {
    const EARNINGS_NO_TIME = item({
      kind: 'earnings',
      symbol: 'ADTX',
      title: 'ADTX 어닝',
      event_date_et: '2026-09-02',
      d_day: 2,
      session: null,
      event_dt_kst: null,
      sources: ['monitor'],
      detail: { eps_estimated: null, eps_actual: null, revenue_estimated: null, revenue_actual: null },
    })
    getCalendar.mockResolvedValue(foldFeed([EARNINGS_NO_TIME]))
    renderPage()

    const row = await screen.findByTestId('event-row-earnings-ADTX')
    expect(row).not.toHaveTextContent('세션 미정')
  })
})

// ── EVT-4B STEP2 — "지난 7일 발표됨" 순서 + 실제값 미수신 문구 + 서프라이즈 200% 규칙.
describe('EventCalendarPage — 지난 7일 + 서프라이즈 규칙(T2)', () => {
  beforeEach(() => {
    getCalendar.mockReset()
  })

  it('지난 7일: watch 결과가 최근순으로 먼저, 거시는 뒤(접힘)에 온다', async () => {
    const RECENT = item({
      kind: 'earnings',
      symbol: 'NVDA',
      title: 'NVDA 어닝',
      event_date_et: '2026-08-29',
      d_day: -2,
      status: 'occurred',
      sources: ['monitor'],
      surprise: { pct: 7.1, direction: 'beat' },
      detail: { eps_estimated: 0.98, eps_actual: 1.05, revenue_estimated: null, revenue_actual: null },
    })
    const OLDER = item({
      kind: 'earnings',
      symbol: 'CRM',
      title: 'CRM 어닝',
      event_date_et: '2026-08-25',
      d_day: -6,
      status: 'occurred',
      sources: ['monitor'],
      surprise: { pct: -2.5, direction: 'miss' },
      detail: { eps_estimated: 2.78, eps_actual: 2.71, revenue_estimated: null, revenue_actual: null },
    })
    const MACRO_PAST_NO_ACTUAL = item({
      kind: 'macro',
      title: 'CPI (8월)',
      event_date_et: '2026-08-26',
      d_day: -5,
      status: 'occurred',
      badges: ['critical'],
      detail: { importance: 'critical', forecast_value: '2.9%', previous_value: '2.7%', actual_value: null, country: 'US' },
    })
    getCalendar.mockResolvedValue(makeFeed([OLDER, RECENT, MACRO_PAST_NO_ACTUAL]))
    renderPage()

    const pastSection = await screen.findByTestId('past-section')
    const order = within(pastSection)
      .getAllByTestId(/^(event-row-earnings-[A-Z]+|macro-fold-past)$/)
      .map((el) => el.getAttribute('data-testid'))

    expect(order).toEqual(['event-row-earnings-NVDA', 'event-row-earnings-CRM', 'macro-fold-past'])
    expect(screen.getByTestId('macro-fold-past')).toHaveTextContent('실제값 미수신 1건')
  })

  it('서프라이즈 |pct| > 200%는 뱃지가 beat/miss만 표기하고 상세는 실측값을 보여준다', async () => {
    const EXTREME_MISS = item({
      kind: 'earnings',
      symbol: 'IREN',
      title: 'IREN 어닝',
      event_date_et: '2026-08-27',
      d_day: -4,
      status: 'occurred',
      sources: ['monitor'],
      surprise: { pct: -243.6, direction: 'miss' },
      detail: { eps_estimated: -0.55, eps_actual: -1.89, revenue_estimated: null, revenue_actual: null },
    })
    getCalendar.mockResolvedValue(makeFeed([EXTREME_MISS]))
    renderPage()

    const row = await screen.findByTestId('event-row-earnings-IREN')
    const badge = within(row).getByTestId('surprise-badge-miss')
    expect(badge).toHaveTextContent('miss')
    expect(badge.textContent).not.toMatch(/%/)
    expect(row).toHaveTextContent(/EPS -1.89 vs 예상 -0.55/)
  })

  it('서프라이즈 |pct| ≤ 200%는 기존 "EPS N% miss" 표기를 유지한다', async () => {
    const NORMAL_MISS = item({
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
    getCalendar.mockResolvedValue(makeFeed([NORMAL_MISS]))
    renderPage()

    const row = await screen.findByTestId('event-row-earnings-CRM')
    expect(within(row).getByTestId('surprise-badge-miss')).toHaveTextContent('EPS -2.5% miss')
  })
})
