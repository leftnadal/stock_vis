'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { RegimeCard, SectorDelta, AnomalyDelta } from '@/lib/api/marketPulseV2'
import { REGIME_TONE, REGIME_NEUTRAL_TONE, FLOW_TONE } from '../meaning'
import { sectorTextClass } from '../sectorColor'
import { CardShell } from './CardShell'

interface DeltaCardProps {
  regime: RegimeCard | null
  sectorDeltas?: SectorDelta[]
  anomalyDelta?: AnomalyDelta
  labels?: Record<string, string>
}

function formatMMDD(isoDate: string): string {
  // Parse ISO date string "YYYY-MM-DD" or ISO datetime → "MM-DD"
  const d = new Date(isoDate)
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(d.getUTCDate()).padStart(2, '0')
  return `${mm}-${dd}`
}

function ruleLabel(ruleId: string, labels?: Record<string, string>): string {
  return translate(`rule.${ruleId}`, labels, ruleId)
}

export function DeltaCard({ regime, sectorDeltas, anomalyDelta, labels }: DeltaCardProps) {
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

      {/* Block 3: 이상 신호 변화 (MP2-DELTA Slice 2) — 4상태. FE 날짜 연산 없음(서버값 표기). */}
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-3 mb-1">이상 신호 변화</p>
      {!anomalyDelta || anomalyDelta.state === 'no_history' ? (
        <p data-testid="anomaly-no-history" className="text-sm text-slate-400">이상 신호 기록 없음</p>
      ) : anomalyDelta.state === 'fired' ? (
        <div className="space-y-1">
          <div className="flex items-center flex-wrap gap-1">
            {anomalyDelta.new_rules.map((r) => (
              <span
                key={`new-${r}`}
                data-testid="anomaly-new-rule"
                className={`text-xs rounded px-1.5 py-0.5 border ${FLOW_TONE.warn}`}
              >
                + {ruleLabel(r, labels)} (신규)
              </span>
            ))}
            {anomalyDelta.gone_rules.map((r) => (
              <span
                key={`gone-${r}`}
                data-testid="anomaly-gone-rule"
                className="line-through text-slate-400 text-xs rounded px-1.5 py-0.5 border border-slate-200 bg-slate-50"
              >
                {ruleLabel(r, labels)} (소멸)
              </span>
            ))}
            {anomalyDelta.new_rules.length === 0 && anomalyDelta.gone_rules.length === 0 ? (
              <span data-testid="anomaly-no-change" className="text-sm text-slate-400">직전 발동일과 동일</span>
            ) : null}
          </div>
          {anomalyDelta.vs_fired_date ? (
            <p data-testid="anomaly-fired-note" className="text-xs text-slate-400">
              직전 발동일 {formatMMDD(anomalyDelta.vs_fired_date)} 대비
            </p>
          ) : null}
        </div>
      ) : anomalyDelta.state === 'resolving' ? (
        <div className="space-y-1">
          <div className="flex items-center flex-wrap gap-1">
            {anomalyDelta.resolved_rules.map((r) => (
              <span
                key={`resolved-${r}`}
                data-testid="anomaly-resolved-rule"
                className={`text-xs rounded px-1.5 py-0.5 border ${FLOW_TONE.calm}`}
              >
                ✓ {ruleLabel(r, labels)} 해소
              </span>
            ))}
          </div>
          {anomalyDelta.last_fired_date ? (
            <p data-testid="anomaly-resolving-note" className="text-xs text-slate-400">
              {formatMMDD(anomalyDelta.last_fired_date)} 발동분 — 이후 재발동 없음
            </p>
          ) : null}
        </div>
      ) : (
        <p data-testid="anomaly-quiet" className="text-sm text-slate-400">
          발동 중인 이상 신호 없음
          {anomalyDelta.last_fired_date ? ` · 마지막 발동 ${formatMMDD(anomalyDelta.last_fired_date)}` : ''}
        </p>
      )}
    </CardShell>
  )
}
