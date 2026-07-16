'use client'

/**
 * My 탭 "권유 읽기 화면" (Slice 20a).
 *
 * 4-상태(로딩/에러/빈/성공) 명시 처리. 손잡이 5종은 읽기 전용(쓰기는 20b),
 * 예상수익률은 데이터가 없어 빈 슬롯 placeholder만 표시한다(§2 절대 규칙).
 */

import { AlertCircle, Loader2, Sparkles } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { AdvisorySummaryStrip } from '@/components/advisory/AdvisorySummaryStrip'
import { ExpectedReturnSlot } from '@/components/advisory/ExpectedReturnSlot'
import { KnobsPanel } from '@/components/advisory/KnobsPanel'
import { RecommendationCard } from '@/components/advisory/RecommendationCard'
import {
  useAdvisoryKnobs,
  useAdvisorySummary,
  useLatestAdvisory,
  useRunAdvisory,
} from '@/hooks/useAdvisory'

function RunButton() {
  const runMutation = useRunAdvisory()
  return (
    <button
      type="button"
      data-testid="run-advisory-button"
      onClick={() => runMutation.mutate()}
      disabled={runMutation.isPending}
      className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
    >
      {runMutation.isPending ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          진단 중...
        </>
      ) : (
        <>
          <Sparkles className="h-4 w-4" />
          지금 진단
        </>
      )}
    </button>
  )
}

function AdvisoryPageContent() {
  const latestQuery = useLatestAdvisory()
  const summaryQuery = useAdvisorySummary()
  const knobsQuery = useAdvisoryKnobs()

  const isLoading = latestQuery.isLoading || summaryQuery.isLoading || knobsQuery.isLoading
  const isError = latestQuery.isError || summaryQuery.isError || knobsQuery.isError
  const isEmpty = !isLoading && !isError && latestQuery.data?.available === false
  const output = latestQuery.data?.output ?? null

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">권유</h1>
          <p className="text-sm text-gray-500">
            보유·목표 기반 배치 권유입니다. 신뢰도·여력 기반 산출이며 미래 예측이 아닙니다.
          </p>
        </div>
        <RunButton />
      </div>

      {isLoading && (
        <div
          data-testid="loading-state"
          className="flex flex-col items-center gap-3 rounded-2xl border border-slate-200 bg-white p-10 text-slate-600 dark:border-gray-800 dark:bg-gray-900"
        >
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <p className="text-sm">불러오는 중...</p>
        </div>
      )}

      {!isLoading && isError && (
        <div
          role="alert"
          data-testid="error-state"
          className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-800 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300"
        >
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-medium">권유 정보를 불러오지 못했습니다.</p>
            <p className="mt-1">잠시 후 다시 시도해 주세요.</p>
          </div>
        </div>
      )}

      {!isLoading && !isError && isEmpty && (
        <div
          data-testid="empty-state"
          className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500 dark:border-gray-700 dark:bg-gray-800/40 dark:text-gray-400"
        >
          아직 진단 이력이 없어요.{' '}
          <a href="/wallet" className="font-medium text-blue-600 hover:underline dark:text-blue-400">
            지갑 탭
          </a>
          에서 보유·현금을 입력하고 <span className="font-medium">[지금 진단]</span>을 누르세요.
        </div>
      )}

      {!isLoading && !isError && !isEmpty && (
        <div className="flex flex-col gap-5">
          {summaryQuery.data?.available && <AdvisorySummaryStrip summary={summaryQuery.data} />}

          {output && (
            <div className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">권유 목록</h2>
              {output.recommendations.length === 0 && (
                <p className="text-sm text-gray-400">권유할 항목이 없어요.</p>
              )}
              <div className="flex flex-col gap-3">
                {output.recommendations.map((rec) => (
                  <RecommendationCard key={`${rec.symbol}-${rec.currency}`} recommendation={rec} />
                ))}
              </div>
            </div>
          )}

          <ExpectedReturnSlot />

          {knobsQuery.data?.available && <KnobsPanel knobs={knobsQuery.data} />}

          {output && (
            <p data-testid="advisory-disclaimer" className="text-xs text-gray-400">
              {output.disclaimer} 신뢰도/여력 기반 산출이며 예측이 아닙니다.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function AdvisoryPage() {
  return (
    <AuthGuard>
      <AdvisoryPageContent />
    </AuthGuard>
  )
}
