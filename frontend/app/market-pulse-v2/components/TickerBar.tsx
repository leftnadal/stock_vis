'use client'

import type { TickerItem } from '@/lib/api/marketPulseV2'

function formatPct(v: number | null) {
  if (v === null || Number.isNaN(v)) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

function tone(v: number | null) {
  if (v === null) return 'text-slate-400'
  if (v > 0) return 'text-emerald-600'
  if (v < 0) return 'text-rose-600'
  return 'text-slate-500'
}

export function TickerBar({ items }: { items: TickerItem[] }) {
  if (!items.length) {
    return <div className="text-xs text-slate-400 px-1 py-2">Ticker · 가격 데이터 미수집</div>
  }
  return (
    <div className="overflow-x-auto sticky top-0 bg-white/95 backdrop-blur z-10 border-b border-slate-200">
      <ul className="flex gap-4 px-2 py-2 whitespace-nowrap text-sm">
        {items.map((it) => (
          <li key={it.symbol} className="flex items-baseline gap-1.5">
            <span className="font-semibold text-slate-700">{it.symbol}</span>
            <span className="text-slate-500">
              {it.last_close !== null ? it.last_close.toFixed(2) : '—'}
            </span>
            <span className={tone(it.change_pct)}>{formatPct(it.change_pct)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
