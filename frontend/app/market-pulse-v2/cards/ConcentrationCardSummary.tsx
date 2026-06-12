'use client'

import type { ConcentrationCard } from '@/lib/api/marketPulseV2'
import { CardShell } from './CardShell'

export function ConcentrationCardSummary({ data, onOpen }: { data: ConcentrationCard | null; onOpen?: () => void }) {
  return (
    <CardShell titleEn="Concentration" titleKo="집중도" onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">집중도 데이터 미생성</p>
      ) : (
        <div className="grid gap-2">
          <div className="grid grid-cols-3 gap-2 text-center">
            <Metric label="top5" value={data.top5_weight} />
            <Metric label="top10" value={data.top10_weight} />
            <Metric label="HHI" value={data.hhi} digits={4} />
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

function Metric({ label, value, digits = 2 }: { label: string; value: number; digits?: number }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-base font-semibold text-slate-900">
        {label === 'HHI' ? value.toFixed(digits) : `${(value * 100).toFixed(digits)}%`}
      </p>
    </div>
  )
}
