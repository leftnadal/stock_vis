/**
 * CommentaryCard — 코치 진단 결과 공통 표시 컴포넌트.
 *
 * 6 진입점(E1~E6)이 공통으로 재사용. Slice 16 Part 1 §3에서 prop 타입을
 * `CommentaryCardData` 공통 base로 일반화 (E1/E2/...의 output 필드 합집합).
 * - 데이터 페칭 안 함 (순수 표시) — 부모가 data를 prop으로 전달.
 * - 로딩·에러·빈 상태는 부모 페이지 책임 (이 컴포넌트는 data가 있을 때만 렌더).
 * - 진입점별로 비어있는 섹션(빈 배열·undefined·빈 dict)은 graceful 미렌더.
 *
 * 후속: Slice 16 Part 5 후 C 리팩터링 재검토 (BaseCard + EP별 Section 분리).
 */

'use client'

import { AlertTriangle, BarChart3, CheckCircle2, ListChecks, Target } from 'lucide-react'

import type {
  CommentaryActionItem,
  CommentaryActionPriority,
  CommentaryCardData,
  CommentaryConfidence,
} from '@/lib/coach/types'

interface CommentaryCardProps {
  output: CommentaryCardData
}

const CONFIDENCE_STYLE: Record<CommentaryConfidence, { label: string; cls: string }> = {
  high: { label: '높음', cls: 'bg-green-100 text-green-800 border-green-300' },
  medium: { label: '보통', cls: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  low: { label: '낮음', cls: 'bg-red-100 text-red-800 border-red-300' },
}

const PRIORITY_STYLE: Record<CommentaryActionPriority, { label: string; cls: string }> = {
  high: { label: '즉시', cls: 'bg-red-50 text-red-700 border-red-200' },
  medium: { label: '단기', cls: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  low: { label: '장기', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
}

function formatQuotedMetricValue(value: unknown): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(2)
  if (typeof value === 'string' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

export default function CommentaryCard({ output }: CommentaryCardProps) {
  const confidence = CONFIDENCE_STYLE[output.confidence]
  const observations = output.key_observations ?? []
  const actionItems: CommentaryActionItem[] = output.action_items ?? []
  const riskFlags = output.risk_flags ?? []
  const quotedMetricsEntries = Object.entries(output.quoted_metrics ?? {})

  return (
    <article
      data-testid="commentary-card"
      className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      {/* ── 요약 + 신뢰도 ── */}
      <header className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">진단 요약</p>
          <h2 className="mt-1 text-xl font-semibold text-slate-900">{output.summary}</h2>
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium ${confidence.cls}`}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          신뢰도 {confidence.label}
        </span>
      </header>

      {/* ── 핵심 관찰 ── */}
      {observations.length > 0 && (
        <section className="mb-5">
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700">
            <Target className="h-4 w-4 text-blue-500" />
            핵심 관찰
          </h3>
          <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
            {observations.map((obs, idx) => (
              <li key={idx}>{obs}</li>
            ))}
          </ul>
        </section>
      )}

      {/* ── 액션 아이템 ── */}
      {actionItems.length > 0 && (
        <section className="mb-5">
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700">
            <ListChecks className="h-4 w-4 text-emerald-500" />
            추천 액션
          </h3>
          <ul className="space-y-2">
            {actionItems.map((item, idx) => {
              const priority = PRIORITY_STYLE[item.priority]
              return (
                <li
                  key={idx}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-3"
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-slate-900">{item.title}</p>
                    <span
                      className={`shrink-0 rounded border px-2 py-0.5 text-[11px] font-medium ${priority.cls}`}
                    >
                      {priority.label}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600">{item.description}</p>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {/* ── 인용 지표 (E2 등) ── */}
      {quotedMetricsEntries.length > 0 && (
        <section className="mb-5">
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700">
            <BarChart3 className="h-4 w-4 text-indigo-500" />
            인용 지표
          </h3>
          <dl className="grid grid-cols-1 gap-1 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2">
            {quotedMetricsEntries.map(([key, value]) => (
              <div key={key} className="flex justify-between gap-3 text-sm">
                <dt className="font-medium text-slate-700">{key}</dt>
                <dd className="text-slate-900">{formatQuotedMetricValue(value)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {/* ── 리스크 플래그 ── */}
      {riskFlags.length > 0 && (
        <section>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            리스크
          </h3>
          <ul className="list-inside list-disc space-y-1 text-sm text-amber-800">
            {riskFlags.map((flag, idx) => (
              <li key={idx}>{flag}</li>
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}
