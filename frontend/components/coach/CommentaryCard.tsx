/**
 * CommentaryCard — 코치 진단 결과 공통 표시 컴포넌트.
 *
 * 6 진입점(E1~E6) 중 카드형 5건(E1·E2·E3·E5·E6)이 공통으로 재사용.
 * Slice 16 Part 1 §3에서 prop 타입을 `CommentaryCardData` 공통 base로 일반화.
 * Slice 17 Step 0에서 BaseCard / SectionHeader / CardSection / ConfidenceBadge로
 * 골격을 분해. Part 2에서 quoted_metrics 블록을 QuotedMetricsSection으로 추출.
 * props 시그니처 무변경(행위 보존 추출 누적).
 *
 * - 데이터 페칭 안 함 (순수 표시) — 부모가 data를 prop으로 전달.
 * - 로딩·에러·빈 상태는 부모 페이지 책임 (이 컴포넌트는 data가 있을 때만 렌더).
 * - 진입점별로 비어있는 섹션(빈 배열·undefined·빈 dict)은 CardSection의
 *   조건부 wrapper로 graceful 미렌더 (분기 로직을 컴포넌트 내부에 보존).
 *
 * ⚠ 안 B 경계 규칙(Slice 17 §0): 본 컴포넌트는 카드 wrapper(BaseCard)를 사용.
 * E4MessageBubble은 별도 말풍선 wrapper로 분기되며 본 컴포넌트와 외형을 공유하지
 * 않는다. 공유 자산은 ConfidenceBadge / styles.ts:CONFIDENCE_STYLE 등 원자 단위뿐.
 */

'use client'

import { AlertTriangle, Target } from 'lucide-react'

import ActionItemsSection from './ActionItemsSection'
import BaseCard from './BaseCard'
import CardSection from './CardSection'
import QuotedMetricsSection from './QuotedMetricsSection'
import SectionHeader from './SectionHeader'
import type { CommentaryCardData } from '@/lib/coach/types'

interface CommentaryCardProps {
  output: CommentaryCardData
}

export default function CommentaryCard({ output }: CommentaryCardProps) {
  const observations = output.key_observations ?? []
  const actionItems = output.action_items ?? []
  const riskFlags = output.risk_flags ?? []
  const quotedMetrics = output.quoted_metrics ?? {}
  const hasQuotedMetrics = Object.keys(quotedMetrics).length > 0

  return (
    <BaseCard summary={output.summary} confidence={output.confidence}>
      {/* ── 핵심 관찰 ── */}
      <CardSection visible={observations.length > 0} className="mb-5">
        <SectionHeader icon={<Target className="h-4 w-4 text-blue-500" />} title="핵심 관찰" />
        <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
          {observations.map((obs, idx) => (
            <li key={idx}>{obs}</li>
          ))}
        </ul>
      </CardSection>

      {/* ── 추천 액션 (E1·E3·E5, Slice 17 Part 3 추출) ── */}
      <CardSection visible={actionItems.length > 0} className="mb-5">
        <ActionItemsSection actionItems={actionItems} />
      </CardSection>

      {/* ── 인용 지표 (E2·E5·E6, Slice 17 Part 2 추출) ── */}
      <CardSection visible={hasQuotedMetrics} className="mb-5">
        <QuotedMetricsSection quotedMetrics={quotedMetrics} />
      </CardSection>

      {/* ── 리스크 플래그 ── */}
      <CardSection visible={riskFlags.length > 0}>
        <SectionHeader
          icon={<AlertTriangle className="h-4 w-4 text-amber-500" />}
          title="리스크"
        />
        <ul className="list-inside list-disc space-y-1 text-sm text-amber-800">
          {riskFlags.map((flag, idx) => (
            <li key={idx}>{flag}</li>
          ))}
        </ul>
      </CardSection>
    </BaseCard>
  )
}
