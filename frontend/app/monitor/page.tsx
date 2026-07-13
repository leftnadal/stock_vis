'use client'

import { useMemo, useState } from 'react'

import Link from 'next/link'
import { Plus } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { MonitorListCard } from '@/components/monitor/MonitorListCard'
import { useMonitors } from '@/hooks/useMonitor'
import type { Monitor, MonitorScope } from '@/types/monitor'

type ScopeFilter = 'all' | MonitorScope

const SCOPE_CHIPS: { key: ScopeFilter; label: string }[] = [
  { key: 'all', label: '전체' },
  { key: 'stock', label: '종목' },
  { key: 'market', label: '시장' },
  { key: 'sector', label: '섹터' },
  { key: 'theme', label: '테마' },
  { key: 'fund', label: '펀드' },
]

function Chip({
  active,
  label,
  count,
  onClick,
}: {
  active: boolean
  label: string
  count?: number
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-sm transition ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
      }`}
    >
      {label}
      {typeof count === 'number' && (
        <span className={active ? 'text-blue-100' : 'text-gray-400'}>{count}</span>
      )}
    </button>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-gray-300 py-16 text-center dark:border-gray-700">
      <p className="text-4xl">🌙</p>
      <div>
        <p className="font-medium text-gray-800 dark:text-gray-100">
          아직 모니터링 중인 대상이 없어요
        </p>
        <p className="mt-1 text-sm text-gray-500">
          관심 대상을 등록하고 내 규칙으로 상태를 추적해 보세요.
        </p>
      </div>
      <Link
        href="/monitor/new"
        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >
        <Plus size={16} /> 새 모니터 만들기
      </Link>
    </div>
  )
}

function MonitorListContent() {
  const { data: monitors, isLoading, isError } = useMonitors()
  const [scope, setScope] = useState<ScopeFilter>('all')
  const [claimOnly, setClaimOnly] = useState(false)

  const scopeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const m of monitors ?? []) counts[m.scope] = (counts[m.scope] ?? 0) + 1
    return counts
  }, [monitors])

  const claimCount = useMemo(
    () => (monitors ?? []).filter((m: Monitor) => m.has_claim).length,
    [monitors]
  )

  // 서버가 트리아지 순서로 정렬해 반환 → 칩 필터는 순서를 보존한 채 부분집합만.
  const filtered = useMemo(() => {
    return (monitors ?? []).filter(
      (m: Monitor) =>
        (scope === 'all' || m.scope === scope) && (!claimOnly || m.has_claim)
    )
  }, [monitors, scope, claimOnly])

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Monitor</h1>
          <p className="text-sm text-gray-500">내 모니터링</p>
        </div>
        <Link
          href="/monitor/new"
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus size={16} /> 새 모니터
        </Link>
      </div>

      {!isLoading && !isError && (monitors?.length ?? 0) > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {SCOPE_CHIPS.map((c) => (
            <Chip
              key={c.key}
              active={scope === c.key}
              label={c.label}
              count={c.key === 'all' ? monitors?.length : scopeCounts[c.key] ?? 0}
              onClick={() => setScope(c.key)}
            />
          ))}
          <Chip
            active={claimOnly}
            label="가설만"
            count={claimCount}
            onClick={() => setClaimOnly((v) => !v)}
          />
        </div>
      )}

      {isLoading && <p className="py-12 text-center text-gray-400">불러오는 중…</p>}
      {isError && (
        <p className="py-12 text-center text-red-500">목록을 불러오지 못했어요.</p>
      )}
      {!isLoading && !isError && (monitors?.length ?? 0) === 0 && <EmptyState />}
      {!isLoading && !isError && (monitors?.length ?? 0) > 0 && (
        <div className="flex flex-col gap-3">
          {filtered.map((m: Monitor) => (
            <MonitorListCard key={m.id} monitor={m} />
          ))}
          {filtered.length === 0 && (
            <p className="py-8 text-center text-sm text-gray-400">
              이 필터에 해당하는 모니터가 없어요.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function MonitorListPage() {
  return (
    <AuthGuard>
      <MonitorListContent />
    </AuthGuard>
  )
}
