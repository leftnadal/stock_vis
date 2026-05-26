/**
 * MSW 핸들러 — coach API mock 응답.
 *
 * Slice 15 Part 1 인프라: E1 happy/error 핸들러 + 테스트별 override 헬퍼.
 *
 * ⚠️ mock 충실성 게이트: 200 응답은 생성 타입 `E1Response` (wrapper 봉투)에
 *    반드시 타입상 부합해야 한다. P1-0에서 봉투 형태로 정정된 이후 기준:
 *    `{output: E1Output, llm_metadata: object, gate_tier?, preset_id?, scores?}`.
 *    이 충실성이 깨지면 Part 3 통합 테스트가 거짓 위에 선다.
 */

import { http, HttpResponse } from 'msw'

import { COACH_E1_PATH, COACH_E2_PATH, COACH_E6_PATH } from '@/lib/coach/api'
import type { E1Response, E2Response, E6Response } from '@/lib/coach/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
const E1_URL = `${API_URL}${COACH_E1_PATH}`
const E2_URL = `${API_URL}${COACH_E2_PATH}`
const E6_URL = `${API_URL}${COACH_E6_PATH}`

/**
 * 표준 happy-path E1 응답 — 실제 백엔드가 반환하는 봉투 형태를 그대로 모방.
 *
 * 백엔드 fixture(`portfolio/tests/fixtures/...`) 결과를 단순화한 형태.
 * Test에서 필요 시 `mockE1Success(custom)`로 일부 필드 override 가능.
 */
export const defaultE1Response: E1Response = {
  output: {
    summary: 'GARP 진단: 균형적 포트폴리오. 성장-가치 비중 65/35 적정.',
    confidence: 'medium',
    key_observations: [
      'EPS 성장률 평균 12% (벤치마크 8% 대비 양호)',
      'PER 평균 18배 (S&P 500 평균 22배 대비 할인)',
    ],
    action_items: [
      {
        title: 'AAPL 비중 5% 축소',
        description: '집중도 완화 및 PER 22배 부담 해소.',
        priority: 'medium',
        category: 'rebalance',
      },
    ],
    risk_flags: ['단일 섹터(Tech) 비중 45% — 분산도 점검 필요'],
    metrics_table: '',
  },
  llm_metadata: {
    provider: 'haiku',
    model: 'claude-haiku-4-5-20251001',
    input_tokens: 1200,
    output_tokens: 450,
    cost_usd: 0.0021,
  },
}

/**
 * E1 happy-path 핸들러 (200). 응답을 인자로 override 가능.
 */
export function mockE1Success(custom?: Partial<E1Response>) {
  const body: E1Response = {
    ...defaultE1Response,
    ...custom,
    output: { ...defaultE1Response.output, ...(custom?.output ?? {}) },
    llm_metadata: { ...defaultE1Response.llm_metadata, ...(custom?.llm_metadata ?? {}) },
  }
  return http.post(E1_URL, () => HttpResponse.json(body, { status: 200 }))
}

/**
 * E1 검증 실패 (400) 핸들러 — 백엔드 errors 형태 모방.
 */
export function mockE1ValidationError() {
  return http.post(E1_URL, () =>
    HttpResponse.json(
      {
        status_code: 400,
        detail: 'Validation failed.',
        code: 'invalid',
        errors: { portfolio_id: ['Field required'] },
      },
      { status: 400 },
    ),
  )
}

/**
 * E1 서버 에러 (500) 핸들러.
 */
export function mockE1ServerError() {
  return http.post(E1_URL, () =>
    HttpResponse.json({ error: 'Internal server error' }, { status: 500 }),
  )
}

// ─────────────────────────────────────────────────────────────
// E2 — 포트폴리오 종합 진단 (Slice 16 Part 1)
//
// ⚠️ mock 충실성 게이트: 200 응답은 codegen `E2Response` 봉투 형태에 부합해야
//    한다. E2 output은 E1과 달리 quoted_metrics(optional)를 포함, action_items/
//    risk_flags는 없음 — 백엔드 E2Output schema 그대로.
// ─────────────────────────────────────────────────────────────

