'use client'

import Link from 'next/link'

import { ArrowIndicator } from '@/components/monitor/ArrowIndicator'
import { MoonPhase } from '@/components/monitor/MoonPhase'
import { StateBandSparkline } from '@/components/monitor/StateBandSparkline'
import { VerdictBadge } from '@/components/monitor/VerdictBadge'
import { useSparkline } from '@/hooks/useMonitor'
import { frozenScore, outcomeToVerdict, type ClaimClosureSummary } from '@/lib/monitor/closure'
import { STATE_TONE_CLASS, ddayLabel, stateMeta } from '@/lib/monitor/display'
import type { Monitor } from '@/types/monitor'

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

interface MonitorListCardProps {
  monitor: Monitor
  // Claim 마감 파생 요약(0.3) — 없으면 기존(마감 무관) 렌더와 동일.
  closureSummary?: ClaimClosureSummary
  // "판정자" 표시용 — AuthContext는 카드가 직접 참조하지 않고 상위(페이지)에서 주입.
  judgeUsername?: string | null
}

export function MonitorListCard({ monitor, closureSummary, judgeUsername }: MonitorListCardProps) {
  const score = monitor.latest_score ?? null
  const display = monitor.display // API 파생값 (degree·color·label·phase), score 없으면 null
  const meta = stateMeta(monitor.current_state)
  const dday = ddayLabel(monitor.next_deadline)
  // score 없는(warming_up) 모니터는 스파크라인 조회 자체를 생략. 동결 카드도 조회는 유지(회색 처리만).
  const { data: spark } = useSparkline(monitor.id, 30, score !== null)

  // 0.4 동결 카드: 이 모니터의 Claim이 전부 resolved → 서리 렌더(중복 렌더 로직 없이 조건부 분기만).
  if (closureSummary?.isFullyClosed) {
    const claim = closureSummary.lastResolvedClaim
    // 동결값 우선(P1.5): resolved Claim의 closure_snapshot, 없으면 live 폴백.
    const frozen = frozenScore(claim, score)
    return (
      <Link
        href={`/monitor/${monitor.id}`}
        className="flex items-center gap-4 rounded-xl border border-gray-200 bg-gray-50 p-4 transition hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800/60"
        data-testid="monitor-card"
        data-frozen="true"
      >
        <div className="relative flex-shrink-0 opacity-50 grayscale">
          <MoonPhase score={frozen} label={display?.phase_label} size="md" />
          <span className="absolute -right-1 -top-1 text-sm" aria-hidden="true">
            ❄️
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-500 dark:bg-gray-700 dark:text-gray-400">
              {SCOPE_LABEL[monitor.scope]}
            </span>
            <h3 className="truncate font-medium text-gray-600 dark:text-gray-300">
              {monitor.name}
            </h3>
          </div>
          <p
            className="mt-1 truncate text-xs text-gray-400"
            data-testid="monitor-card-frozen-meta"
          >
            {claim?.resolved_at ? `${formatDate(claim.resolved_at)} 마감` : '마감'}
            {typeof frozen === 'number' && ` · 동결 점수 ${frozen.toFixed(3)}`}
            {judgeUsername && ` · 판정자 ${judgeUsername}`}
          </p>
          {spark && (
            <div className="mt-2 grayscale">
              <StateBandSparkline
                series={spark.series}
                bands={spark.bands}
                transitions={spark.transitions}
              />
            </div>
          )}
        </div>

        {claim && <VerdictBadge verdict={outcomeToVerdict(claim.outcome)} />}
      </Link>
    )
  }

  return (
    <Link
      href={`/monitor/${monitor.id}`}
      className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-4 transition hover:border-gray-300 hover:shadow-sm dark:border-gray-700 dark:bg-gray-800"
      data-testid="monitor-card"
    >
      <MoonPhase score={score} label={display?.phase_label} size="md" />

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-500 dark:bg-gray-700 dark:text-gray-400">
            {SCOPE_LABEL[monitor.scope]}
          </span>
          <h3 className="truncate font-medium text-gray-900 dark:text-gray-100">
            {monitor.name}
          </h3>
        </div>
        {monitor.resolved_label && (
          <p className="truncate text-xs text-gray-500 dark:text-gray-400">
            {monitor.resolved_label}
          </p>
        )}
        <div className="mt-1 flex items-center gap-2 text-xs">
          <span className={`rounded px-1.5 py-0.5 font-medium ${STATE_TONE_CLASS[meta.tone]}`}>
            {meta.label}
          </span>
          {typeof monitor.indicator_count === 'number' && (
            <span className="text-gray-400">지표 {monitor.indicator_count}</span>
          )}
          {dday && (
            <span className="font-medium text-gray-600 dark:text-gray-300">{dday}</span>
          )}
          {closureSummary && closureSummary.resolved > 0 && !closureSummary.isFullyClosed && (
            <span
              className="text-gray-400"
              data-testid="monitor-card-partial-closed"
            >
              {closureSummary.total}중 {closureSummary.resolved}마감
            </span>
          )}
        </div>
        {spark && (
          <div className="mt-2">
            <StateBandSparkline
              series={spark.series}
              bands={spark.bands}
              transitions={spark.transitions}
            />
          </div>
        )}
      </div>

      {display ? (
        <ArrowIndicator
          degree={display.degree}
          color={display.color}
          label={display.label}
          size="md"
        />
      ) : (
        <span className="text-gray-300" aria-label="데이터 부족">
          —
        </span>
      )}
    </Link>
  )
}
