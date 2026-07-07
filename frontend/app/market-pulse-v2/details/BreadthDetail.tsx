'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { BreadthDetail as Detail } from '@/lib/api/marketPulseV2'
import { breadthBand } from '../meaning'
import { DIRECTION_TEXT, DIRECTION_TEXT_SOFT } from '../colorSemantics'
import { BreadthTrajectory } from './BreadthTrajectory'

export function BreadthDetail({
  payload,
  labels,
  transitionDates = [],
}: {
  payload: Detail
  labels?: Record<string, string>
  // MP2-TREND S2: 전환일 세로선(regime 계약 공용 소비 — 컨테이너가 조회해 전달). 없으면 무영향(E4).
  transitionDates?: string[]
}) {
  if (!payload.available) {
    return <p className="text-sm text-slate-500">시장 폭 상세 데이터가 아직 준비되지 않았습니다.</p>
  }

  // MP-UX: 상세 헤드라인에도 의미밴드 일관 표시(카드 face와 동일 단일소스, additive).
  const bb = breadthBand({
    advance: payload.advance ?? 0,
    decline: payload.decline ?? 0,
    new_high_52w: payload.new_high_52w ?? 0,
    new_low_52w: payload.new_low_52w ?? 0,
    ad_line_change: payload.ad_line_change ?? 0,
  })

  return (
    <div className="grid gap-4">
      {bb ? (
        <p className={`rounded border px-2 py-1 text-sm ${bb.tone}`}>
          {translate(`breadth.${bb.band}`, labels, bb.band)}
        </p>
      ) : null}
      <header className="grid grid-cols-3 gap-2 text-center">
        <Cell label="상승" value={payload.advance ?? 0} tone={DIRECTION_TEXT.positive} />
        <Cell label="하락" value={payload.decline ?? 0} tone={DIRECTION_TEXT.negative} />
        <Cell
          label={translate('metric.ad_line', labels, 'AD-line')}
          value={payload.ad_line ?? 0}
          sub={(payload.ad_line_change ?? 0) >= 0 ? `+${payload.ad_line_change}` : `${payload.ad_line_change}`}
        />
      </header>

      {/* MP2-TREND S2: 단순 AD-line 차트 → 궤적(A/D + 기준선 MA20 + 전환일). 공용 MultiLineTrendChart. */}
      <BreadthTrajectory payload={payload} transitionDates={transitionDates} />

      <div>
        <p className="text-xs text-slate-500 mb-1">신고가 / 신저가 (52주)</p>
        <div className="grid grid-cols-2 gap-2 text-center">
          <Cell label="52w 신고가" value={payload.new_high_52w ?? 0} tone={DIRECTION_TEXT_SOFT.positive} />
          <Cell label="52w 신저가" value={payload.new_low_52w ?? 0} tone={DIRECTION_TEXT_SOFT.negative} />
        </div>
      </div>
    </div>
  )
}

function Cell({ label, value, sub, tone }: { label: string; value: number; sub?: string; tone?: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-lg font-semibold ${tone ?? 'text-slate-900'}`}>
        {value.toLocaleString()}
        {sub ? <span className="ml-1 text-xs text-slate-500">{sub}</span> : null}
      </p>
    </div>
  )
}
