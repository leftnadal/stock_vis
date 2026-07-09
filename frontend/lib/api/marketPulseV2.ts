/**
 * Market Pulse v2 API client (PR-K/L).
 */
import axios, { AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

import { tokenUtils, refreshAccessToken } from '@/lib/api/authAxios'

const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
const API_ORIGIN = RAW_API_URL.replace(/\/api\/v\d+\/?$/, '')
export const MP_V2_BASE = `${API_ORIGIN}/api/v2/market-pulse`

const client: AxiosInstance = axios.create({
  baseURL: MP_V2_BASE,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = tokenUtils.getAccess()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// A2: detail 클릭 시점 access 만료 → 401. 요청 인터셉터만으론 갱신 안 됨.
// authAxios와 동일 refresh 헬퍼(단일 소스)로 1회 갱신 후 재시도(_retry 무한루프 가드).
client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status !== 401 || originalRequest?._retry) {
      return Promise.reject(error)
    }
    originalRequest._retry = true
    try {
      const newAccess = await refreshAccessToken()
      originalRequest.headers.Authorization = `Bearer ${newAccess}`
      return client(originalRequest)
    } catch (refreshError) {
      return Promise.reject(refreshError)
    }
  },
)

export type APIStatus = 'OK' | 'INSUFFICIENT_DATA' | 'STALE' | 'FAILED' | 'MARKET_CLOSED'

export interface Meta {
  status: APIStatus
  status_reason: string
  generated_at: string
  latency_ms: number
  data_finalized: boolean
  cache?: 'HIT' | 'MISS' | ''
}

export type SectorGroup = 'BENCHMARK' | 'SECTOR' | 'SAFE_HAVEN' | 'INTERNATIONAL'

export interface TickerItem {
  symbol: string
  last_close: number | null
  change_pct: number | null
  sector_group: SectorGroup | null
}

export type NewsCategory = 'MACRO' | 'GEOPOLITICS' | 'SECTOR' | 'INDEX' | 'MAG7' | 'SMART_MONEY'

export interface NewsItem {
  id: number
  category: NewsCategory
  title: string
  summary: string
  url: string
  publisher: string
  image_url?: string
  published_at: string
  matched_symbols: string[]
}

export type AnomalyMode = 'ANOMALY' | 'HYBRID' | 'CALM'
export type AnomalyRuleId = 'R02' | 'R04' | 'R09' | 'R12'

export interface AnomalyItem {
  rule_id: AnomalyRuleId
  headline: string
  threshold: Record<string, number>
  actual: number
  paired_news_id: number | null
  evidence?: {
    top10_weight: number | null
    vix_change_pct: number | null
    max_abs_sector_z: number | null
    sector_extreme_symbol: string | null
  } | null
  paired_news_title?: string | null
  paired_news_url?: string | null
}

export interface AnomalySection {
  mode: AnomalyMode
  overview: string
  sector_highlight: string
  portfolio_action: string
  fired: AnomalyItem[]
}

export type RegimeId = 'BULL_EXPANSION' | 'LATE_BULL' | 'TRANSITION' | 'BEAR_CONTRACTION' | 'CRISIS'
export type RegimeStatus = 'OK' | 'INSUFFICIENT_DATA' | 'STALE' | 'FAILED'

export interface RegimeCard {
  regime: RegimeId
  status: RegimeStatus
  coverage: number
  headline: string
  fired_rules: string[]
  transitioned: boolean
  // D-MP2-SURFACE additive: 판단 카피 + 유효성 플래그 (구버전 응답엔 없을 수 있어 optional)
  stance_copy?: string
  stance_ok?: boolean
  next_stage?: string | null
  next_stage_closest?: {
    indicator: string
    op: string
    threshold: number
    actual: number
    to_threshold: number
  } | null
  margins?: Array<{
    indicator: string
    op: string
    threshold: number
    actual: number
    to_threshold: number
  }>
  transition_from?: string | null
}

export interface BreadthCard {
  universe: 'SPY' | 'QQQ' | 'DIA'
  advance: number
  decline: number
  unchanged: number
  total: number
  new_high_52w: number
  new_low_52w: number
  ad_line: number
  ad_line_change: number
}

export interface SectorCardItem {
  symbol: string
  rel_strength: number
  rank: number
  momentum_1d: number
}

export interface SectorCard {
  leaders: SectorCardItem[]
  laggards: SectorCardItem[]
  cross_dispersion: number
  rotation_index: number
}

export interface ConcentrationCard {
  universe: string
  top5_weight: number
  top10_weight: number
  hhi: number
  top_holdings: { symbol: string; weight: number }[]
}

