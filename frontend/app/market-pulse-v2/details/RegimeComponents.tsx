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

import { useRegimeZScore } from '@/hooks/useMarketPulseV2'
import type {
  RegimeComponent,
  RegimeDetail,
  RegimeNearestCut,
  RegimeZComponent,
} from '@/lib/api/marketPulseV2'
import { RegimeComponentSparkline } from './RegimeComponentSparkline'
import { RegimeZSparkline } from './RegimeZSparkline'

// 예약 탭(이상도 z)은 S4로 실 뷰 장착 — 상수는 계약 하위호환 위해 유지(항상 노출).
export const SHOW_ZSCORE_TAB = true

// |z|≥2 = danger(이상). 스파크라인 밴드와 동일 임계.
const Z_DANGER = 2

// 성분 series의 현재(최신 non-null) z. 없으면 null.
function currentZ(c: RegimeZComponent): number | null {
  for (let i = c.series.length - 1; i >= 0; i--) {
    if (c.series[i].z != null) return c.series[i].z
  }
  return null
}

// 정렬: |현재 z| 내림차순 → 현재 z null(기준 충분) → insufficient 최후미.
function sortByAnomaly(a: RegimeZComponent, b: RegimeZComponent): number {
  const rank = (c: RegimeZComponent) => (c.insufficient ? 2 : currentZ(c) == null ? 1 : 0)
  const ra = rank(a)
  const rb = rank(b)
  if (ra !== rb) return ra - rb
  if (ra === 0) return Math.abs(currentZ(b) as number) - Math.abs(currentZ(a) as number)
  return 0
}

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

function ZComponentCell({
  component,
  lowConfidenceUntil,
}: {
  component: RegimeZComponent
  lowConfidenceUntil?: string
}) {
  const label = INDICATOR_LABEL[component.key] ?? component.key
  const cz = currentZ(component)
  const danger = cz != null && Math.abs(cz) >= Z_DANGER

  return (
    <div
      data-testid={`zcomp-cell-${component.key}`}
      className="rounded border border-slate-200 bg-white px-2 py-1.5"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-700">{label}</span>
        {component.insufficient ? (
          <span data-testid={`zchip-${component.key}`} className="text-[10px] text-slate-400">
            기준 부족
          </span>
        ) : (
          <span
            data-testid={`zchip-${component.key}`}
            className={`text-[10px] font-semibold tabular-nums rounded px-1 ${
              danger ? 'bg-rose-100 text-rose-700' : 'text-slate-500'
            }`}
          >
            {cz == null ? 'z —' : `z ${cz > 0 ? '+' : ''}${cz.toFixed(1)}`}
          </span>
        )}
      </div>
      <div className="my-1">
        {component.insufficient ? (
          <div className="h-11 flex items-center text-[10px] text-slate-400">기준 불충분</div>
        ) : (
          <RegimeZSparkline component={component} lowConfidenceUntil={lowConfidenceUntil} />
        )}
      </div>
    </div>
  )
}

function ZView({
  loading,
  error,
  components,
  lowConfidenceUntil,
}: {
  loading: boolean
  error: boolean
  components: RegimeZComponent[]
  lowConfidenceUntil?: string
}) {
  if (loading) {
    return (
      <div data-testid="zview-loading" className="px-3 py-6 text-center text-xs text-slate-400">
        이상도(z) 불러오는 중…
      </div>
    )
  }
  if (error) {
    return (
      <div data-testid="zview-error" className="px-3 py-6 text-center text-xs text-rose-600">
        이상도(z)를 불러오지 못했습니다.
      </div>
    )
  }
  if (components.length === 0) {
    return (
      <div data-testid="zview-empty" className="px-3 py-6 text-center text-xs text-slate-400">
        z 기준 분포가 아직 부족합니다.
      </div>
    )
  }
  const sorted = [...components].sort(sortByAnomaly)
  return (
    <div data-testid="zview">
      <div className="grid grid-cols-2 gap-2">
        {sorted.map((c) => (
          <ZComponentCell key={c.key} component={c} lowConfidenceUntil={lowConfidenceUntil} />
        ))}
      </div>
      <p data-testid="zview-caption" className="text-[10px] text-slate-400 mt-2">
        점선 ±2σ · 기준: 3년 소급 분포 · 좌측 음영 = 저신뢰 초입
      </p>
    </div>
  )
}

// z 탭 — mode==='z'일 때만 마운트 → useRegimeZScore가 그때만 호출(lazy).
//   raw 모드에선 미마운트 → 훅 무호출 → 기존 raw 탭 테스트 QueryClient 불요(무영향).
function RegimeZTab() {
  const { data, isLoading, isError } = useRegimeZScore(true)
  return (
    <ZView
      loading={isLoading}
      error={isError}
      components={data?.data?.components ?? []}
      lowConfidenceUntil={data?.data?.meta?.low_confidence_until}
    />
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
        <RegimeZTab />
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
