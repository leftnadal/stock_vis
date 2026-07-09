'use client'

/**
 * MP2-SECTOR-CD Slice 3 → CD-READ 변형 H — RRG(회전) 사분면 맵.
 *
 * x=rel_strength_5d(5일 상대수익, CD-STAB A′), y=momentum_5d(상승 동력). 판정선 2축 = 서빙 메타
 *   (cd_rel_strength_baseline·cd_momentum_baseline) — FE 하드코딩 금지(규칙 #2).
 * 점 색 = 서빙된 cd_state의 cd 토큰(재분류 0, 규칙 #1).
 *
 * 변형 H(D-CD-READ) — 가독성:
 *   - 포커스 디폴트: 진입(from) 섹터만 꼬리+풀 라벨+링. 나머지 = 점(충돌 없으면 라벨).
 *   - 점 탭 → 그 섹터로 포커스 전환(꼬리·라벨 이동). URL 동기화 = onFocusChange(현행 구조).
 *   - 전체 꼬리 토글: OFF 디폴트. ON 시 전 섹터 꼬리 초감쇄 + 포커스만 진한 꼬리(세션 메모리, 저장 0).
 *   - 확인 중(cd_state≠cd_state_raw): 포커스 링 점선(주황)+⏳. 재분류 아님(두 서빙값 비교뿐, 규칙 #1).
 * 꼬리 = 최근 5거래일(D-CD-TRAIL) raw 좌표 — 색은 현재 상태색 저투명. 과거 점 재분류 금지.
 */
import { useState } from 'react'

import { translate } from '@/lib/i18n/marketPulse'
import type { SectorDetail as Detail, SectorRow } from '@/lib/api/marketPulseV2'
import { CD_TRANSITION_HEX, cdStateDotFill, isTransitioning } from '../sectorColor'

// D-CD-TRAIL: 꼬리 길이 = 5거래일(momentum_5d 창 정합). FE 표시 상수 단일 정의.
export const RRG_TRAIL_DAYS = 5

const W = 360
const H = 320
const M = { top: 18, right: 16, bottom: 18, left: 16 }
const PLOT_W = W - M.left - M.right
const PLOT_H = H - M.top - M.bottom

interface Pt {
  rel: number
  mom: number
}

interface Box {
  x0: number
  y0: number
  x1: number
  y1: number
}

function extent(vals: number[], base: number): [number, number] {
  const all = vals.concat([base])
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const pad = (hi - lo || 1) * 0.15
  return [lo - pad, hi + pad]
}

function overlaps(a: Box, b: Box): boolean {
  return a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0
}