export const defaultE2Response: E2Response = {
  output: {
    summary: '포트폴리오 종합 진단: Tech 비중 65%, 1년 수익률 +12.5% 양호.',
    confidence: 'medium',
    key_observations: [
      '섹터 집중도 — Tech 65% / Healthcare 20% / 기타 15%',
      '1년 수익률 12.5%는 벤치마크 S&P 500 (~10%) 대비 우수',
      '대형주 비중 80% — 변동성 흡수 양호',
    ],
    quoted_metrics: {
      portfolio_return_1y: 12.5,
      tech_weight: 0.65,
      healthcare_weight: 0.2,
      large_cap_ratio: 0.8,
    },
    metrics_table: '',
  },
  llm_metadata: {
    provider: 'haiku',
    model: 'claude-haiku-4-5-20251001',
    input_tokens: 1100,
    output_tokens: 420,
    cost_usd: 0.0019,
  },
}

export function mockE2Success(custom?: Partial<E2Response>) {
  const body: E2Response = {
    ...defaultE2Response,
    ...custom,
    output: { ...defaultE2Response.output, ...(custom?.output ?? {}) },
    llm_metadata: { ...defaultE2Response.llm_metadata, ...(custom?.llm_metadata ?? {}) },
  }
  return http.post(E2_URL, () => HttpResponse.json(body, { status: 200 }))
}

export function mockE2ValidationError() {
  return http.post(E2_URL, () =>
    HttpResponse.json(
      {
        status_code: 400,
        detail: 'Validation failed.',
        code: 'invalid',
        errors: { portfolio_id: ['Field required'] },
      },
      { status: 400 },
    ),
  )
}

export function mockE2ServerError() {
  return http.post(E2_URL, () =>
    HttpResponse.json({ error: 'Internal server error' }, { status: 500 }),
  )
}

// ─────────────────────────────────────────────────────────────
// E6 — 분석엔진 (비교 분석) (Slice 16 Part 2)
//
// ⚠️ mock 충실성 게이트: 200 응답은 codegen `E6Response` 봉투 형태에 부합.
//    E6 output 필드 = summary / key_observations? / confidence / risk_flags?
//    / quoted_metrics? (E1과 달리 action_items 없음, E2와 달리 risk_flags 있음).
// ─────────────────────────────────────────────────────────────

export const defaultE6Response: E6Response = {
  output: {
    summary: 'AAPL 매수 우위 / MSFT 보유 / NVDA 차익실현 신호.',
    confidence: 'medium',
    key_observations: [
      'AAPL: PEG 1.3, 모멘텀 양호 — score 0.78',
      'MSFT: 안정적 캐시플로우 — score 0.65',
      'NVDA: 단기 과열 신호 — score 0.42',
    ],
    risk_flags: ['NVDA 변동성 ↑ — 단기 익절 고려'],
    quoted_metrics: {
      avg_score: 0.62,
      bull_signals: 2,
      bear_signals: 1,
    },
  },
  llm_metadata: {
    provider: 'haiku',
    model: 'claude-haiku-4-5-20251001',
    input_tokens: 950,
    output_tokens: 380,
    cost_usd: 0.0018,
  },
}

export function mockE6Success(custom?: Partial<E6Response>) {
  const body: E6Response = {
    ...defaultE6Response,
    ...custom,
    output: { ...defaultE6Response.output, ...(custom?.output ?? {}) },
    llm_metadata: { ...defaultE6Response.llm_metadata, ...(custom?.llm_metadata ?? {}) },
  }
  return http.post(E6_URL, () => HttpResponse.json(body, { status: 200 }))
}

export function mockE6ValidationError() {
  return http.post(E6_URL, () =>
    HttpResponse.json(
      {
        status_code: 400,
        detail: 'Validation failed.',
        code: 'invalid',
        errors: { portfolio_id: ['Field required'] },
      },
      { status: 400 },
    ),
  )
}

export function mockE6ServerError() {
  return http.post(E6_URL, () =>
    HttpResponse.json({ error: 'Internal server error' }, { status: 500 }),
  )
}

/**
 * 기본 핸들러 — 서버 listen 시점에 등록. 테스트에서 `server.use(...)`로 override.
 */
export const handlers = [mockE1Success(), mockE2Success(), mockE6Success()]
