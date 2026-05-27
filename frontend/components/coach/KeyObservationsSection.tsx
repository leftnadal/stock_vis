/**
 * KeyObservationsSection — Slice 17 Part 4 신규. 5 카드형 EP 공통 섹션.
 *
 * 보유 EP: 6 EP 전부(optional, base 필드). 본 컴포넌트는 CommentaryCard의
 * key_observations 인라인 블록(Part 3 종료 시점 L45-53)을 행위 보존 추출한 결과.
 * 본 추출로 CommentaryCard는 인라인 렌더 로직 0건이 되어 순수 조립부가 된다.
 *
 * - 조건부 가시성은 호출처(CardSection visible)에 위임. 본 컴포넌트는 단일 책임.
 * - SectionHeader 사용 + Target 아이콘 보존 (시각 회귀 0).
 * - 본문 slate-700 색상 보존 (관찰 사항의 차분한 강조 유지).
 */

'use client'

import { Target } from 'lucide-react'

import SectionHeader from './SectionHeader'

interface KeyObservationsSectionProps {
  keyObservations: string[]
}

export default function KeyObservationsSection({
  keyObservations,
}: KeyObservationsSectionProps) {
  return (
    <>
      <SectionHeader
        icon={<Target className="h-4 w-4 text-blue-500" />}
        title="핵심 관찰"
      />
      <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
        {keyObservations.map((obs, idx) => (
          <li key={idx}>{obs}</li>
        ))}
      </ul>
    </>
  )
}
