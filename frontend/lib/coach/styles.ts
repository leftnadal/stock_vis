/**
 * Coach 도메인 공유 스타일 토큰 — Slice 17 Step 0 신규.
 *
 * CommentaryCard / E4MessageBubble 양쪽에 동일하게 중복되어 있던 confidence
 * 라벨/배경 스타일 사전을 단일 소스로 통합. 향후 새 EP / 컴포넌트가 confidence
 * 표현을 추가할 때 이 모듈만 수정한다.
 *
 * ⚠ 안 B 경계 규칙(Slice 17 §0): 공유 가능한 것은 confidence 배지처럼 EP 무관
 * 동일 의미의 원자 표현 요소뿐. 카드/말풍선 wrapper처럼 EP 표현 정체성을
 * 결정하는 컨테이너 스타일은 본 모듈에 포함하지 않는다.
 */

import type { CommentaryConfidence } from './types'

export interface ConfidenceStyle {
  label: string
  cls: string
}

export const CONFIDENCE_STYLE: Record<CommentaryConfidence, ConfidenceStyle> = {
  high: { label: '높음', cls: 'bg-green-100 text-green-800 border-green-300' },
  medium: { label: '보통', cls: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  low: { label: '낮음', cls: 'bg-red-100 text-red-800 border-red-300' },
}
