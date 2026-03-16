'use client'

import { useState, useEffect, useRef, Suspense } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import { ArrowLeft, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'
import { thesisApi } from '@/lib/thesis/api'
import { useThesis, useIndicators } from '@/lib/thesis/queries'
import {
  useAddIndicator, useRemoveIndicator, useToggleIndicator,
} from '@/lib/thesis/mutations'
import {
  USE_MOCK, MOCK_INDICATORS, MOCK_RECOMMENDATIONS,
} from '@/lib/thesis/mock'
import type { RecommendedIndicator, IndicatorCreatePayload } from '@/lib/thesis/types'
import { IndicatorSetupCard } from '@/components/thesis/indicators/IndicatorSetupCard'
import { AddIndicatorSheet } from '@/components/thesis/indicators/AddIndicatorSheet'

export default function ThesisIndicatorsPage() {
  return (
    <Suspense fallback={<IndicatorsLoading />}>
      <IndicatorsContent />
    </Suspense>
  )
}

function IndicatorsLoading() {
  return (
    <div className="flex flex-col h-[calc(100dvh-env(safe-area-inset-top))] bg-gray-950">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
        <div className="p-1 text-gray-400"><ArrowLeft size={20} /></div>
        <h1 className="text-white text-base font-medium flex-1">지표 설정</h1>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-gray-600 text-sm">불러오는 중...</div>
      </div>
    </div>
  )
}

function IndicatorsContent() {
  const params = useParams()
  const searchParams = useSearchParams()
  const router = useRouter()
  const thesisId = params.thesisId as string
  const isAutoMode = searchParams.get('auto') === 'true'

  // ── 데이터 조회 ──
  const { data: thesis } = useThesis(thesisId)
  const {
    data: indicators,
    isLoading: isLoadingIndicators,
    error: indicatorsError,
    refetch: refetchIndicators,
  } = useIndicators(thesisId)

  // ── Mutations ──
  const addMutation = useAddIndicator(thesisId)
  const removeMutation = useRemoveIndicator(thesisId)
  const toggleMutation = useToggleIndicator(thesisId)

  // ── Mock 로컬 상태 (토글/삭제 즉시 반영) ──
  const [mockIndicators, setMockIndicators] = useState(MOCK_INDICATORS)

  // ── AI 추천 상태 (query cache 아님) ──
  const [recommendations, setRecommendations] = useState<RecommendedIndicator[]>([])
  const [isRecommending, setIsRecommending] = useState(false)
  const [addedNames, setAddedNames] = useState<Set<string>>(new Set())
  const [addingName, setAddingName] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  // ── 표시할 지표 목록 ──
  const displayIndicators = USE_MOCK ? mockIndicators : (indicators ?? [])

  // ── 기존 지표로 addedNames 초기화 (중복 추가 방지) ──
  useEffect(() => {
    if (displayIndicators.length > 0) {
      setAddedNames(prev => {
        const next = new Set(prev)
        displayIndicators.forEach(ind => next.add(ind.name))
        return next
      })
    }
  }, [displayIndicators.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── ?auto=true: 마운트 시 자동 추천 (1회만, StrictMode 방지) ──
  const autoFetchedRef = useRef(false)
  useEffect(() => {
    if (isAutoMode && !autoFetchedRef.current) {
      autoFetchedRef.current = true
      fetchRecommendations()
    }
  }, [isAutoMode]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── AI 추천 호출 ──
  async function fetchRecommendations() {
    setIsRecommending(true)
    setSheetOpen(true)

    if (USE_MOCK) {
      setTimeout(() => {
        setRecommendations(MOCK_RECOMMENDATIONS)
        setIsRecommending(false)
      }, 1500)
      return
    }

    try {
      const response = await thesisApi.autoRecommend(thesisId)
      setRecommendations(response.indicators)
    } catch {
      toast.error('AI 추천에 실패했어요')
      setRecommendations([])
    } finally {
      setIsRecommending(false)
    }
  }

  // ── 추천 지표 추가 (개별) ──
  async function handleAddRecommended(rec: RecommendedIndicator) {
    if (addedNames.has(rec.name)) return
    setAddingName(rec.name)

    const payload: IndicatorCreatePayload = {
      name: rec.name,
      indicator_type: rec.indicator_type,
      data_source: rec.data_source,
      data_params: rec.data_params,
      support_direction: rec.support_direction,
      is_ai_recommended: true,
    }

    if (USE_MOCK) {
      setTimeout(() => {
        setAddedNames(prev => new Set(prev).add(rec.name))
        setAddingName(null)
        toast.success(`${rec.name} 추가됨`)
      }, 300)
      return
    }

    try {
      await addMutation.mutateAsync(payload)
      setAddedNames(prev => new Set(prev).add(rec.name))
      toast.success(`${rec.name} 추가됨`)
    } catch {
      // onError in mutation handles toast
    } finally {
      setAddingName(null)
    }
  }

  // ── 추천 전체 추가 ──
  async function handleAddAll() {
    const remaining = recommendations.filter(r => !addedNames.has(r.name))
    for (const rec of remaining) {
      await handleAddRecommended(rec)
    }
  }

  // ── 기존 지표 토글 (Mock: 로컬 상태 반영) ──
  function handleToggle(indicatorId: string, isActive: boolean) {
    if (USE_MOCK) {
      setMockIndicators(prev =>
        prev.map(ind =>
          ind.id === indicatorId ? { ...ind, is_active: isActive } : ind,
        ),
      )
      toast.success(isActive ? '지표 활성화됨' : '지표 비활성화됨')
      return
    }
    toggleMutation.mutate({ indicatorId, isActive })
  }

  // ── 기존 지표 삭제 (Mock: 로컬 상태 반영) ──
  function handleRemove(indicatorId: string) {
    if (USE_MOCK) {
      setMockIndicators(prev => prev.filter(ind => ind.id !== indicatorId))
      toast.success('지표 삭제됨')
      return
    }
    removeMutation.mutate(indicatorId)
  }

  // ── 네비게이션 ──
  function handleStartMonitoring() {
    if (USE_MOCK || !thesisId) {
      router.push('/thesis')
      return
    }
    router.push(`/thesis/${thesisId}`)
  }

  return (
    <div className="flex flex-col h-[calc(100dvh-env(safe-area-inset-top))] bg-gray-950">
      {/* 헤더 */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
        <Link href="/thesis" className="p-1 text-gray-400 hover:text-white">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-white text-base font-medium flex-1">지표 설정</h1>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="flex-1 overflow-y-auto px-4 pt-4 pb-4">
        {/* 가설 정보 */}
        {thesis && (
          <div className="mb-6">
            <p className="text-gray-500 text-xs mb-1">가설</p>
            <p className="text-white text-lg font-medium">
              {thesis.title}
              <span className="ml-2 text-sm">
                {thesis.direction === 'bullish'
                  ? '\u{1F4C8}'
                  : thesis.direction === 'bearish'
                    ? '\u{1F4C9}'
                    : '\u27A1\uFE0F'}
              </span>
            </p>
          </div>
        )}

        {/* 지표 목록 */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-gray-400 text-sm font-medium">
              현재 지표 ({displayIndicators.length}개)
            </p>
          </div>

          {isLoadingIndicators && !USE_MOCK ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div
                  key={i}
                  className="bg-gray-900 border border-gray-700 rounded-xl p-4 animate-pulse"
                >
                  <div className="h-4 bg-gray-800 rounded w-2/3 mb-2" />
                  <div className="h-3 bg-gray-800 rounded w-1/3" />
                </div>
              ))}
            </div>
          ) : indicatorsError && !USE_MOCK ? (
            <div className="text-center py-8">
              <p className="text-gray-400 text-sm mb-3">지표를 불러오지 못했어요</p>
              <button
                onClick={() => refetchIndicators()}
                className="text-blue-400 text-sm hover:underline"
              >
                다시 시도
              </button>
            </div>
          ) : displayIndicators.length === 0 ? (
            <div className="text-center py-8 border border-dashed border-gray-700 rounded-xl">
              <p className="text-gray-500 text-sm">아직 지표가 없어요</p>
              <p className="text-gray-600 text-xs mt-1">
                AI 추천으로 지표를 추가해보세요
              </p>
            </div>
          ) : (
            <ul className="space-y-3 list-none">
              {displayIndicators.map(ind => (
                <li key={ind.id}>
                  <IndicatorSetupCard
                    indicator={ind}
                    onToggle={handleToggle}
                    onRemove={handleRemove}
                    isToggling={toggleMutation.isPending}
                    isRemoving={removeMutation.isPending}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* AI 추천 버튼 */}
        <button
          onClick={fetchRecommendations}
          disabled={isRecommending}
          className="w-full flex items-center justify-center gap-2 py-3.5
                     border border-dashed border-gray-600 rounded-xl
                     text-gray-300 text-sm hover:border-gray-500
                     transition-colors active:scale-[0.98]"
        >
          <Sparkles size={16} className="text-purple-400" />
          AI 추천으로 추가
        </button>
      </div>

      {/* 하단 CTA */}
      <div className="flex-shrink-0 border-t border-gray-800 bg-gray-950 px-4 py-4 space-y-2">
        <button
          onClick={handleStartMonitoring}
          disabled={displayIndicators.length === 0 && !USE_MOCK}
          className={`w-full py-4 text-sm font-medium rounded-xl
                     active:scale-[0.98] transition-transform
                     ${displayIndicators.length > 0 || USE_MOCK
                       ? 'bg-blue-600 text-white'
                       : 'bg-gray-800 text-gray-600 cursor-not-allowed'}`}
        >
          관제 시작하기 →
        </button>
        <Link
          href="/thesis"
          className="block w-full py-2 text-gray-500 text-sm text-center"
        >
          돌아가기
        </Link>
      </div>

      {/* 추천 바텀시트 */}
      <AddIndicatorSheet
        isOpen={sheetOpen}
        onClose={() => setSheetOpen(false)}
        recommendations={recommendations}
        isLoading={isRecommending}
        addedNames={addedNames}
        onAdd={handleAddRecommended}
        onAddAll={handleAddAll}
        addingName={addingName}
      />
    </div>
  )
}
