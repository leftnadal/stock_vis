'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { AnomalySection, AnomalyItem } from '@/lib/api/marketPulseV2'
import { MODE_MEANING } from '../meaning'

/** sector.* 심볼 → 사람 읽는 라벨 (translate 없는 경우 심볼 그대로). */
function sectorLabel(symbol: string, labels?: Record<string, string>): string {
  return labels?.[`sector.${symbol}`] ?? symbol
}

interface AnomalyEvidenceProps {
  f: AnomalyItem
  labels?: Record<string, string>
}

function EvidenceChips({ f, labels }: AnomalyEvidenceProps) {
  const thresholdVal = Object.values(f.threshold ?? {})[0]
  const chips: Array<{ label: string; hot: boolean }> = []

  // 분산 칩: rule actual vs threshold
  if (thresholdVal !== undefined) {
    const hot = f.actual >= thresholdVal
    chips.push({ label: `분산 ${f.actual.toFixed(2)}/${thresholdVal}`, hot })
  }

  // 상위10비중
  const top10 = f.evidence?.top10_weight
  if (top10 != null) {
    chips.push({ label: `상위10 ${(top10 * 100).toFixed(1)}%`, hot: false })
  }

  // VIX변화
  const vix = f.evidence?.vix_change_pct
  if (vix != null) {
    const sign = vix > 0 ? '+' : ''
    chips.push({ label: `VIX ${sign}${vix.toFixed(1)}%`, hot: false })
  }

  // 최대섹터z
  const sectorZ = f.evidence?.max_abs_sector_z
  if (sectorZ != null) {
    chips.push({ label: `섹터z ${sectorZ.toFixed(2)}`, hot: false })
  }

  // 급등섹터 (hot 강조)
  const extreme = f.evidence?.sector_extreme_symbol
  if (extreme != null) {
    chips.push({ label: sectorLabel(extreme, labels), hot: true })
  }

  if (chips.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {chips.map((chip) => (
        <span
          key={chip.label}
          className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${
            chip.hot
              ? 'bg-rose-100 text-rose-700'
              : 'bg-slate-100 text-slate-600'
          }`}
        >
          {chip.label}
        </span>
      ))}
    </div>
  )
}

const MODE_TONE: Record<string, string> = {
  ANOMALY: 'border-rose-300 bg-rose-50',
  HYBRID: 'border-amber-300 bg-amber-50',
  CALM: 'border-slate-200 bg-slate-50',
}

const MODE_TEXT: Record<string, string> = {
  ANOMALY: 'text-rose-700',
  HYBRID: 'text-amber-700',
  CALM: 'text-slate-600',
}

export function AnomalyPanel({ data, labels }: { data: AnomalySection; labels?: Record<string, string> }) {
  const tone = MODE_TONE[data.mode] ?? MODE_TONE.CALM
  const textTone = MODE_TEXT[data.mode] ?? MODE_TEXT.CALM
  return (
    <section className={`mt-4 rounded-lg border ${tone} p-4`}>
      <header className="flex items-center gap-2 mb-2">
        <span className={`text-xs font-semibold uppercase ${textTone}`}>
          {translate(`mode.${data.mode}`, labels, data.mode)}
        </span>
        {data.fired.length > 0 ? (
          <span className="text-xs text-slate-500">{data.fired.length}개 시그널</span>
        ) : null}
      </header>
      {/* MP-UX-S2: 모드 의미 밴드 (CALM/HYBRID/ANOMALY → 의미 문구). 색은 기존 textTone 재사용. */}
      <p className={`text-xs mb-2 ${textTone}`}>{MODE_MEANING[data.mode] ?? ''}</p>
      <dl className="grid gap-1.5 text-sm">
        <div>
          <dt className="text-xs text-slate-500">총평</dt>
          <dd className="text-slate-800">{data.overview || '—'}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">주목 섹터</dt>
          <dd className="text-slate-800">{data.sector_highlight || '—'}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">포트폴리오</dt>
          <dd className="text-slate-800">{data.portfolio_action || '—'}</dd>
        </div>
      </dl>
      {data.fired.length > 0 ? (
        <ul className="mt-3 grid gap-1 text-xs">
          {data.fired.map((f) => (
            <li key={`${f.rule_id}-${f.actual}`} className="text-slate-600">
              <span className="font-mono mr-1">{f.rule_id}</span>
              {translate(`rule.${f.rule_id}`, labels, f.headline)} ·{' '}
              <span className="font-medium text-slate-800">{f.actual.toFixed(3)}</span>
              {/* MP-UX-S2: 경보선 = fired[].threshold(기바인딩, FE만, 임계 하드코딩 0). rule 모두 op '>=' (engine.py) */}
              {Object.values(f.threshold ?? {})[0] !== undefined ? (
                <span className="text-slate-400"> (경보선 {Object.values(f.threshold ?? {})[0]} 초과)</span>
              ) : null}
              <EvidenceChips f={f} labels={labels} />
              {f.paired_news_title && f.paired_news_url ? (
                <a
                  href={f.paired_news_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block mt-1 text-[10px] text-blue-600 underline hover:text-blue-800"
                >
                  🔗 {f.paired_news_title}
                </a>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
