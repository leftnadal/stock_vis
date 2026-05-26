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

import {
  COACH_E1_PATH,
  COACH_E2_PATH,
  COACH_E3_PATH,
  COACH_E4_PATH,
  COACH_E5_PATH,
  COACH_E6_PATH,
} from '@/lib/coach/api'
import type {
  E1Response,
  E2Response,
  E3Response,
  E4Response,
  E5Response,
  E6Response,
} from '@/lib/coach/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
const E1_URL = `${API_URL}${COACH_E1_PATH}`
const E2_URL = `${API_URL}${COACH_E2_PATH}`
const E3_URL = `${API_URL}${COACH_E3_PATH}`
const E4_URL = `${API_URL}${COACH_E4_PATH}`
const E5_URL = `${API_URL}${COACH_E5_PATH}`
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

// ─────────────────────────────────────────────────────────────
// E3 — 집중도 분석 (Slice 16 Part 3)
//
// ⚠️ mock 충실성 게이트: 200 응답은 codegen `E3Response` 봉투 형태에 부합.
//    E3 output 필드 = summary / key_observations? / confidence / action_items?
//    / risk_flags? (metrics_table, quoted_metrics 없음 — base 완화 활용).
// ─────────────────────────────────────────────────────────────

export const defaultE3Response: E3Response = {
  output: {
    summary: 'AAPL 단일 종목 60% 집중 — 분산 부족 위험.',
    confidence: 'high',
    key_observations: [
      'HHI 0.52 — 통상 0.25 이상은 고집중도',
      'Top3 비중 100% (3종목만 보유)',
      'Tech 섹터 100% — 산업 단일화',
    ],
    action_items: [
      {
        title: 'AAPL 비중 축소',
        description: '60%에서 35~40%로 점진적 리밸런싱. 매각 차익은 분산 종목 매수.',
        priority: 'high',
        category: 'rebalance',
      },
      {
        title: '비-Tech 섹터 편입',
        description: 'Healthcare, Financial, Consumer Staples 등 최소 2개 섹터 추가.',
        priority: 'medium',
        category: 'rebalance',
      },
    ],
    risk_flags: [
      '단일 종목 집중도 60% — 개별 종목 충격 시 포트폴리오 30%+ 손실 위험',
      'Tech 섹터 단일화 — 금리 변동·규제 위험에 동시 노출',
    ],
  },
  llm_metadata: {
    provider: 'haiku',
    model: 'claude-haiku-4-5-20251001',
    input_tokens: 900,
    output_tokens: 410,
    cost_usd: 0.0021,
  },
}

export function mockE3Success(custom?: Partial<E3Response>) {
  const body: E3Response = {
    ...defaultE3Response,
    ...custom,
    output: { ...defaultE3Response.output, ...(custom?.output ?? {}) },
    llm_metadata: { ...defaultE3Response.llm_metadata, ...(custom?.llm_metadata ?? {}) },
  }
  return http.post(E3_URL, () => HttpResponse.json(body, { status: 200 }))
}

