/**
 * MP-KL-F1 — Market Pulse v2 테스트 픽스처 + MSW 핸들러 팩토리.
 *
 * market-pulse-v2 프론트는 자체 axios 인스턴스(`MP_V2_BASE = /api/v2/market-pulse`)를
 * 쓰므로 coach handlers와 분리해 이 파일에서 도메인 전용 mock을 제공한다.
 *
 * ⚠️ 충실성: 200 응답은 `@/lib/api/marketPulseV2`의 생성 타입
 *   (`OverviewResponse` / `CardDetailEnvelope` / `I18nResponse`)에 타입상 부합해야 한다.
 *   page.tsx는 mount 시 overview + i18n 두 쿼리를 동시에 발사하므로
 *   page 렌더 테스트는 두 핸들러를 항상 등록해야 한다(onUnhandledRequest: 'error').
 */
import { http, HttpResponse, delay } from 'msw'

import {
  MP_V2_BASE,
  type OverviewResponse,
  type I18nResponse,
} from '@/lib/api/marketPulseV2'

// ── 픽스처 ──

export const overviewFixture: OverviewResponse = {
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

export const i18nFixture: I18nResponse = {
  _meta: { locale: 'ko', supported: ['ko', 'en'], cache: 'MISS' },
  // MP-UX-S1: status.* 추가 — StatusBanner가 하드코딩 COPY 대신 /i18n 단일소스(translate)를
  // 쓰도록 전환됨에 따라, mock도 실제 /i18n 응답(labels.py KO_LABELS)처럼 status 라벨을 제공.
  labels: {
    'card.regime': 'Market Regime',
    'card.concentration': 'Concentration',
    'regime.BULL_EXPANSION': '강세 확장',
    'mode.CALM': '안정',
    'status.INSUFFICIENT_DATA': '데이터 수집 부족',
    'status.STALE': '데이터 오래됨',
    'status.FAILED': '계산 실패',
    'status.MARKET_CLOSED': '장 마감',
  },
}

/** card detail 페이로드 — cardId별 최소 valid payload(available=true). */
export const cardDetailFixtures: Record<string, Record<string, unknown>> = {
  regime: {
    available: true,
    date: '2026-06-11',
    regime: 'BULL_EXPANSION',
    status: 'OK',
    coverage: 0.92,
    fired_rules: ['R1'],
    headline: '확장 국면 지속',
    is_finalized: true,
  },
  breadth: {
    available: true,
    universe: 'SPY',
    date: '2026-06-11',
    advance: 320,
    decline: 160,
    ad_line: 1234,
    ad_line_change: 56,
    history_30d: [],
  },
  sector: {
    available: true,
    date: '2026-06-11',
    sectors: [],
    cross_dispersion: 0.314,
    rotation_index: 0.072,
  },
  concentration: {
    available: true,
    date: '2026-06-11',
    universe: 'SPY',
    top5_weight: 0.28,
    top10_weight: 0.41,
    hhi: 0.0521,
    top_holdings: [{ symbol: 'AAPL', weight: 0.071 }],
    history_30d: [],
  },
  brief: {
    available: true,
    date: '2026-06-11',
    model_version: 'gemini-2.5-flash',
    status: 'OK',
    headline: '시장 요약',
    content: '오늘 시장은 완만한 상승세를 보였다.',
  },
}

// ── 핸들러 팩토리 ──

export function mpOverviewSuccess(overrides?: Partial<OverviewResponse>) {
  return http.get(`${MP_V2_BASE}/overview`, () =>
    HttpResponse.json({ ...overviewFixture, ...overrides }, { status: 200 }),
  )
}

export function mpOverviewPending() {
  return http.get(`${MP_V2_BASE}/overview`, async () => {
    await delay('infinite')
    return HttpResponse.json(overviewFixture)
  })
}

export function mpOverviewError(status = 500) {
  return http.get(`${MP_V2_BASE}/overview`, () =>
    HttpResponse.json({ error: 'boom' }, { status }),
  )
}

export function mpI18nSuccess() {
  return http.get(`${MP_V2_BASE}/i18n`, () => HttpResponse.json(i18nFixture, { status: 200 }))
}

export function mpCardDetailSuccess(cardId: string) {
  return http.get(`${MP_V2_BASE}/cards/${cardId}/detail`, () =>
    HttpResponse.json(
      {
        _meta: { generated_at: '2026-06-11T00:00:00Z', latency_ms: 5, cache: 'MISS' },
        data: cardDetailFixtures[cardId],
      },
      { status: 200 },
    ),
  )
}

export function mpNewsRefreshSuccess() {
  return http.post(`${MP_V2_BASE}/news/refresh`, () =>
    HttpResponse.json(
      {
        _meta: { generated_at: '2026-06-11T00:00:00Z', count: 1, pool_size: 10, seen_count: 1 },
        items: overviewFixture.news,
      },
      { status: 200 },
    ),
  )
}

/** page 렌더에 필요한 공통 핸들러(overview + i18n + 5 card detail + news refresh). */
export function mpAllHandlers() {
  return [
    mpOverviewSuccess(),
    mpI18nSuccess(),
    mpNewsRefreshSuccess(),
    ...['regime', 'breadth', 'sector', 'concentration', 'brief'].map(mpCardDetailSuccess),
  ]
}
