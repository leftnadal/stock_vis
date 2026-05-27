/**
 * QuotedMetricsSection — Slice 17 Part 2 신규. Group B(quoted_metrics) 섹션.
 *
 * 보유 EP: E2 / E5 / E6 (E5는 Part 4 조합 검증에서 확인). 본 컴포넌트는
 * CommentaryCard로부터 quoted_metrics 렌더 블록(L93-107)을 행위 보존 추출한 결과.
 *
 * - 조건부 렌더는 호출처(CommentaryCard)의 <CardSection visible=...>가 책임.
 *   본 컴포넌트는 entries가 비어 있을 때도 dl만 빈 채로 렌더 (단일 책임 — section
 *   가시성 결정은 wrapper에 위임).
 * - SectionHeader 사용 + BarChart3 아이콘 보존 (시각 회귀 0)
 * - formatQuotedMetricValue 헬퍼를 본 컴포넌트 내부로 이동 — quoted_metrics
 *   단독 사용 헬퍼라 응집(CommentaryCard에서 제거).
 *
 * ⚠ 외형 wrapper 신규 생성 금지 (지시서 Part 2 §1-1). SectionHeader + 기존
 *   dl 마크업만 사용.
 */

'use client'

import { BarChart3 } from 'lucide-react'

import SectionHeader from './SectionHeader'

interface QuotedMetricsSectionProps {
  quotedMetrics: Record<string, unknown>
}

export function formatQuotedMetricValue(value: unknown): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(2)
  if (typeof value === 'string' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

export default function QuotedMetricsSection({ quotedMetrics }: QuotedMetricsSectionProps) {
  const entries = Object.entries(quotedMetrics)
  return (
    <>
      <SectionHeader
        icon={<BarChart3 className="h-4 w-4 text-indigo-500" />}
        title="인용 지표"
      />
      <dl className="grid grid-cols-1 gap-1 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex justify-between gap-3 text-sm">
            <dt className="font-medium text-slate-700">{key}</dt>
            <dd className="text-slate-900">{formatQuotedMetricValue(value)}</dd>
          </div>
        ))}
      </dl>
    </>
  )
}
