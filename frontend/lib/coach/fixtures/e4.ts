/**
 * E4 fixture — Slice 16 Part 5 (P5-A) 신규 작성.
 *
 * Slice 7 `portfolio/tests/fixtures/e4_conversation/`는 별도 스키마
 * (E4ConversationInput, `current_user_question` / `tier` 필드 등)이라 본
 * CommentaryInputE4와 호환되지 않는다. 본 프론트 fixture는 codegen 타입
 * (`CoachE4RequestRequest`) 형태에 정합한 신규 자산.
 *
 * 복제 함정 방지 — 다른 EP fixture에서 빠뜨려 문제가 됐던 4 필드
 * (portfolio_id / fetched_at / preset / holdings)을 모두 채워둔다.
 *
 * 샘플:
 *   - sampleE4InputEmptyHistory: 첫 질문 (history 빈 배열)
 *   - sampleE4InputTwoTurnHistory: 후속 질문 (1턴 user/assistant 누적된 상태)
 *   - sampleE4Response: 응답 봉투 (defaultE4Response와 유사하나 fixture는 독립)
 */

import type { E4Request, E4Response, E4Turn } from '../types'

const COMMON_BASE = {
  portfolio_id: 'fixture-e4-001',
  fetched_at: '2026-05-26T00:00:00Z' as const,
  preset: 'garp' as const,
  entry_point: 'e4' as const,
  holdings: [
    { ticker: 'AAPL', weight: 0.4, sector: 'Tech', asset_class: 'stock' as const, name: 'Apple' },
    {
      ticker: 'MSFT',
      weight: 0.35,
      sector: 'Tech',
      asset_class: 'stock' as const,
      name: 'Microsoft',
    },
    {
      ticker: 'JNJ',
      weight: 0.25,
      sector: 'Healthcare',
      asset_class: 'stock' as const,
      name: 'Johnson & Johnson',
    },
  ],
}

export const sampleE4InputEmptyHistory: E4Request = {
  ...COMMON_BASE,
  user_question: '내 포트폴리오의 집중도가 어느 정도인가요?',
  conversation_history: [],
}

/**
 * 2 turn 누적 사례 — 1턴 user/assistant 끝난 직후 2번째 질문 제출 시 보내는 payload.
 * conversation_history 원소는 `E4Turn` 계약(role/content) 그대로.
 */
const PREV_TURN_USER: E4Turn = {
  role: 'user',
  content: '내 포트폴리오의 집중도가 어느 정도인가요?',
}
const PREV_TURN_ASSISTANT: E4Turn = {
  role: 'assistant',
  content:
    'HHI 0.40 기준 집중도는 중간 수준입니다. Tech 비중 65%가 결정 요인이며 분산 여지가 있습니다.',
}

export const sampleE4InputTwoTurnHistory: E4Request = {
  ...COMMON_BASE,
  user_question: 'Tech 비중을 줄이려면 어떤 종목부터 검토하면 좋을까요?',
  // codegen 타입은 list[dict[str, Any]] → E4Turn dict 그대로 호환.
  conversation_history: [PREV_TURN_USER, PREV_TURN_ASSISTANT],
}

export const sampleE4Response: E4Response = {
  output: {
    summary:
      'AAPL 비중 부분 축소(40→30%) 후 Healthcare/Consumer Staples 종목 추가 검토를 권장합니다.',
    confidence: 'medium',
    key_observations: [
      'AAPL 단일 종목 40% — Top1 비중이 분산 효과를 크게 제한',
      'Tech 65% → 50% 수준으로 완화 시 섹터 충격 흡수력 개선',
      'JNJ 외 비-Tech 종목 부재 — 분산 후보 섹터 다양화 필요',
    ],
  },
  llm_metadata: {
    provider: 'haiku',
    model: 'claude-haiku-4-5-20251001',
    input_tokens: 940,
    output_tokens: 360,
    cost_usd: 0.0016,
  },
}
