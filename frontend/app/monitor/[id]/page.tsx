'use client'

// Monitor 상세 (MON-CLOSE-UI Phase 2 §0.5) — 리스트 카드가 이미 링크하던 dangling 대상 신설.
import { use, useState } from 'react'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { CloseModal } from '@/components/monitor/CloseModal'
import { MoonPhase } from '@/components/monitor/MoonPhase'
import { StateBandSparkline } from '@/components/monitor/StateBandSparkline'
import { VerdictBadge } from '@/components/monitor/VerdictBadge'
import { useAuth } from '@/contexts/AuthContext'
import {
  useClosePreview,
  useIndicators,
  useMonitor,
  useMonitorClaims,
  useSparkline,
} from '@/hooks/useMonitor'
import { outcomeToVerdict } from '@/lib/monitor/closure'
import { STATE_TONE_CLASS, ddayLabel, stateMeta } from '@/lib/monitor/display'
import type { Claim, Monitor } from '@/types/monitor'

const SCOPE_LABEL: Record<Monitor['scope'], string> = {
  market: '시장',
  sector: '섹터',
  theme: '테마',
  fund: '펀드',
  stock: '종목',
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  return iso.slice(0, 10)
}

function IndicatorRow({
  name,
  latestValue,
}: {
  name: string
  latestValue: number | null | undefined
}) {
  return (
    <div className="flex items-center justify-between border-b border-gray-100 py-2 text-sm last:border-0 dark:border-gray-800">
      <span className="text-gray-600 dark:text-gray-300">{name}</span>
      <span className="text-gray-400">
        {typeof latestValue === 'number' ? latestValue.toFixed(3) : '—'}
      </span>
    </div>
  )
}

function ClaimRow({
  claim,
  judgeUsername,
  onCloseClick,
}: {
  claim: Claim
  judgeUsername?: string | null
  onCloseClick: (claim: Claim) => void
}) {
  const pending = claim.outcome === 'pending'
  return (
    <div
      className="flex items-start justify-between gap-3 border-b border-gray-100 py-3 last:border-0 dark:border-gray-800"
      data-testid="claim-row"
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm text-gray-800 dark:text-gray-100">{claim.assertion}</p>
        {claim.deadline && <p className="mt-0.5 text-xs text-gray-400">마감 {claim.deadline}</p>}
        {!pending && (
          <p className="mt-1 text-xs text-gray-400" data-testid="claim-row-closure-summary">
            {claim.resolved_at ? `${formatDate(claim.resolved_at)} 마감` : '마감'}
            {judgeUsername && ` · 판정자 ${judgeUsername}`}
          </p>
        )}
        {!pending && claim.retro_memo && (
          <p className="mt-1 text-xs italic text-gray-400">&ldquo;{claim.retro_memo}&rdquo;</p>
        )}
      </div>
      {pending ? (
        <button
          type="button"
          onClick={() => onCloseClick(claim)}
          data-testid="claim-close-button"
          className="flex-shrink-0 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
        >
          마감
        </button>
      ) : (
        <VerdictBadge verdict={outcomeToVerdict(claim.outcome)} />
      )}
    </div>
  )
}

function MonitorDetailContent({ monitorId }: { monitorId: string }) {
  const { data: monitor, isLoading, isError, error } = useMonitor(monitorId)
  const { data: claims } = useMonitorClaims(monitorId)
  const { data: indicators } = useIndicators(monitorId)
  const { user } = useAuth()

  const score = monitor?.latest_score ?? null
  const { data: spark } = useSparkline(monitorId, 30, score !== null)

  // close-preview는 무상태라 claim 상태 무관하게 호출 가능 — 이걸로 지표 "최신값"을 보강.
  const firstClaimId = claims?.[0]?.id ?? ''
  const { data: preview } = useClosePreview(firstClaimId, !!firstClaimId)
  const latestValueById = new Map((preview?.indicators ?? []).map((i) => [i.id, i.latest_value]))

  const [closingClaim, setClosingClaim] = useState<Claim | null>(null)

  if (isLoading) {
    return (
      <div className="py-16 text-center text-gray-400" data-testid="monitor-detail-loading">
        불러오는 중…
      </div>
    )
  }

  if (isError || !monitor) {
    const status = (error as { response?: { status?: number } } | null | undefined)?.response
      ?.status
    return (
      <div className="py-16 text-center text-gray-400" data-testid="monitor-detail-not-found">
        {status === 404 ? '찾을 수 없는 모니터입니다.' : '불러오지 못했어요.'}
      </div>
    )
  }

  const meta = stateMeta(monitor.current_state)
  const dday = ddayLabel(monitor.next_deadline)

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <div className="mb-4 flex items-center gap-3">
        <Link href="/monitor" className="text-gray-500 hover:text-gray-800" aria-label="목록으로">
          <ArrowLeft size={20} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-500 dark:bg-gray-700 dark:text-gray-400">
              {SCOPE_LABEL[monitor.scope]}
            </span>
            <h1 className="truncate font-semibold text-gray-900 dark:text-gray-100">
              {monitor.name}
            </h1>
          </div>
          {monitor.resolved_label && (
            <p className="truncate text-xs text-gray-500 dark:text-gray-400">
              {monitor.resolved_label}
            </p>
          )}
        </div>
        <span className={`rounded px-2 py-1 text-xs font-medium ${STATE_TONE_CLASS[meta.tone]}`}>
          {meta.label}
        </span>
        {dday && <span className="text-xs font-medium text-gray-500">{dday}</span>}
      </div>

      <div className="mb-6 flex items-center gap-4 rounded-xl border border-gray-200 p-4 dark:border-gray-700">
        <MoonPhase score={score} label={monitor.display?.phase_label} size="lg" showLabel />
        {spark && (
          <div className="flex-1">
            <StateBandSparkline
              series={spark.series}
              bands={spark.bands}
              transitions={spark.transitions}
              width={220}
              height={48}
            />
          </div>
        )}
      </div>

      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">지표</h2>
        {(indicators ?? []).length === 0 ? (
          <p className="text-sm text-gray-400">등록된 지표가 없어요.</p>
        ) : (
          <div className="rounded-xl border border-gray-100 px-3 dark:border-gray-800">
            {(indicators ?? []).map((ind) => (
              <IndicatorRow key={ind.id} name={ind.name} latestValue={latestValueById.get(ind.id)} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">가설</h2>
        {(claims ?? []).length === 0 ? (
          <p className="text-sm text-gray-400">등록된 가설이 없어요.</p>
        ) : (
          <div className="rounded-xl border border-gray-100 px-3 dark:border-gray-800">
            {(claims ?? []).map((c) => (
              <ClaimRow
                key={c.id}
                claim={c}
                judgeUsername={user?.username}
                onCloseClick={setClosingClaim}
              />
            ))}
          </div>
        )}
      </section>

      {closingClaim && (
        <CloseModal
          monitorId={monitorId}
          claimId={closingClaim.id}
          onClose={() => setClosingClaim(null)}
        />
      )}
    </div>
  )
}

export default function MonitorDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return (
    <AuthGuard>
      <MonitorDetailContent monitorId={id} />
    </AuthGuard>
  )
}
