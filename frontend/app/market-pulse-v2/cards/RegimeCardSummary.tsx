'use client'

import { translate } from '@/lib/i18n/marketPulse'
import type { RegimeCard } from '@/lib/api/marketPulseV2'
import { REGIME_MEANING, REGIME_TERM, REGIME_TONE, STAGE_ORDER } from '../meaning'
import { CardShell } from './CardShell'
import { SenseNote } from './SenseNote'

/** 전체 단계 수 (STAGE_ORDER 키 개수 — 단일소스). */
const TOTAL_STAGES = Object.keys(STAGE_ORDER).length // 5

/**
 * 5단계 게이지: 현재 국면 위치를 불릿으로 표시.
 * 심각도 오름차순(BULL_EXPANSION=0 … CRISIS=4).
 * stance_ok=false 또는 undefined면 숨김.
 */
function StageGauge({ regime }: { regime: string }) {
  const current = (STAGE_ORDER as Record<string, number>)[regime] ?? null
  const stageKeys = Object.keys(STAGE_ORDER) as (keyof typeof STAGE_ORDER)[]

  return (
    <div className="flex items-center gap-1 mt-2" aria-label={`국면 게이지 ${(current ?? 0) + 1}/${TOTAL_STAGES}`}>
      {stageKeys.map((key, idx) => {
        const isCurrent = idx === current
        return (
          <span
            key={key}
            className={`inline-block rounded-full transition-all ${
              isCurrent
                ? 'w-3 h-3 bg-slate-800'
                : 'w-2 h-2 bg-slate-300'
            }`}
            aria-hidden="true"
          />
        )
      })}
      {current !== null ? (
        <span className="text-xs text-slate-500 ml-1">
          {current + 1}/{TOTAL_STAGES}
        </span>
      ) : null}
    </div>
  )
}

// D-MP2-DEEPEN: 전조 블록 sub-component
interface ClosestShape {
  indicator: string
  op: string
  threshold: number
  actual: number
  to_threshold: number
}

function NextStageBlock({
  closest,
  nextStage,
  labels,
}: {
  closest: ClosestShape
  nextStage?: string | null
  labels?: Record<string, string>
}) {
  const near = Math.abs(closest.to_threshold) <= 0.2 * Math.abs(closest.threshold)
  const progressPct = Math.max(
    0,
    Math.min(100, (1 - Math.abs(closest.to_threshold) / Math.abs(closest.threshold)) * 100),
  )
  const sign = closest.to_threshold > 0 ? '+' : ''
  const containerCls = near
    ? 'mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs'
    : 'mt-3 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-xs'
  const barCls = near ? 'bg-amber-400' : 'bg-slate-400'
  const badgeTestId = near ? 'next-stage-imminent' : 'next-stage-margin'
  const badgeText = near ? '전환 임박' : '전환 여유'

  return (
    <div className={containerCls}>
      <div className="flex items-center justify-between mb-1">
        <span data-testid={badgeTestId} className={`font-semibold ${near ? 'text-amber-700' : 'text-slate-600'}`}>
          {badgeText}
        </span>
        {nextStage ? (
          <span data-testid="next-stage-label" className="text-slate-500">
            → {translate(`regime.${nextStage}`, labels, nextStage)}
          </span>
        ) : null}
      </div>
      <p data-testid="next-stage-info" className="text-slate-700 mb-1">
        전환까지 {closest.indicator} {closest.actual}/{closest.threshold} ({sign}{closest.to_threshold.toFixed(2)} 남음)
      </p>
      <div className="h-1.5 rounded bg-slate-200 overflow-hidden">
        <div
          data-testid="next-stage-progress"
          className={`h-full rounded ${barCls} transition-all`}
          style={{ width: `${progressPct}%` }}
        />
      </div>
    </div>
  )
}

/**
 * Regime hero — full-width 판단 카드.
 * D-MP2-SURFACE 변형1: hero로 승격, stance_copy + 5단계 게이지 추가.
 * 기존 표시(라벨·밴드·coverage·headline·SenseNote) 전부 유지.
 */
export function RegimeCardSummary({
  data, labels, onOpen, sense,
}: { data: RegimeCard | null; labels?: Record<string, string>; onOpen?: () => void; sense?: string | null }) {
  return (
    <CardShell titleEn="Market Regime" titleKo={`시장 ${REGIME_TERM}`} status={data?.status} onOpen={onOpen}>
      {!data ? (
        <p className="text-sm text-slate-400">{REGIME_TERM} 데이터 미생성</p>
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

          {/* D-MP2-SURFACE: 판단 카피 + 5단계 게이지 */}
          {data.stance_ok === true ? (
            <>
              <p className="mt-3 text-base font-bold text-slate-900" data-testid="stance-copy">
                {data.stance_copy}
              </p>
              <StageGauge regime={data.regime} />
              {/* D-MP2-DEEPEN: 전조 블록 */}
              {data.next_stage_closest != null ? (
                <NextStageBlock closest={data.next_stage_closest} nextStage={data.next_stage} labels={labels} />
              ) : null}
            </>
          ) : (
            <p className="mt-3 text-sm text-slate-400" data-testid="stance-fallback">
              {data.stance_copy ?? '판단 보류 — 데이터 지연/부족'}
            </p>
          )}

          {/* S4: 감각 유추(additive) — 없으면 미렌더, 밴드·raw 불변 */}
          <SenseNote sense={sense} />
        </div>
      )}
    </CardShell>
  )
}
