'use client'

import type { BreadthCard } from '@/lib/api/marketPulseV2'
import { CardShell } from './CardShell'

export function BreadthCardSummary({
  data, onOpen,
}: { data: BreadthCard | null; onOpen?: () => void }) {
  return (
    <CardShell titleEn="Market Breadth" titleKo="시장 폭" onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">Breadth 데이터 미생성</p>
      ) : (
        <div className="grid grid-cols-2 gap-2 text-sm">
          <Stat label="상승" value={data.advance} tone="text-emerald-600" />
          <Stat label="하락" value={data.decline} tone="text-rose-600" />
          <Stat label="신고가 52w" value={data.new_high_52w} tone="text-emerald-500" />
          <Stat label="신저가 52w" value={data.new_low_52w} tone="text-rose-500" />
          <Stat
            label="AD-line"
            value={data.ad_line}
            sub={data.ad_line_change >= 0 ? `+${data.ad_line_change}` : `${data.ad_line_change}`}
            tone="text-slate-700"
          />
        </div>
      )}
    </CardShell>
  )
}

function Stat({ label, value, sub, tone }: { label: string; value: number; sub?: string; tone?: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-base font-semibold ${tone ?? ''}`}>
        {value.toLocaleString()}
        {sub ? <span className="ml-1 text-xs text-slate-500">{sub}</span> : null}
      </p>
    </div>
  )
}
