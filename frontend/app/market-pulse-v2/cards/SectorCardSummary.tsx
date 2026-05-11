'use client'

import type { SectorCard } from '@/lib/api/marketPulseV2'
import { CardShell } from './CardShell'

function formatPct(v: number) {
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

export function SectorCardSummary({ data, onOpen }: { data: SectorCard | null; onOpen?: () => void }) {
  return (
    <CardShell titleEn="Sector Flow" titleKo="섹터 흐름" onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">섹터 데이터 미생성</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 text-sm">
          <Section title="리더" rows={data.leaders} tone="text-emerald-600" />
          <Section title="후행" rows={data.laggards} tone="text-rose-600" />
        </div>
      )}
      {data ? (
        <p className="text-xs text-slate-500 mt-2">
          dispersion {data.cross_dispersion.toFixed(3)} · rotation {data.rotation_index.toFixed(3)}
        </p>
      ) : null}
    </CardShell>
  )
}

function Section({ title, rows, tone }: { title: string; rows: SectorCard['leaders']; tone: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500 mb-1">{title}</p>
      <ul className="space-y-1">
        {rows.map((r) => (
          <li key={r.symbol} className="flex items-baseline justify-between">
            <span className="font-mono text-sm text-slate-800">{r.symbol}</span>
            <span className={`text-xs font-medium ${tone}`}>{formatPct(r.rel_strength)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
