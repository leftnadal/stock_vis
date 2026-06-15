'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { RegimeCard } from '@/lib/api/marketPulseV2'
import { REGIME_MEANING, REGIME_TONE } from '../meaning'
import { CardShell } from './CardShell'

export function RegimeCardSummary({
  data, labels, onOpen,
}: { data: RegimeCard | null; labels?: Record<string, string>; onOpen?: () => void }) {
  return (
    <CardShell titleEn="Market Regime" titleKo="시장 국면" status={data?.status} onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">레짐 데이터 미생성</p>
      ) : (
        <div>
          <p className="text-lg font-semibold text-slate-900">
            {translate(`regime.${data.regime}`, labels, data.regime)}
          </p>
          {/* MP-UX-S2: 단계 의미 밴드 (rules.yaml 5단계 → 의미 문구, 단계별 색). 표시만 추가. */}
          {REGIME_MEANING[data.regime] ? (
            <div className={`mt-1 rounded border px-2 py-1 text-xs ${REGIME_TONE[data.regime] ?? ''}`}>
              {REGIME_MEANING[data.regime]}
            </div>
          ) : null}
          <p className="text-xs text-slate-500 mt-1">
            {translate('metric.coverage', labels, 'coverage')} {(data.coverage * 100).toFixed(0)}%
            {data.transitioned ? ' · 전환' : ''}
          </p>
          {data.headline ? <p className="text-sm text-slate-700 mt-2">{data.headline}</p> : null}
        </div>
      )}
    </CardShell>
  )
}
