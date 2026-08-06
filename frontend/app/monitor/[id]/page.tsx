'use client'

// Monitor 상세 — B안(슬림 스트립 + 일지 지배), MON-DETAIL-P1 / D-MON-DETAIL-LAYOUT-B.
// 스트립(6토큰+펼침 패널) → 일지(지배 영역) → 매수 시나리오(마감 루프 보존).
import { use, useState } from 'react'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { CloseModal } from '@/components/monitor/CloseModal'
import { SlimStrip } from '@/components/monitor/SlimStrip'
import { VerdictBadge } from '@/components/monitor/VerdictBadge'
import { JournalFeed } from '@/components/monitor/journal/JournalFeed'
import { useAuth } from '@/contexts/AuthContext'
import {
  useClosePreview,
  useIndicators,
  useMonitor,
  useMonitorAlerts,
  useMonitorClaims,
  useSparkline,
} from '@/hooks/useMonitor'
import { buildJournal } from '@/lib/monitor/journal'
import { outcomeToVerdict } from '@/lib/monitor/closure'
import type { Claim } from '@/types/monitor'

function formatDate(iso: string | null): string {
  if (!iso) return ''
  return iso.slice(0, 10)
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
        {claim.scenario_type === 'hold' && (
          <div className="mb-1 flex items-center gap-1.5">
            <span
              data-testid="claim-hold-chip"
              className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
            >
              {claim.zone_display?.mode_label ?? '보유 관리'}
            </span>
            {claim.zone_display?.pnl_pct != null && (
              <span
                data-testid="claim-pnl-chip"
                className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
                  claim.zone_display.pnl_pct > 0
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                    : claim.zone_display.pnl_pct < 0
                      ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'
                }`}
              >
                {claim.zone_display.pnl_pct >= 0 ? '+' : ''}
                {claim.zone_display.pnl_pct.toFixed(1)}%
              </span>
            )}
            {claim.purchase_price && (
              <span className="text-[11px] text-gray-400">매입 {claim.purchase_price}</span>
            )}
          </div>
        )}
        <p className="text-sm text-gray-800 dark:text-gray-100">{claim.assertion}</p>
        {claim.deadline && <p className="mt-0.5 text-xs text-gray-400">마감 {claim.deadline}</p>}
        {!pending && (
          <p className="mt-1 text-xs text-gray-400" data-testid="claim-row-closure-summary">
            {claim.resolved_at ? `${formatDate(claim.resolved_at)} 마감` : '마감'}
            {typeof claim.closure_snapshot?.overall_score === 'number' &&
              ` · 동결 점수 ${claim.closure_snapshot.overall_score.toFixed(3)}`}
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
  const { data: alerts } = useMonitorAlerts(monitorId)
  const { user } = useAuth()

  const score = monitor?.latest_score ?? null
  const { data: spark } = useSparkline(monitorId, 30, score !== null)

  // close-preview는 무상태라 claim 상태 무관하게 호출 가능 — 이걸로 지표 "최신값"을 보강.
  const firstClaimId = claims?.[0]?.id ?? ''
  const { data: preview } = useClosePreview(firstClaimId, !!firstClaimId)
  const latestValueById = new Map((preview?.indicators ?? []).map((i) => [i.id, i.latest_value]))
  // MON-P2A T3: 지표별 충분성(신호 패널 배지). is_sufficient 미제공 시 표기 안 함.
  const sufficientById = new Map(
    (preview?.indicators ?? [])
      .filter((i) => i.is_sufficient !== undefined)
      .map((i) => [i.id, i.is_sufficient as boolean])
  )

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

  // 가격축: 활성 Claim 중 zone_display 있는 첫 건 → 스트립 존/손절여유 + 가격 사다리 패널.
  const zoneClaim = (claims ?? []).find((c) => c.status === 'active' && c.zone_display?.zone)

  // 전일 Δ = 스파크라인 최근 두 점 차(스트립 점수 토큰).
  const series = spark?.series ?? []
  const scoreDelta =
    series.length >= 2
      ? Math.round((series[series.length - 1].score - series[series.length - 2].score) * 100) / 100
      : null

  const journal = buildJournal({ sparkline: spark, alerts, monitor, claims })

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <Link
        href="/monitor"
        className="mb-3 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
        aria-label="목록으로"
      >
        <ArrowLeft size={16} /> 목록
      </Link>

      {/* T1 — 슬림 스트립 헤더 (6토큰 + 펼침 패널) */}
      <SlimStrip
        monitor={monitor}
        zoneClaim={zoneClaim}
        scoreDelta={scoreDelta}
        indicators={indicators ?? []}
        latestValueById={latestValueById}
        sufficientById={sufficientById}
      />

      {/* T2 — 일지 (지배 영역) */}
      <section className="mb-6" data-testid="detail-journal">
        <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">일지</h2>
        <div className="rounded-xl border border-gray-100 px-4 dark:border-gray-800">
          <JournalFeed entries={journal} />
        </div>
      </section>

      {/* 매수 시나리오 (마감 루프 보존) */}
      <section>
        <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
          매수 시나리오
        </h2>
        {(claims ?? []).length === 0 ? (
          <p className="text-sm text-gray-400">등록된 매수 시나리오가 없어요.</p>
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
