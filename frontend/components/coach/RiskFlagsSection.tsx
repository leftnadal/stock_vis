/**
 * RiskFlagsSection — Slice 17 Part 3 신규. Group A 두 번째 섹션.
 *
 * 보유 EP: E1 / E3 / E6 (E6는 quoted_metrics + risk_flags 양쪽 보유 — Part 2
 * QuotedMetricsSection과 본 컴포넌트가 함께 작동). 본 컴포넌트는 CommentaryCard
 * 의 risk_flags 인라인 블록(L94-105)을 행위 보존 추출한 결과.
 *
 * - 조건부 가시성은 호출처(CardSection visible)에 위임. 본 컴포넌트는 단일 책임.
 * - SectionHeader 사용 + AlertTriangle 아이콘 보존 (시각 회귀 0).
 * - 리스크 본문은 amber-800 색상 보존 (강조 의도 유지).
 */

'use client'

import { AlertTriangle } from 'lucide-react'

import SectionHeader from './SectionHeader'

interface RiskFlagsSectionProps {
  riskFlags: string[]
}

export default function RiskFlagsSection({ riskFlags }: RiskFlagsSectionProps) {
  return (
    <>
      <SectionHeader
        icon={<AlertTriangle className="h-4 w-4 text-amber-500" />}
        title="리스크"
      />
      <ul className="list-inside list-disc space-y-1 text-sm text-amber-800">
        {riskFlags.map((flag, idx) => (
          <li key={idx}>{flag}</li>
        ))}
      </ul>
    </>
  )
}
