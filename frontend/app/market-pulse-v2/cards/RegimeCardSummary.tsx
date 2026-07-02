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