export interface BriefCard {
  headline: string
  content_preview: string
  status: string
  model_version: string
}

export interface OverviewCards {
  regime: RegimeCard | null
  breadth: BreadthCard | null
  sector: SectorCard | null
  concentration: ConcentrationCard | null
  brief: BriefCard | null
}

/** Phase 1.5 S4 — 카드별 감각 유추(senses) envelope. cards와 동렬 블록(미생성 시 null). */
export interface Translations {
  senses: Record<string, string>
  model_version: string
  generated_at: string
  status: string
}

export interface SectorDelta {
  sector: string
  rank: number
  prev_rank: number
  rank_delta: number
  as_of: string
  vs_date: string
}

/** MP2-DELTA 슬라이스2 — anomaly 발동 상태 변화(조회-시 파생). 날짜·state 전부 서버값. */
export type AnomalyDeltaState = 'fired' | 'resolving' | 'quiet' | 'no_history'

export interface AnomalyDelta {
  state: AnomalyDeltaState
  as_of: string
  last_fired_date: string | null
  vs_fired_date: string | null
  new_rules: AnomalyRuleId[]
  gone_rules: AnomalyRuleId[]
  resolved_rules: AnomalyRuleId[]
}

export interface OverviewResponse {
  _meta: Meta
  ticker_bar: TickerItem[]
  news: NewsItem[]
  anomaly: AnomalySection
  cards: OverviewCards
  // S4: additive — 미생성/구버전 응답엔 없을 수 있어 optional + null 허용.
  translations?: Translations | null
  sector_deltas?: SectorDelta[]
  // 슬라이스2: additive — 구버전 응답엔 없을 수 있어 optional.
  anomaly_delta?: AnomalyDelta
}

export interface CardDetailEnvelope<T> {
  _meta: { generated_at: string; latency_ms: number; cache: 'HIT' | 'MISS' }
  data: T
}

export async function fetchOverview(): Promise<OverviewResponse> {
  const { data } = await client.get<OverviewResponse>('/overview')
  return data
}

export async function fetchCardDetail<T = unknown>(
  cardId: 'regime' | 'breadth' | 'sector' | 'concentration' | 'brief',
): Promise<CardDetailEnvelope<T>> {
  const { data } = await client.get<CardDetailEnvelope<T>>(`/cards/${cardId}/detail`)
  return data
}

export async function refreshNews(): Promise<{
  _meta: { generated_at: string; count: number; pool_size: number; seen_count: number }
  items: NewsItem[]
}> {
  const { data } = await client.post('/news/refresh')
  return data
}

export interface I18nResponse {
  _meta: { locale: string; supported: string[]; cache: string; warning?: string }
  labels: Record<string, string>
}

export async function fetchI18n(locale: string = 'ko'): Promise<I18nResponse> {
  const { data } = await client.get<I18nResponse>('/i18n', { params: { locale } })
  return data
}

// ── Detail payload types (Layer 1) ──

export interface RegimeHistoryPoint {
  date: string
  stage: RegimeId
}

export interface RegimeMargin {
  indicator: string
  op: string
  threshold: number
  actual: number | null
  to_threshold: number | null
}

// MP2-TREND S3(R1): 국면 재료 판정-거리. 컷 = rules.yaml 도출(하드코딩 0), z-score 아님(raw).
export interface RegimeCut {
  value: number
  regime: RegimeId
  op: string
}
export interface RegimeComponentPoint {
  date: string
  value: number | null
}
export interface RegimeNearestCut {
  cut: number
  regime: RegimeId
  op: string
  distance: number
}
export interface RegimeComponent {
  key: string
  unit: string
  current: number | null
  series: RegimeComponentPoint[]
  cuts: RegimeCut[]
  crossed_cuts: RegimeCut[]
  nearest_cut_distance: RegimeNearestCut | null
}

export interface RegimeDetail {
  available: boolean
  date?: string
  regime?: RegimeId
  previous_regime?: string
  status?: RegimeStatus
  coverage?: number
  inputs?: Record<string, number | null>
  fired_rules?: string[]
  hysteresis_streak?: number
  headline?: string
  is_finalized?: boolean
  // MP-UX-S3a: 국면 타임라인 데이터원 (렌더는 후속 FE 슬라이스 — 타입만)
  regime_history_30d?: RegimeHistoryPoint[]
  // MP2-TREND S2(additive): 전환일(previous_regime≠regime, BE 조회-시 파생). 궤적 vlines 공용 소비.
  transition_dates?: string[]
  // MP-UX-S3b: 다음 단계까지 거리 (렌더는 후속 FE 슬라이스 — 타입만)
  next_stage?: RegimeId | null
  margins?: RegimeMargin[]
  next_stage_closest?: RegimeMargin | null
  // MP2-TREND S3(R1, additive): 국면 재료 판정-거리 소형 다중(7지표 raw + 컷).
  components?: RegimeComponent[]
}

