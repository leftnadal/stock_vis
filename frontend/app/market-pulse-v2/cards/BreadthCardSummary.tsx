'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { BreadthCard } from '@/lib/api/marketPulseV2'
import { breadthBand } from '../meaning'
import { CardShell } from './CardShell'

/** 보조 부제(변형 A) — 신고저 우위 + AD 추세 화살표. 빈 신호는 생략. */
function breadthSubcue(data: BreadthCard, labels?: Record<string, string>): string {
  const parts: string[] = []
  if (data.new_high_52w > data.new_low_52w) parts.push(translate('breadth.cue.high_lead', labels, '신고가 우위'))
  else if (data.new_low_52w > data.new_high_52w) parts.push(translate('breadth.cue.low_lead', labels, '신저가 우위'))
  parts.push(data.ad_line_change > 0 ? 'AD ↑' : data.ad_line_change < 0 ? 'AD ↓' : 'AD →')
  return parts.join(' · ')
}

export function BreadthCardSummary({
  data, labels, onOpen,
}: { data: BreadthCard | null; labels?: Record<string, string>; onOpen?: () => void }) {
  // MP-UX: 의미밴드 1줄(색=meaning.ts FLOW_TONE 단일소스, 문구=i18n breadth.*) + raw 유지(additive).
  const bb = data ? breadthBand(data) : null
  return (
    <CardShell titleEn="Market Breadth" titleKo="시장 폭" onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">Breadth 데이터 미생성</p>
      ) : (
        <div className="grid gap-2">
          {bb ? (
            <p className={`rounded border px-2 py-1 text-sm ${bb.tone}`}>
              {translate(`breadth.${bb.band}`, labels, bb.band)}
              <span className="ml-1 text-xs opacity-80">· {breadthSubcue(data, labels)}</span>
            </p>
          ) : null}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <Stat label="상승" value={data.advance} tone="text-emerald-600" />
            <Stat label="하락" value={data.decline} tone="text-rose-600" />
            <Stat label="신고가 52w" value={data.new_high_52w} tone="text-emerald-500" />
            <Stat label="신저가 52w" value={data.new_low_52w} tone="text-rose-500" />
            <Stat
              label={translate('metric.ad_line', labels, 'AD-line')}
              value={data.ad_line}
              sub={data.ad_line_change >= 0 ? `+${data.ad_line_change}` : `${data.ad_line_change}`}
              tone="text-slate-700"
            />
          </div>
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