export function mockE3ValidationError() {
  return http.post(E3_URL, () =>
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

export function mockE3ServerError() {
  return http.post(E3_URL, () =>
    HttpResponse.json({ error: 'Internal server error' }, { status: 500 }),
  )
}

// ─────────────────────────────────────────────────────────────
// E5 — 추출 + 시계열 컨텍스트 (Slice 16 Part 4)
//
// ⚠️ mock 충실성 게이트: 200 응답은 codegen `E5Response` 봉투 형태에 부합.
//    E5Output 필드 = summary / key_observations? / confidence / action_items?
//    / quoted_metrics? (risk_flags 없음, metrics_table 없음).
// ─────────────────────────────────────────────────────────────

export const defaultE5Response: E5Response = {
  output: {
    summary: '배당수익률 3.45% (12분기 +30bp), 시계열 흐름 우상향.',
    confidence: 'high',
    key_observations: [
      '배당수익률 12분기 누적 +30bp — 안정적 증가 추세',
      '4분기 변화율 +4.5% — 단기 모멘텀 양호',
      '섹터 다각화 부재 — Tech 100%',
    ],
    action_items: [
      {
        title: '배당 성장 지속성 점검',
        description: '12분기 + 추세이나 최근 1분기 증가폭 둔화 모니터링.',
        priority: 'medium',
        category: 'monitor',
      },
    ],
    quoted_metrics: {
      dividend_yield: '3.45% (12분기 +30bp)',
      sector_diversification: 'low (Tech 100%)',
      beta: '1.12',
      expense_ratio: '0.18%',
    },
  },
  llm_metadata: {
    provider: 'haiku',
    model: 'claude-haiku-4-5-20251001',
    input_tokens: 1050,
    output_tokens: 480,
    cost_usd: 0.0024,
  },
}

export function mockE5Success(custom?: Partial<E5Response>) {
  const body: E5Response = {
    ...defaultE5Response,
    ...custom,
    output: { ...defaultE5Response.output, ...(custom?.output ?? {}) },
    llm_metadata: { ...defaultE5Response.llm_metadata, ...(custom?.llm_metadata ?? {}) },
  }
  return http.post(E5_URL, () => HttpResponse.json(body, { status: 200 }))
}

export function mockE5ValidationError() {
  return http.post(E5_URL, () =>
    HttpResponse.json(
      {
        status_code: 400,
        detail: 'Validation failed.',
        code: 'invalid',
        errors: { extraction_targets: ['Field required'] },
      },
      { status: 400 },
    ),
  )
}

export function mockE5ServerError() {
  return http.post(E5_URL, () =>
    HttpResponse.json({ error: 'Internal server error' }, { status: 500 }),
  )
}

// ─────────────────────────────────────────────────────────────
// E4 — 대화 Q&A (Slice 16 Part 5, 마지막 진입점)
//
// ⚠️ mock 충실성 게이트: 200 응답은 codegen `E4Response` 봉투 형태에 부합.
//    E4Output 필드 = summary / key_observations? / confidence 만 (base 그대로,
//    action_items / risk_flags / quoted_metrics / metrics_table 모두 부재).
//    화면에서 assistant turn content = output.summary 1:1 매핑 (E4Turn 계약).
// ─────────────────────────────────────────────────────────────

export const defaultE4Response: E4Response = {
  output: {
    summary:
      'HHI 0.40 기준 집중도는 중간 수준입니다. Tech 비중 65%가 결정 요인이며 분산 여지가 있습니다.',
    confidence: 'medium',
    key_observations: [
      'HHI 0.40 — 통상 0.25 이상은 집중도 주의 구간',
      'Tech 65% — 단일 섹터 충격 노출도 높음',
      'Top3 종목 80% — 분산 효과 제한적',
    ],
  },
  llm_metadata: {
    provider: 'haiku',
    model: 'claude-haiku-4-5-20251001',
    input_tokens: 880,
    output_tokens: 320,
    cost_usd: 0.0014,
  },
}

export function mockE4Success(custom?: Partial<E4Response>) {
  const body: E4Response = {
    ...defaultE4Response,
    ...custom,
    output: { ...defaultE4Response.output, ...(custom?.output ?? {}) },
    llm_metadata: { ...defaultE4Response.llm_metadata, ...(custom?.llm_metadata ?? {}) },
  }
  return http.post(E4_URL, () => HttpResponse.json(body, { status: 200 }))
}

export function mockE4ValidationError() {
  return http.post(E4_URL, () =>
    HttpResponse.json(
      {
        status_code: 400,
        detail: 'Validation failed.',
        code: 'invalid',
        errors: { user_question: ['Field required'] },
      },
      { status: 400 },
    ),
  )
}

export function mockE4ServerError() {
  return http.post(E4_URL, () =>
    HttpResponse.json({ error: 'Internal server error' }, { status: 500 }),
  )
}

/**
 * 기본 핸들러 — 서버 listen 시점에 등록. 테스트에서 `server.use(...)`로 override.
 */
export const handlers = [
  mockE1Success(),
  mockE2Success(),
  mockE3Success(),
  mockE4Success(),
  mockE5Success(),
  mockE6Success(),
]
