'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { ConcentrationCard } from '@/lib/api/marketPulseV2'
import { CONCENTRATION_SCALE, concentrationBand, concentrationSentence } from '../meaning'
import { CardShell } from './CardShell'
import { SenseNote } from './SenseNote'

export function ConcentrationCardSummary({
  data, labels, onOpen, sense,
}: { data: ConcentrationCard | null; labels?: Record<string, string>; onOpen?: () => void; sense?: string | null }) {
  // MP-UX-S5: 의미밴드는 top10_weight 기준(R02 0.40 grounded 앵커, meaning.ts 단일소스).
  const band = data ? concentrationBand(data.top10_weight) : null
  return (
    <CardShell titleEn="Concentration" titleKo="집중도" onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">집중도 데이터 미생성</p>
      ) : band == null ? (
        // null → 대기(밴드·값·바 미렌더, 0 변환 금지)
        <p className="text-sm text-slate-400">집중도 데이터 수집 대기 중</p>
      ) : (
        <div className="grid gap-2">
          {/* 의미밴드 ● 현 위치 (4구간, 활성만 톤) */}
          <BandScale activeIndex={band.index} />
          <p className="text-sm text-slate-800">{concentrationSentence(band)}</p>
          {/* 리스크 렌즈 ① 유효 종목 수(1/HHI) — 즉시 파생, HHI>0 가드(D-CONC-RISK-LENSES). */}
          {data.hhi > 0 ? (
            <p className="text-xs text-slate-500">
              유효 종목 수 ≈ {Math.round(1 / data.hhi)}종 <span className="text-slate-400">(1/허핀달)</span>
            </p>
          ) : null}
          {/* 원시값(top5/top10/HHI)은 기본 숨김 → 펼침으로만 */}
          <details className="text-xs text-slate-500">
            <summary className="cursor-pointer select-none text-slate-400">원시 지표</summary>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              <Metric labelKey="metric.top5" fallback="top5" value={data.top5_weight} labels={labels} />
              <Metric labelKey="metric.top10" fallback="top10" value={data.top10_weight} labels={labels} />
              <Metric labelKey="metric.hhi" fallback="HHI" value={data.hhi} digits={4} percent={false} labels={labels} />
            </div>
            {data.top_holdings.length ? (
              <ul className="mt-2 space-y-0.5 text-slate-600">
                {data.top_holdings.slice(0, 5).map((h) => (
                  <li key={h.symbol} className="flex justify-between">
                    <span className="font-mono">{h.symbol}</span>
                    <span>{(h.weight * 100).toFixed(2)}%</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </details>
          {/* S4: 감각 유추(additive) — 없으면 미렌더 */}
          <SenseNote sense={sense} />
        </div>
      )}
    </CardShell>
  )
}

/** 집중도 4밴드 위치 표시 — 활성 구간만 톤, 나머지 muted. 색·라벨은 meaning.ts 단일소스. */
function BandScale({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="flex gap-1" role="img" aria-label={`집중도: ${CONCENTRATION_SCALE[activeIndex]?.label ?? ''}`}>
      {CONCENTRATION_SCALE.map((b) => {
        const active = b.index === activeIndex
        return (
          <div
            key={b.key}
            className={`flex-1 rounded border px-1 py-0.5 text-center text-[10px] ${
              active ? b.tone : 'border-slate-200 bg-slate-50 text-slate-300'
            }`}
            title={b.label}
          >
            {active ? `● ${b.label}` : b.label}
          </div>
        )
      })}
    </div>
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
