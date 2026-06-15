'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { AnomalySection } from '@/lib/api/marketPulseV2'
import { MODE_MEANING } from '../meaning'

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
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
