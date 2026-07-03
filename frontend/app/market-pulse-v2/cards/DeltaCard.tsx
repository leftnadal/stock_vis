'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { RegimeCard, SectorDelta } from '@/lib/api/marketPulseV2'
import { REGIME_TONE, REGIME_NEUTRAL_TONE } from '../meaning'
import { sectorTextClass } from '../sectorColor'
import { CardShell } from './CardShell'

interface DeltaCardProps {
  regime: RegimeCard | null
  sectorDeltas?: SectorDelta[]
  labels?: Record<string, string>
}

function formatMMDD(isoDate: string): string {
  // Parse ISO date string "YYYY-MM-DD" or ISO datetime → "MM-DD"
  const d = new Date(isoDate)
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(d.getUTCDate()).padStart(2, '0')
  return `${mm}-${dd}`
}

export function DeltaCard({ regime, sectorDeltas, labels }: DeltaCardProps) {
  const topThree = (sectorDeltas ?? []).slice(0, 3)
  const hasDeltas = topThree.length > 0
  const allFlat = hasDeltas && topThree.every((s) => s.rank_delta === 0)

  return (
    <CardShell titleEn="Delta" titleKo="어제와 달라진 것">
      {/* subtitle */}
      {sectorDeltas && sectorDeltas.length > 0 ? (
        <p data-testid="delta-subtitle" className="text-xs text-slate-400 mb-2">
          {formatMMDD(sectorDeltas[0].as_of)} vs 직전 거래일 {formatMMDD(sectorDeltas[0].vs_date)}
        </p>
      ) : null}

      {/* Block 1: regime transition */}
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-1 mb-1">국면 전환</p>
      {regime?.transition_from ? (
        <div className="flex items-center flex-wrap gap-1">
          <span
            data-testid="transition-from"
            className="line-through text-slate-400 text-xs rounded px-1.5 py-0.5 border border-slate-200 bg-slate-50"
          >
            {translate(`regime.${regime.transition_from}`, labels, regime.transition_from)}
          </span>
          <span className="mx-2 text-slate-400">→</span>
          <span
            data-testid="transition-to"
            className={`text-xs rounded px-1.5 py-0.5 border ${REGIME_TONE[regime.regime as keyof typeof REGIME_TONE] ?? REGIME_NEUTRAL_TONE}`}
          >
            {translate(`regime.${regime.regime}`, labels, regime.regime)}
          </span>
        </div>
      ) : (
        <p data-testid="no-transition" className="text-sm text-slate-400">변화 없음</p>
      )}

      {/* Block 2: sector rank movements */}
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-3 mb-1">섹터 순위 변동</p>
      {!hasDeltas ? (
        <p data-testid="no-sector-data" className="text-sm text-slate-400">비교할 어제 데이터 없음</p>
      ) : allFlat ? (
        <p data-testid="no-rank-change" className="text-sm text-slate-400">순위 변동 없음</p>
      ) : (
        <div className="space-y-1">
          {topThree.map((item) => (
            <div data-testid="sector-row" key={item.sector} className="flex items-center gap-2 text-sm">
              <span className="text-slate-700 flex-1">
                {translate(`sector.${item.sector}`, labels, item.sector)}
              </span>
              <span data-testid="rank-delta-badge" className={`font-semibold ${sectorTextClass(item.rank_delta)}`}>
                {item.rank_delta > 0 ? `▲${item.rank_delta}` : `▼${Math.abs(item.rank_delta)}`}
              </span>
              <span data-testid="rank-trail" className="text-slate-400 text-xs">
                {item.prev_rank}위 → {item.rank}위
              </span>
            </div>
          ))}
        </div>
      )}
    </CardShell>
  )
}
