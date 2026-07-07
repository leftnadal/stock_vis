'use client'

/**
 * MP2-TREND S3(R1) — 국면 재료 판정-거리 소형 다중(옵션 B, H3 뷰모드).
 *
 * 세그먼트 컨트롤 [판정 거리(raw) | 이상도(z) 🔒]. z 탭 = 예약 슬롯(placeholder) — 실제 z 뷰는
 *   S4(트리거 B-1 land)로 이연. 예약 탭 노출은 SHOW_ZSCORE_TAB 단일 상수로 제어.
 * 7칸 그리드(2열): 지표명 + 현재값 + 스파크라인(라인+컷 hlines) + 판정거리 라벨.
 * 복합 룰(any/all) 완전 표현은 범위 밖 — 컷은 "이 지표가 룰에 등장하는 값"까지. 판정은 hero 담당.
 * 컨테이너→순수 뷰 prop 패턴(S2 동일, QueryClient 불요).
 */
import { useState } from 'react'

import type { RegimeComponent, RegimeDetail, RegimeNearestCut } from '@/lib/api/marketPulseV2'
import { RegimeComponentSparkline } from './RegimeComponentSparkline'

// 예약 탭(이상도 z) 노출 플래그 — S4 착수 전까지 placeholder. 끄려면 false.
export const SHOW_ZSCORE_TAB = true

const INDICATOR_LABEL: Record<string, string> = {
  vix: 'VIX',
  move: 'MOVE',
  hy_oas_pct: 'HY OAS',
  nfci: 'NFCI',
  t10y2y_pct: 'T10Y2Y',
  t10y3m_pct: 'T10Y3M',
  drawdown_pct: '52w DD',
}

// 컷 regime → 짧은 심각도 라벨(거리 문구용).
const REGIME_SHORT: Record<string, string> = {
  LATE_BULL: '후반',
  TRANSITION: '전환',
  BEAR_CONTRACTION: '약세',
  CRISIS: '위기',
  BULL_EXPANSION: '강세',
}

function fmtValue(v: number | null, unit: string): string {
  if (v == null) return '—'
  return `${v.toFixed(1)}${unit}`
}

function distanceLabel(nearest: RegimeNearestCut): string {
  const regimeKo = REGIME_SHORT[nearest.regime] ?? nearest.regime
  // distance는 항상 양수(미통과 잔여 마진). 컷 통과 방향과 무관하게 "남은 거리"로 표기.
  return `${regimeKo} 컷(${nearest.cut})까지 +${nearest.distance.toFixed(1)}`
}

function ComponentCell({ component }: { component: RegimeComponent }) {
  const label = INDICATOR_LABEL[component.key] ?? component.key
  const crossed = component.crossed_cuts.length > 0
  const nearest = component.nearest_cut_distance

  return (
    <div
      data-testid={`comp-cell-${component.key}`}
      className="rounded border border-slate-200 bg-white px-2 py-1.5"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-700">{label}</span>
        <span className="text-xs tabular-nums text-slate-900">
          {fmtValue(component.current, component.unit)}
        </span>
      </div>
      <div className="my-1">
        <RegimeComponentSparkline component={component} />
      </div>
      {crossed ? (
        <p data-testid={`dist-${component.key}`} className="text-[10px] font-semibold text-rose-600">
          ⚠ 컷 통과
        </p>
      ) : nearest ? (
        <p data-testid={`dist-${component.key}`} className="text-[10px] text-slate-500">
          {distanceLabel(nearest)}
        </p>
      ) : (
        <p data-testid={`dist-${component.key}`} className="text-[10px] text-slate-400">
          —
        </p>
      )}
    </div>
  )
}

export function RegimeComponents({ payload }: { payload: RegimeDetail; labels?: Record<string, string> }) {
  const [mode, setMode] = useState<'raw' | 'z'>('raw')
  const components = payload.components ?? []
  if (components.length === 0) return null

  return (
    <section data-testid="regime-components">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">국면 재료 판정 거리</p>
        <div role="tablist" className="flex rounded border border-slate-200 overflow-hidden text-[11px]">
          <button
            type="button"
            role="tab"
            data-testid="tab-raw"
            aria-selected={mode === 'raw'}
            onClick={() => setMode('raw')}
            className={`px-2 py-0.5 ${mode === 'raw' ? 'bg-slate-800 text-white' : 'bg-white text-slate-600'}`}
          >
            판정 거리
          </button>
          {SHOW_ZSCORE_TAB ? (
            <button
              type="button"
              role="tab"
              data-testid="tab-z"
              aria-selected={mode === 'z'}
              onClick={() => setMode('z')}
              className={`px-2 py-0.5 border-l border-slate-200 ${
                mode === 'z' ? 'bg-slate-800 text-white' : 'bg-white text-slate-400'
              }`}
            >
              이상도(z) 🔒
            </button>
          ) : null}
        </div>
      </div>

      {mode === 'z' ? (
        <div
          data-testid="zscore-placeholder"
          className="rounded border border-dashed border-slate-200 bg-slate-50 px-3 py-6 text-center text-xs text-slate-400"
        >
          이상도(z) 뷰는 장기 히스토리 확보 후 제공 예정입니다.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            {components.map((c) => (
              <ComponentCell key={c.key} component={c} />
            ))}
          </div>
          <p data-testid="hysteresis-caption" className="text-[10px] text-slate-400 mt-2">
            임계 교차 ≠ 즉시 전환 — 같은 후보 2일 유지 시 확정(위기 즉시).
          </p>
        </>
      )}
    </section>
  )
}