export function RRGChart({
  payload,
  labels,
  fromSymbol,
  onFocusChange,
}: {
  payload: Detail
  labels?: Record<string, string>
  fromSymbol?: string
  onFocusChange?: (symbol: string) => void
}) {
  // CD-STAB A′: 판단 x축 = rel_strength_5d(5일 상대수익). 서빙값이 숫자인 섹터만(null=판단 유보).
  const sectors = (payload.sectors ?? []).filter(
    (s): s is SectorRow & { rel_strength_5d: number } =>
      typeof s.rel_strength_5d === 'number' && typeof s.momentum_5d === 'number',
  )

  // 변형 H 상태: 포커스 override(진입 from → 탭으로 전환) + 전체 꼬리 토글(세션 메모리).
  const [override, setOverride] = useState<string | undefined>(undefined)
  const [showAllTrails, setShowAllTrails] = useState(false)

  const xBase = payload.cd_rel_strength_baseline ?? 0
  const yBase = payload.cd_momentum_baseline ?? 0

  // 꼬리 좌표(섹터별 최근 RRG_TRAIL_DAYS일, 두 축 모두 숫자인 점만). x = rel_strength_5d.
  const histMap = new Map((payload.sector_history ?? []).map((h) => [h.symbol, h.history]))
  const trailBySymbol = new Map<string, Pt[]>()
  for (const s of sectors) {
    const pts = (histMap.get(s.symbol) ?? [])
      .filter((p) => typeof p.momentum_5d === 'number' && typeof p.rel_strength_5d === 'number')
      .slice(-RRG_TRAIL_DAYS)
      .map((p) => ({ rel: p.rel_strength_5d as number, mom: p.momentum_5d as number }))
    trailBySymbol.set(s.symbol, pts)
  }

  if (sectors.length === 0) {
    return <p data-testid="rrg-empty" className="text-sm text-slate-400">회전 맵 데이터가 아직 없습니다.</p>
  }

  // 유효 포커스: 탭 override → 진입 from → rank-1(첫 섹터). 항상 유효 심볼.
  const focusSym = override ?? fromSymbol ?? sectors[0].symbol
  const handleFocus = (sym: string) => {
    setOverride(sym)
    onFocusChange?.(sym)
  }

  // 도메인 = 현재 점 + (표시되는) 꼬리 점 + 기준선 포함, 대칭 패딩(클리핑 금지).
  const allRel = sectors.map((s) => s.rel_strength_5d)
  const allMom = sectors.map((s) => s.momentum_5d)
  for (const s of sectors) {
    // 도메인엔 표시 예정 꼬리만 반영(포커스 항상 + 전체 토글 ON 시 전부).
    if (s.symbol === focusSym || showAllTrails) {
      for (const p of trailBySymbol.get(s.symbol) ?? []) {
        allRel.push(p.rel)
        allMom.push(p.mom)
      }
    }
  }
  const [x0, x1] = extent(allRel, xBase)
  const [y0, y1] = extent(allMom, yBase)

  const px = (rel: number) => M.left + ((rel - x0) / (x1 - x0)) * PLOT_W
  const py = (mom: number) => M.top + ((y1 - mom) / (y1 - y0)) * PLOT_H // 반전: 높은 mom = 상단

  const bx = px(xBase)
  const by = py(yBase)

  // 점 좌표 사전계산.
  const pos = new Map(sectors.map((s) => [s.symbol, { cx: px(s.rel_strength_5d), cy: py(s.momentum_5d) }]))

  // 라벨 배치(규칙 #4 단순 그리디): 포커스 먼저 배치(항상 표시), 이후 rank순.
  //   후보 라벨 bbox가 이미 배치된 라벨과 겹치면 숨김(밀집 충돌 자동 숨김).
  const labelText = (s: SectorRow) => translate(`sector.${s.symbol}`, labels, s.symbol)
  const labelBox = (cx: number, cy: number, text: string): Box => {
    const w = text.length * 6 + 6 // fontSize 9 근사 폭
    return { x0: cx + 6, y0: cy - 7, x1: cx + 6 + w, y1: cy + 7 }
  }
  const showLabel = new Set<string>()
  const placed: Box[] = []
  const order = [
    ...sectors.filter((s) => s.symbol === focusSym),
    ...sectors.filter((s) => s.symbol !== focusSym),
  ]
  for (const s of order) {
    const p = pos.get(s.symbol)!
    const box = labelBox(p.cx, p.cy, labelText(s))
    if (s.symbol === focusSym) {
      showLabel.add(s.symbol) // 포커스는 항상 풀 라벨
      placed.push(box)
      continue
    }
    if (!placed.some((b) => overlaps(box, b))) {
      showLabel.add(s.symbol)
      placed.push(box)
    }
  }

  const focusSector = sectors.find((s) => s.symbol === focusSym)
  const focusTransitioning = focusSector
    ? isTransitioning(focusSector.cd_state, focusSector.cd_state_raw)
    : false

  return (
    <div data-testid="rrg-chart">
      <div className="mb-1 flex justify-end">
        <button
          type="button"
          data-testid="rrg-trail-toggle"
          aria-pressed={showAllTrails}
          onClick={() => setShowAllTrails((v) => !v)}
          className={`rounded border px-2 py-0.5 text-[11px] font-medium ${
            showAllTrails
              ? 'border-slate-400 bg-slate-100 text-slate-700'
              : 'border-slate-200 text-slate-500 hover:bg-slate-50'
          }`}
        >
          전체 꼬리 {showAllTrails ? 'ON' : 'OFF'}
        </button>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="섹터 회전 사분면 맵">
        {/* 사분면 배경 틴트 — 기준선 교차점 기준 4분할(연한 cd 색) */}
        <rect x={bx} y={M.top} width={M.left + PLOT_W - bx} height={by - M.top} fill="#fff1f2" />{/* 우상 주도·강화 rose */}
        <rect x={M.left} y={M.top} width={bx - M.left} height={by - M.top} fill="#f0fdfa" />{/* 좌상 부진·개선 teal */}
        <rect x={bx} y={by} width={M.left + PLOT_W - bx} height={M.top + PLOT_H - by} fill="#fffbeb" />{/* 우하 주도·둔화 amber */}
        <rect x={M.left} y={by} width={bx - M.left} height={M.top + PLOT_H - by} fill="#f0f9ff" />{/* 좌하 부진·악화 sky */}

        {/* 판정선 2축 — 서빙 메타값 위치. data-value로 하드코딩 아님 증명(S2 동형). */}
        <line
          data-testid="rrg-baseline-x"
          data-value={xBase}
          x1={bx}
          y1={M.top}
          x2={bx}
          y2={M.top + PLOT_H}
          stroke="#94a3b8"
          strokeWidth={1}
          strokeDasharray="3 3"
        />
        <line
          data-testid="rrg-baseline-y"
          data-value={yBase}
          x1={M.left}
          y1={by}
          x2={M.left + PLOT_W}
          y2={by}
          stroke="#94a3b8"
          strokeWidth={1}
          strokeDasharray="3 3"
        />

        {/* 사분면 코너 라벨 */}
        <text x={W - M.right} y={M.top + 10} textAnchor="end" fontSize={10} fill="#9f1239">주도·강화</text>
        <text x={M.left} y={M.top + 10} fontSize={10} fill="#0f766e">부진·개선</text>
        <text x={W - M.right} y={H - M.bottom} textAnchor="end" fontSize={10} fill="#b45309">주도·둔화</text>
        <text x={M.left} y={H - M.bottom} fontSize={10} fill="#0369a1">부진·악화</text>

        {/* 꼬리 폴리라인 — 포커스 항상(진함) + 전체 토글 ON 시 나머지(초감쇄). raw 좌표, 현재 상태색. */}
        {sectors.map((s) => {
          const isFocus = s.symbol === focusSym
          if (!isFocus && !showAllTrails) return null // 포커스 디폴트: 나머지 꼬리 숨김
          const pts = trailBySymbol.get(s.symbol) ?? []
          if (pts.length < 2) return null
          const poly = pts.map((p) => `${px(p.rel).toFixed(1)},${py(p.mom).toFixed(1)}`).join(' ')
          return (
            <polyline
              key={`trail-${s.symbol}`}
              data-testid={`rrg-trail-${s.symbol}`}
              points={poly}
              fill="none"
              stroke={cdStateDotFill(s.cd_state ?? null)}
              strokeWidth={isFocus ? 1.75 : 1.25}
              strokeOpacity={isFocus ? 0.5 : 0.18}
            />
          )
        })}

        {/* 섹터 점 — 색=서빙 cd_state. 포커스=확대+링(확인 중=점선 주황). 탭=포커스 전환. */}
        {sectors.map((s) => {
          const isFocus = s.symbol === focusSym
          const { cx, cy } = pos.get(s.symbol)!
          const fill = cdStateDotFill(s.cd_state ?? null)
          return (
            <g key={s.symbol}>
              {isFocus ? (
                <circle
                  data-testid={`rrg-ring-${s.symbol}`}
                  cx={cx}
                  cy={cy}
                  r={9}
                  fill="none"
                  stroke={focusTransitioning ? CD_TRANSITION_HEX : fill}
                  strokeWidth={1.5}
                  strokeDasharray={focusTransitioning ? '2 2' : undefined}
                />
              ) : null}
              <circle
                data-testid={`rrg-dot-${s.symbol}`}
                cx={cx}
                cy={cy}
                r={isFocus ? 6 : 4}
                fill={fill}
                style={{ cursor: 'pointer' }}
                onClick={() => handleFocus(s.symbol)}
              />
              {showLabel.has(s.symbol) ? (
                <text
                  data-testid={`rrg-label-${s.symbol}`}
                  x={cx + 7}
                  y={cy + 3}
                  fontSize={9}
                  fill={isFocus ? '#0f172a' : '#334155'}
                  fontWeight={isFocus ? 700 : 400}
                >
                  {labelText(s)}
                  {isFocus && focusTransitioning ? ' ⏳' : ''}
                </text>
              ) : null}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
