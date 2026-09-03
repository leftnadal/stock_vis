'use client'

import type { TickerItem } from '@/lib/api/marketPulseV2'
import { DIRECTION_TEXT } from '@/components/common/colorSemantics'

// A-3(HUB-V02-S1): FMP 현물 심볼 → 한글 표기. 금·은은 GCUSD/SIUSD가 실데이터 소스
//   (ETF GLD/SLV는 0행 — 배선 교정으로 스트립 진입 예정). 원 심볼은 사용자에게 불친절.
const SYMBOL_LABEL: Record<string, string> = { GCUSD: '금', SIUSD: '은' }

function formatPct(v: number | null) {
  if (v === null || Number.isNaN(v)) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

// COLOR-STAGE2(한국축): 가격 상승=긍정→rose / 하락=부정→sky. 부호(+/−) 라벨 병기 불변.
function tone(v: number | null) {
  if (v === null) return 'text-slate-400'
  if (v > 0) return DIRECTION_TEXT.positive
  if (v < 0) return DIRECTION_TEXT.negative
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
            <span className="font-semibold text-slate-700">{SYMBOL_LABEL[it.symbol] ?? it.symbol}</span>
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
