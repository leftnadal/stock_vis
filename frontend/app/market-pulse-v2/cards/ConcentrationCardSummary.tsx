'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { ConcentrationCard } from '@/lib/api/marketPulseV2'
import { CardShell } from './CardShell'

export function ConcentrationCardSummary({
  data, labels, onOpen,
}: { data: ConcentrationCard | null; labels?: Record<string, string>; onOpen?: () => void }) {
  return (
    <CardShell titleEn="Concentration" titleKo="집중도" onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">집중도 데이터 미생성</p>
      ) : (
        <div className="grid gap-2">
          <div className="grid grid-cols-3 gap-2 text-center">
            <Metric labelKey="metric.top5" fallback="top5" value={data.top5_weight} labels={labels} />
            <Metric labelKey="metric.top10" fallback="top10" value={data.top10_weight} labels={labels} />
            <Metric labelKey="metric.hhi" fallback="HHI" value={data.hhi} digits={4} percent={false} labels={labels} />
          </div>
          {data.top_holdings.length ? (
            <ul className="text-xs text-slate-600 space-y-0.5">
              {data.top_holdings.slice(0, 5).map((h) => (
                <li key={h.symbol} className="flex justify-between">
                  <span className="font-mono">{h.symbol}</span>
                  <span>{(h.weight * 100).toFixed(2)}%</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </CardShell>
  )
}

function Metric({
  labelKey, fallback, value, digits = 2, percent = true, labels,
}: {
  labelKey: string
  fallback: string
  value: number
  digits?: number
  percent?: boolean
  labels?: Record<string, string>
}) {
  return (
    <div>
      <p className="text-xs text-slate-500">{translate(labelKey, labels, fallback)}</p>
      <p className="text-base font-semibold text-slate-900">
        {percent ? `${(value * 100).toFixed(digits)}%` : value.toFixed(digits)}
      </p>
    </div>
  )
}
