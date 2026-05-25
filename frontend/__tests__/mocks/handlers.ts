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

import { COACH_E1_PATH } from '@/lib/coach/api'
import type { E1Response } from '@/lib/coach/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
const E1_URL = `${API_URL}${COACH_E1_PATH}`

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

/**
 * 기본 핸들러 — 서버 listen 시점에 등록. 테스트에서 `server.use(...)`로 override.
 */
export const handlers = [mockE1Success()]
