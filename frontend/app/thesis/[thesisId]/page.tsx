'use client'

import { useParams } from 'next/navigation'
import { Settings } from 'lucide-react'
import Link from 'next/link'
import { useDashboard } from '@/lib/thesis/queries'
import { USE_MOCK, MOCK_DASHBOARD } from '@/lib/thesis/mock'
import { ThesisDashboardSkeleton } from '@/components/thesis/skeleton/ThesisSkeleton'
import { DashboardPageHeader } from '@/components/thesis/dashboard/DashboardPageHeader'
import { DashboardHeader } from '@/components/thesis/dashboard/DashboardHeader'
import { IndicatorRow } from '@/components/thesis/dashboard/IndicatorRow'
import { AISummarySection } from '@/components/thesis/dashboard/AISummarySection'
import { NotableChangesSection } from '@/components/thesis/dashboard/NotableChangesSection'

export default function ThesisDashboardPage() {
  const params = useParams()
  const thesisId = params.thesisId as string

  const {
    data: dashboard,
    isLoading,
    isError,
    refetch,
  } = useDashboard(thesisId)

  const data = USE_MOCK ? MOCK_DASHBOARD : dashboard

  // ── 로딩 ──
  if (isLoading && !USE_MOCK) {
    return (
      <div className="max-w-lg mx-auto px-4 pt-4 pb-20">
        <DashboardPageHeader />
        <ThesisDashboardSkeleton />
      </div>
    )
  }

  // ── 에러 ──
  if ((isError || !data) && !USE_MOCK) {
    return (
      <div className="max-w-lg mx-auto px-4 pt-4 pb-20">
        <DashboardPageHeader />
        <div className="text-center py-20">
          <p className="text-gray-400 text-sm mb-3">
            대시보드를 불러오지 못했어요
          </p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 text-blue-400 text-sm
                       hover:text-blue-300 transition-colors"
          >
            새로고침
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="max-w-lg mx-auto px-4 pt-4 pb-20">
      {/* 공통 헤더 */}
      <DashboardPageHeader
        showRefresh
        isLoading={isLoading}
        onRefresh={() => refetch()}
      />

      <div className="space-y-6">
        {/* 가설 정보 */}
        <DashboardHeader thesis={data.thesis} />

        {/* AI 분석 */}
        <AISummarySection
          summary={data.thesis.ai_summary}
          snapshotDate={data.thesis.snapshot_date}
        />

        {/* 오늘의 변화 */}
        <NotableChangesSection
          changes={data.thesis.notable_changes}
          snapshotDate={data.thesis.snapshot_date}
        />

        {/* 지표 리스트 (세로 나열) */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-gray-400 text-sm font-medium">
              지표 ({data.indicators.length}개)
            </h3>
            <Link
              href={`/thesis/${thesisId}/indicators`}
              className="inline-flex items-center gap-1 text-gray-500 text-xs
                         hover:text-gray-300 transition-colors"
            >
              <Settings size={12} />
              설정
            </Link>
          </div>

          {data.indicators.length === 0 ? (
            <div className="text-center py-8 border border-dashed border-gray-700 rounded-xl">
              <p className="text-gray-500 text-sm">아직 지표가 없어요</p>
              <Link
                href={`/thesis/${thesisId}/indicators`}
                className="text-blue-400 text-xs hover:underline mt-1 inline-block"
              >
                지표 추가하기
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {data.indicators.map((ind) => (
                <IndicatorRow
                  key={ind.id}
                  thesisId={thesisId}
                  indicator={ind}
                />
              ))}
            </div>
          )}
        </section>

        {/* 하단 액션 */}
        <div className="space-y-2 pt-2">
          <Link
            href={`/thesis/${thesisId}/close`}
            className="block w-full py-3 border border-gray-700 text-gray-400 text-sm
                       text-center rounded-xl hover:border-gray-500 transition-colors"
          >
            가설 마감하기
          </Link>
        </div>
      </div>
    </div>
  )
}
