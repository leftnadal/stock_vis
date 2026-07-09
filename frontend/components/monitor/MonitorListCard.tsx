'use client'

import Link from 'next/link'

import { ArrowIndicator } from '@/components/monitor/ArrowIndicator'
import { MoonPhase } from '@/components/monitor/MoonPhase'
import { ddayLabel, stateMeta } from '@/lib/monitor/display'
import type { Monitor } from '@/types/monitor'

const SCOPE_LABEL: Record<Monitor['scope'], string> = {
  market: '시장',
  sector: '섹터',
  theme: '테마',
  fund: '펀드',
  stock: '종목',
}

const TONE_CLASS: Record<string, string> = {
  danger: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  warn: 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  watch: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  stable: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300',
}

export function MonitorListCard({ monitor }: { monitor: Monitor }) {
  const score = monitor.latest_score ?? null
  const display = monitor.display // API 파생값 (degree·color·label·phase), score 없으면 null
  const meta = stateMeta(monitor.current_state)
  const dday = ddayLabel(monitor.next_deadline)

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
          <span className={`rounded px-1.5 py-0.5 font-medium ${TONE_CLASS[meta.tone]}`}>
            {meta.label}
          </span>
          {typeof monitor.indicator_count === 'number' && (
            <span className="text-gray-400">지표 {monitor.indicator_count}</span>
          )}
          {dday && (
            <span className="font-medium text-gray-600 dark:text-gray-300">{dday}</span>
          )}
        </div>
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
