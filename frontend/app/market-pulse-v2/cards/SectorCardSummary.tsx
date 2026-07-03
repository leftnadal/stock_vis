'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { SectorCard, SectorCardItem } from '@/lib/api/marketPulseV2'
import { sectorFlow, sectorSentence } from '../meaning'
import { sectorTextClass } from '../sectorColor'
import { CardShell } from './CardShell'
import { SenseNote } from './SenseNote'

function formatPct(v: number) {
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

export function SectorCardSummary({
  data, labels, onOpen, sense,
}: { data: SectorCard | null; labels?: Record<string, string>; onOpen?: () => void; sense?: string | null }) {
  // 섹터 KO 라벨(없으면 symbol fallback — graceful). 라벨 소스는 labels prop 단일.
  const ko = (sym: string) => translate(`sector.${sym}`, labels, sym)
  // 유입=리더(rel_strength>0), 유출=후행(<0). flat은 제외(부분 데이터 graceful). 최대 2개씩.
  const inNames = data
    ? data.leaders.filter((r) => sectorFlow(r.rel_strength).dir === 'in').slice(0, 2).map((r) => ko(r.symbol))
    : []
  const outNames = data
    ? data.laggards.filter((r) => sectorFlow(r.rel_strength).dir === 'out').slice(0, 2).map((r) => ko(r.symbol))
    : []
  const sentence = data ? sectorSentence(inNames, outNames) : null

  return (
    <CardShell titleEn="Sector Flow" titleKo="섹터 흐름" onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">섹터 데이터 미생성</p>
      ) : (
        <div className="grid gap-2">
          {/* 한 줄 의미 문장 (없으면 생략 = 대기) */}
          {sentence ? <p className="text-sm text-slate-800">{sentence}</p> : null}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Section title="유입" rows={data.leaders} labels={labels} />
            <Section title="유출" rows={data.laggards} labels={labels} />
          </div>
          {/* 원시값(dispersion/rotation) 기본 숨김 → 펼침으로만 */}
          <details className="text-xs text-slate-500">
            <summary className="cursor-pointer select-none text-slate-400">원시 지표</summary>
            <p className="mt-2">
              {translate('metric.dispersion', labels, 'dispersion')} {data.cross_dispersion.toFixed(3)} ·{' '}
              {translate('metric.rotation', labels, 'rotation')} {data.rotation_index.toFixed(3)}
            </p>
          </details>
          {/* S4: 감각 유추(additive) — 없으면 미렌더 */}
          <SenseNote sense={sense} />
        </div>
      )}
    </CardShell>
  )
}

/** 섹터 행 — 종목별 유입/유출 톤(meaning.ts sectorFlow 단일소스). */
function Section({
  title, rows, labels,
}: { title: string; rows: SectorCardItem[]; labels?: Record<string, string> }) {
  return (
    <div>
      <p className="text-xs text-slate-500 mb-1">{title}</p>
      <ul className="space-y-1">
        {rows.map((r) => {
          const tone = sectorTextClass(r.rel_strength)
          return (
            <li key={r.symbol} className="flex items-baseline justify-between">
              <span className="font-mono text-sm text-slate-800">{translate(`sector.${r.symbol}`, labels, r.symbol)}</span>
              <span className={`text-xs font-medium ${tone}`}>{formatPct(r.rel_strength)}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