export interface BreadthHistoryPoint {
  date: string
  advance: number
  decline: number
  ad_line: number
  ad_line_change: number
  // MP2-TREND S2(additive): A/D선 20일 이동평균(기준선). <20일 구간은 null.
  ad_line_ma20?: number | null
}

export interface BreadthDetail {
  available: boolean
  universe?: string
  date?: string
  advance?: number
  decline?: number
  unchanged?: number
  total?: number
  new_high_52w?: number
  new_low_52w?: number
  ad_line?: number
  ad_line_change?: number
  // MP2-TREND S2(additive): 최신일 기준 기준선(MA20) 이탈 연속 일수.
  ma_deviation_streak_days?: number
  history_30d?: BreadthHistoryPoint[]
}

export interface SectorRow {
  symbol: string
  rel_strength: number
  // CD-STAB Slice A′(additive): 5일 상대수익(= momentum_5d − bench 5일 수익률). 판단 계열 x축
  //   (RRG 점·미니맵·카드 근거). bench 소급 부족 시 null. 기존 rel_strength(1일)는 맥박·히트맵.
  rel_strength_5d?: number | null
  momentum_1d: number
  momentum_5d: number
  momentum_20d: number
  flow_proxy: number
  rank: number
  // MP2-SECTOR-CD S1(additive): 판단 4-상태. BE payload builder 단독 판정.
  //   구버전 응답엔 없을 수 있어 optional. null = 판단 유보.
  cd_state?:
    | 'leading_strengthening'
    | 'leading_weakening'
    | 'lagging_improving'
    | 'lagging_deteriorating'
    | null
  // CD-STAB Slice B(additive): 원시 즉시 분류값(히스테리시스 전). CD-TRANSITION-INDICATOR가 첫 소비
  //   (CD-READ) — cd_state ≠ cd_state_raw면 "전환 확인 중". 재분류 아님, 두 서빙값 비교뿐.
  cd_state_raw?:
    | 'leading_strengthening'
    | 'leading_weakening'
    | 'lagging_improving'
    | 'lagging_deteriorating'
    | null
}

export interface SectorHistoryPoint {
  date: string
  rel_strength: number
  // MP2-TREND S1(additive): 순위 궤적 y값(1~11, 1위 상단). 구버전 응답엔 없을 수 있어 optional.
  rank?: number
  // MP2-SECTOR-CD S2(additive): per-date 5일 모멘텀(저장값 노출). 구버전 응답엔 없을 수 있어 optional.
  momentum_5d?: number | null
  // CD-STAB Slice A′(additive): per-date 5일 상대수익 — RRG 점/꼬리 x축. bench 부족 시 null.
  rel_strength_5d?: number | null
}

export interface SectorHistory {
  symbol: string
  history: SectorHistoryPoint[]
}

export interface SectorDetail {
  available: boolean
  date?: string
  sectors?: SectorRow[]
  cross_dispersion?: number
  rotation_index?: number
  // MP-UX-S5-B-SECTOR-BE: 섹터별 rel_strength 시계열 (2-D, 11섹터 전부). 렌더는 slice 2(SectorSparkline).
  sector_history?: SectorHistory[]
  // MP2-SECTOR-CD S2(additive): 모멘텀 판정선 단일소스(= CD_MOMENTUM_BASELINE). FE y=0 하드코딩 금지.
  cd_momentum_baseline?: number
  // MP2-SECTOR-CD S3(additive): RRG x축(상대강도) 판정선 단일소스(= CD_REL_STRENGTH_BASELINE). FE 하드코딩 금지.
  cd_rel_strength_baseline?: number
}

export interface ConcentrationHistoryPoint {
  date: string
  top5: number
  top10: number
  hhi: number
}

export interface ConcentrationDetail {
  available: boolean
  date?: string
  universe?: string
  top5_weight?: number
  top10_weight?: number
  hhi?: number
  top_holdings?: { symbol: string; weight: number }[]
  history_30d?: ConcentrationHistoryPoint[]
}

export interface BriefDetail {
  available: boolean
  date?: string
  model_version?: string
  status?: string
  headline?: string
  body?: string
  body_sections?: string[]
  content?: string // legacy 호환 (BE는 body/body_sections 반환)
  inputs_summary?: Record<string, unknown>
  tokens?: { prompt: number; completion: number; latency_ms: number }
}
