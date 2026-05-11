'use client'

import { useMemo } from 'react'
import { useThesisList, useAlerts } from '@/lib/thesis/queries'
import { sortThesesByPriority } from '@/lib/thesis/utils'
import { ThesisListSkeleton } from '@/components/thesis/skeleton/ThesisSkeleton'
import { ThesisListCard } from '@/components/thesis/list/ThesisListCard'
import { TodayChangeCard } from '@/components/thesis/list/TodayChangeCard'
import { EntryPointGrid } from '@/components/thesis/list/EntryPointGrid'
import { MoonPhase } from '@/components/thesis'
import { RefreshCw } from 'lucide-react'
import { USE_MOCK, MOCK_THESES, MOCK_ALERTS } from '@/lib/thesis/mock'

export default function ThesisPage() {
  return (
    <div className="space-y-8">
      <ActiveThesesSection />
      <TodayChangesSection />
      <NewThesisSection />
    </div>
  )
}

// ═══ 섹션 1: 추적 중 가설 목록 ═══
function ActiveThesesSection() {
  // ── Mock 모드 분기 (M1) ──
  // USE_MOCK=true일 때 enabled:false로 실제 네트워크 요청 차단.
  // hook 호출 자체는 유지하여 Rules of Hooks 준수.
  const { data, isLoading, isError, refetch } = useThesisList({
    enabled: !USE_MOCK,
  })

  const theses = USE_MOCK ? MOCK_THESES : data

  // ── 상태 우선순위 정렬 (M8) ──
  // critical → needs_review → weakening → strengthening → active → warming_up
  // useMemo를 early return 위에 배치하여 Rules of Hooks 준수
  const activeTheses = (theses ?? []).filter((t) => t.status === 'active')
  const sorted = useMemo(
    () => sortThesesByPriority(activeTheses),
    // activeTheses는 매 렌더마다 새 배열 참조 — JSON 문자열로 안정화
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(activeTheses)],
  )

  if (isLoading && !USE_MOCK) return <ThesisListSkeleton />

  if (isError && !USE_MOCK) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400 text-sm mb-3">
          데이터를 불러오지 못했어요.
        </p>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 text-blue-400 text-sm
                     hover:text-blue-300 transition-colors"
        >
          <RefreshCw size={14} />
          새로고침
        </button>
      </div>
    )
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-gray-300 text-sm font-medium">
          추적 중
          {sorted.length > 0 && (
            <span className="ml-1.5 text-gray-500">{sorted.length}</span>
          )}
        </h2>
      </div>

      {sorted.length === 0 ? (
        <EmptyTheses />
      ) : (
        <ul className="space-y-3">
          {sorted.map((thesis) => (
            <li key={thesis.id}>
              <ThesisListCard thesis={thesis} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

// ═══ 섹션 2: 오늘의 변화 ═══
function TodayChangesSection() {
  const { data } = useAlerts({
    enabled: !USE_MOCK,
  })

  const alerts = USE_MOCK ? MOCK_ALERTS : data

  const unreadAlerts = (alerts ?? []).filter((a) => !a.is_read).slice(0, 3)

  return (
    <section>
      <h2 className="text-gray-300 text-sm font-medium mb-3">오늘의 변화</h2>

      {unreadAlerts.length === 0 ? (
        // ── 시간 중립 문구 (M4) ──
        // created_at 기반 "오늘"/"지난밤" 필터링 미구현 상태이므로
        // 시간 해석이 포함된 문구("어젯밤") 대신 데이터 조건과 일치하는 중립 문구 사용.
        <p className="text-gray-600 text-sm py-4 text-center">
          새로운 변화가 아직 없어요.
        </p>
      ) : (
        <ul className="space-y-2">
          {unreadAlerts.map((alert) => (
            <li key={alert.id}>
              <TodayChangeCard alert={alert} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

// ═══ 섹션 3: 새 가설 진입점 ═══
function NewThesisSection() {
  return (
    <section>
      <h2 className="text-gray-300 text-sm font-medium mb-3">새로운 가설</h2>
      <EntryPointGrid />
    </section>
  )
}

// ═══ 빈 상태 ═══
function EmptyTheses() {
  return (
    <div className="text-center py-12 bg-gray-900/50 rounded-xl border border-dashed border-gray-800">
      <MoonPhase score={null} size="md" />
      <p className="text-gray-400 text-sm mt-4">
        아직 추적 중인 가설이 없어요.
      </p>
      <p className="text-gray-600 text-xs mt-1">
        아래에서 첫 가설을 세워보세요!
      </p>
    </div>
  )
}
