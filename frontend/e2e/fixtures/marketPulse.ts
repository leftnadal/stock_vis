/**
 * P2-DLITE — Playwright E2E용 market-pulse-v2 API 모킹 픽스처.
 *
 * 자체 완결(msw·@ alias 미의존) — Playwright route interception으로 백엔드/인증/공유DB
 * 없이 결정론적으로 페이지를 렌더한다. 응답 형태는 `@/lib/api/marketPulseV2`의 생성
 * 타입(OverviewResponse / CardDetailEnvelope / I18nResponse)에 부합.
 */
import type { Page, Route } from '@playwright/test'

export const overviewFixture = {
  _meta: {
    status: 'OK',
    status_reason: '',
    generated_at: '2026-06-11T00:00:00Z',
    latency_ms: 12,
    data_finalized: true,
    cache: 'MISS',
  },
  ticker_bar: [
    { symbol: 'SPY', last_close: 540.12, change_pct: 0.42, sector_group: 'BENCHMARK' },
    { symbol: 'QQQ', last_close: 470.55, change_pct: -0.31, sector_group: 'BENCHMARK' },
  ],
  news: [
    {
      id: 1,
      category: 'MACRO',
      title: 'CPI 둔화로 금리 인하 기대',
      summary: '5월 CPI가 예상치를 하회했다.',
      url: 'https://example.com/news/1',
      publisher: 'Reuters',
      published_at: '2026-06-10T13:00:00Z',
      matched_symbols: ['SPY'],
    },
  ],
  anomaly: {
    mode: 'CALM',
    overview: '특이 신호 없음',
    sector_highlight: '기술주 상대 강세',
    portfolio_action: '관망',
    fired: [],
  },
  sector_deltas: [],
  anomaly_delta: null,
  translations: null,
  cards: {
    regime: {
      regime: 'BULL_EXPANSION',
      status: 'OK',
      coverage: 0.92,
      headline: '확장 국면 지속',
      fired_rules: ['R1'],
      transitioned: false,
    },
    breadth: {
      universe: 'SPY',
      advance: 320,
      decline: 160,
      unchanged: 20,
      total: 500,
      new_high_52w: 42,
      new_low_52w: 8,
      ad_line: 1234,
      ad_line_change: 56,
    },
    sector: {
      leaders: [{ symbol: 'XLK', rel_strength: 1.23, rank: 1, momentum_1d: 0.8 }],
      laggards: [{ symbol: 'XLE', rel_strength: -0.95, rank: 11, momentum_1d: -0.6 }],
      cross_dispersion: 0.314,
      rotation_index: 0.072,
    },
    concentration: {
      universe: 'SPY',
      top5_weight: 0.28,
      top10_weight: 0.41,
      hhi: 0.0521,
      top_holdings: [
        { symbol: 'AAPL', weight: 0.071 },
        { symbol: 'MSFT', weight: 0.068 },
      ],
    },
    brief: {
      headline: '시장 요약',
      content_preview: '오늘 시장은 완만한 상승세를 보였다.',
      status: 'OK',
      model_version: 'gemini-2.5-flash',
    },
  },
}

export const i18nFixture = {
  _meta: { locale: 'ko', supported: ['ko', 'en'], cache: 'MISS' },
  labels: {
    'card.regime': 'Market Regime',
    'card.concentration': 'Concentration',
    'regime.BULL_EXPANSION': '강세 확장',
    'mode.CALM': '안정',
    'status.OK': '정상',
  },
}

const META = { generated_at: '2026-06-11T00:00:00Z', latency_ms: 5, cache: 'MISS' }

export const cardDetailFixtures: Record<string, Record<string, unknown>> = {
  regime: { available: true, date: '2026-06-11', regime: 'BULL_EXPANSION', status: 'OK', coverage: 0.92, fired_rules: ['R1'], headline: '확장 국면 지속', is_finalized: true },
  breadth: { available: true, universe: 'SPY', date: '2026-06-11', advance: 320, decline: 160, ad_line: 1234, ad_line_change: 56, history_30d: [] },
  sector: { available: true, date: '2026-06-11', sectors: [], cross_dispersion: 0.314, rotation_index: 0.072 },
  concentration: { available: true, date: '2026-06-11', universe: 'SPY', top5_weight: 0.28, top10_weight: 0.41, hhi: 0.0521, top_holdings: [{ symbol: 'AAPL', weight: 0.071 }], history_30d: [] },
  brief: { available: true, date: '2026-06-11', model_version: 'gemini-2.5-flash', status: 'OK', headline: '시장 요약', content: '오늘 시장은 완만한 상승세를 보였다.' },
}

// hero 배지 + StressCard가 available시 접근하는 필드 전부 포함(크래시 방지).
export const stressFixture = {
  available: true,
  as_of: '2026-06-11',
  score: 42,
  level_band: 'caution',
  percentile: { value: 58, window_days: 756 },
  direction: {
    stress: { d5: 3.2, d20: -1.1, state: 'rising' },
    price: { vs_ma20: 'above', vs_ma60: 'above', state: 'up' },
  },
  categories: [],
  meta: { population: 500 },
}

// analog은 unavailable 경로(analog-unavailable)로 안전 렌더(딥필드 미접근).
export const analogFixture = {
  available: false,
  as_of: '2026-06-11',
  today_axes: [],
  today_category: null,
  neighbors: [],
  fan: [],
  alert: { on: false, nearest_dist: null },
}

export const playbookFixture = {
  chains: [
    { id: 'risk_off', name: '위험회피', narrative: '위험회피 국면', cadence: 'daily', lit_count: 1, total: 3, state: 'partial', data_as_of: '2026-06-11' },
  ],
  summary: { total: 1, total_lit: 1, top_chain: { id: 'risk_off', name: '위험회피' } },
}

const json = (route: Route, obj: unknown, status = 200) =>
  route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(obj) })

interface MockOpts {
  /** overview 응답 코드 — 429/500 등 에러 경로 시뮬레이션. 기본 200. */
  overviewStatus?: number
  /** 요청 관측 콜백(경로·상태) — 429 스모크 카운팅용. */
  onApiRequest?: (pathname: string) => void
}

/**
 * `**​/api/**` 전량 인터셉트. market-pulse 엔드포인트는 픽스처, 그 외 /api는 benign 200
 * (jwt/verify·telemetry 등 부수 호출의 ECONNREFUSED 콘솔 노이즈 차단).
 */
export async function mockMarketPulse(page: Page, opts: MockOpts = {}): Promise<void> {
  const { overviewStatus = 200, onApiRequest } = opts
  await page.route('**/api/**', (route) => {
    const p = new URL(route.request().url()).pathname
    onApiRequest?.(p)
    if (p.endsWith('/market-pulse/overview')) {
      return overviewStatus === 200
        ? json(route, overviewFixture)
        : json(route, { detail: 'throttled' }, overviewStatus)
    }
    if (p.endsWith('/market-pulse/i18n')) return json(route, i18nFixture)
    if (p.endsWith('/regime/stress')) return json(route, { _meta: META, data: stressFixture })
    if (p.endsWith('/regime/analog')) return json(route, { _meta: META, data: analogFixture })
    if (p.endsWith('/market-pulse/playbook')) return json(route, { _meta: META, data: playbookFixture })
    const cd = p.match(/\/cards\/([^/]+)\/detail$/)
    if (cd) return json(route, { _meta: META, data: cardDetailFixtures[cd[1]] ?? { available: false } })
    // 그 외 /api (부수 호출) — benign 빈 응답
    return json(route, {})
  })
}
