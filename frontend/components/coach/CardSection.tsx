/**
 * CardSection — Slice 17 Step 0 신규. 조건부 wrapper.
 *
 * CommentaryCard의 각 optional 섹션이 가진 graceful 미렌더 로직
 * (`length > 0` 등)을 본 컴포넌트 내부로 흡수해 한 곳에 박는다.
 *
 * ⚠ 실측 (c)-1: 이 로직을 5 페이지로 옮기면 조건 분기가 분산된다. 강제로
 * 컴포넌트 내부에 보존 (Slice 17 §0 회귀 위험 지점 1번).
 *
 * - 사용 패턴: <CardSection visible={obs.length > 0} className="mb-5">...</CardSection>
 *   visible=false면 null 반환 (graceful 미렌더).
 */

'use client'

import type { ReactNode } from 'react'

interface CardSectionProps {
  visible: boolean
  /** section wrapper에 부여할 추가 클래스 (기본 마진 등). */
  className?: string
  children: ReactNode
}

export default function CardSection({ visible, className, children }: CardSectionProps) {
  if (!visible) return null
  return <section className={className}>{children}</section>
}
