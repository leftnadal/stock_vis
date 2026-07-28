'use client'

import { useMemo, useState } from 'react'

import Link from 'next/link'
import { Plus } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { MonitorListCard } from '@/components/monitor/MonitorListCard'
import { useAuth } from '@/contexts/AuthContext'
import { useClaims, useMonitors } from '@/hooks/useMonitor'
import { summarizeClaimClosure } from '@/lib/monitor/closure'
import type { Claim, Monitor, MonitorScope } from '@/types/monitor'

type ScopeFilter = 'all' | MonitorScope
type StatusFilter = 'active' | 'closed' | 'all'

const SCOPE_CHIPS: { key: ScopeFilter; label: string }[] = [
  { key: 'all', label: '전체' },
  { key: 'stock', label: '종목' },
  { key: 'market', label: '시장' },
  { key: 'sector', label: '섹터' },
  { key: 'theme', label: '테마' },
  { key: 'fund', label: '펀드' },
]

const STATUS_SEGMENTS: { key: StatusFilter; label: string }[] = [
  { key: 'active', label: '진행 중' },
  { key: 'closed', label: '마감' },
  { key: 'all', label: '전체' },
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

function StatusSegment({
  value,
  onChange,
}: {
  value: StatusFilter
  onChange: (v: StatusFilter) => void
}) {
  return (
    <div
      className="mb-4 inline-flex rounded-lg bg-gray-100 p-1 dark:bg-gray-800"
      data-testid="status-segment"
    >
      {STATUS_SEGMENTS.map((s) => (
        <button
          key={s.key}
          type="button"
          onClick={() => onChange(s.key)}
          data-testid={`status-seg-${s.key}`}
          aria-pressed={value === s.key}
          className={`rounded-md px-3 py-1 text-sm transition ${
            value === s.key
              ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-gray-100'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'
          }`}
        >
          {s.label}
        </button>
      ))}
    </div>
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
  const { data: claims } = useClaims()
  const { user } = useAuth()
  const [scope, setScope] = useState<ScopeFilter>('all')
  const [claimOnly, setClaimOnly] = useState(false)
  const [status, setStatus] = useState<StatusFilter>('active')

  // 모니터별 필터는 클라이언트단(BE는 monitor로 필터하지 않음) — 전체 Claim을 모니터 id로 그룹핑.
  const claimsByMonitor = useMemo(() => {
    const map = new Map<string, Claim[]>()
    for (const c of claims ?? []) {
      const list = map.get(c.monitor) ?? []
      list.push(c)
      map.set(c.monitor, list)
    }
    return map
  }, [claims])

  // 0.3 마감 상태 파생: Monitor:Claim=1:N → 전 Claim resolved면 "마감", 일부면 "진행+n중 m".
  const closureByMonitor = useMemo(() => {
    const map = new Map<string, ReturnType<typeof summarizeClaimClosure>>()
    for (const m of monitors ?? []) {
      map.set(m.id, summarizeClaimClosure(claimsByMonitor.get(m.id) ?? []))
    }
    return map
  }, [monitors, claimsByMonitor])

  // 가격축(TIMING-P2): 모니터별 활성 Claim 중 zone_display 있는 첫 건 → 카드 가격축.
  const zoneByMonitor = useMemo(() => {
    const map = new Map<string, Claim['zone_display']>()
    for (const m of monitors ?? []) {
      const active = (claimsByMonitor.get(m.id) ?? []).find(
        (c) => c.status === 'active' && c.zone_display?.zone
      )
      if (active?.zone_display) map.set(m.id, active.zone_display)
    }
    return map
  }, [monitors, claimsByMonitor])

  const closedCount = useMemo(
    () => [...closureByMonitor.values()].filter((c) => c.isFullyClosed).length,
    [closureByMonitor]
  )

  const scopeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const m of monitors ?? []) counts[m.scope] = (counts[m.scope] ?? 0) + 1
    return counts
  }, [monitors])

  const claimCount = useMemo(
    () => (monitors ?? []).filter((m: Monitor) => m.has_claim).length,
    [monitors]
  )

  // 서버가 트리아지 순서로 정렬해 반환 → 칩/세그먼트 필터는 순서를 보존한 채 부분집합만(AND 교차).
  const filtered = useMemo(() => {
    return (monitors ?? []).filter((m: Monitor) => {
      if (scope !== 'all' && m.scope !== scope) return false
      if (claimOnly && !m.has_claim) return false
      const closure = closureByMonitor.get(m.id)
      if (status === 'active' && closure?.isFullyClosed) return false
      if (status === 'closed' && !closure?.isFullyClosed) return false
      return true
    })
  }, [monitors, scope, claimOnly, status, closureByMonitor])

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
        <>
          <div className="mb-3 flex flex-wrap gap-2">
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
              label="시나리오만"
              count={claimCount}
              onClick={() => setClaimOnly((v) => !v)}
            />
          </div>
          {/* 0.2 B-1: 마감 0건이면 세그먼트 자체를 숨긴다(빈 세그먼트 노출 금지). */}
          {closedCount > 0 && <StatusSegment value={status} onChange={setStatus} />}
        </>
      )}

      {isLoading && <p className="py-12 text-center text-gray-400">불러오는 중…</p>}
      {isError && (
        <p className="py-12 text-center text-red-500">목록을 불러오지 못했어요.</p>
      )}
      {!isLoading && !isError && (monitors?.length ?? 0) === 0 && <EmptyState />}
      {!isLoading && !isError && (monitors?.length ?? 0) > 0 && (
        <div className="flex flex-col gap-3">
          {filtered.map((m: Monitor) => (
            <MonitorListCard
              key={m.id}
              monitor={m}
              closureSummary={closureByMonitor.get(m.id)}
              judgeUsername={user?.username}
              zoneDisplay={zoneByMonitor.get(m.id)}
            />
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
