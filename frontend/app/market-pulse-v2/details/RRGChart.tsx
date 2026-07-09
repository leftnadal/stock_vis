'use client'

/**
 * MP2-SECTOR-CD Slice 3 — RRG(회전) 사분면 맵.
 *
 * x=rel_strength_5d(5일 상대수익, CD-STAB A′), y=momentum_5d(상승 동력). 판정선 2축 = 서빙 메타
 *   (cd_rel_strength_baseline·cd_momentum_baseline) — FE 하드코딩 금지(규칙 #2).
 * 점 색 = 서빙된 cd_state의 cd 토큰(재분류 0, 규칙 #1). 출발 섹터 = 확대점+링.
 * 꼬리 = 최근 5거래일(D-CD-TRAIL) raw 좌표 폴리라인 — 색은 해당 섹터의 **현재** 상태색 저투명.
 *   과거 점별 상태 분류·상태색 금지(규칙 #1). 히스토리 부족 시 있는 만큼만(발명 0).
 */
import { translate } from '@/lib/i18n/marketPulse'
import type { SectorDetail as Detail, SectorRow } from '@/lib/api/marketPulseV2'
import { cdStateDotFill } from '../sectorColor'

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

function extent(vals: number[], base: number): [number, number] {
  const all = vals.concat([base])
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const pad = (hi - lo || 1) * 0.15
  return [lo - pad, hi + pad]
}

export function RRGChart({
  payload,
  labels,
  fromSymbol,
}: {
  payload: Detail
  labels?: Record<string, string>
  fromSymbol?: string
}) {
  // CD-STAB A′: 판단 x축 = rel_strength_5d(5일 상대수익). 서빙값이 숫자인 섹터만(null=판단 유보).
  const sectors = (payload.sectors ?? []).filter(
    (s): s is SectorRow & { rel_strength_5d: number } =>
      typeof s.rel_strength_5d === 'number' && typeof s.momentum_5d === 'number',
  )
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

  // 도메인 = 현재 점 + 꼬리 점 + 기준선 포함, 대칭 패딩(클리핑 금지).
  const allRel = sectors.map((s) => s.rel_strength_5d)
  const allMom = sectors.map((s) => s.momentum_5d)
  for (const pts of trailBySymbol.values()) {
    pts.forEach((p) => {
      allRel.push(p.rel)
      allMom.push(p.mom)
    })
  }
  const [x0, x1] = extent(allRel, xBase)
  const [y0, y1] = extent(allMom, yBase)

  const px = (rel: number) => M.left + ((rel - x0) / (x1 - x0)) * PLOT_W
  const py = (mom: number) => M.top + ((y1 - mom) / (y1 - y0)) * PLOT_H // 반전: 높은 mom = 상단

  const bx = px(xBase)
  const by = py(yBase)

  return (
    <div data-testid="rrg-chart">
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

        {/* 꼬리 폴리라인 — raw 좌표, 색=현재 상태색 저투명(과거 점 재분류 금지, D-CD-TRAIL) */}
        {sectors.map((s) => {
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
              strokeWidth={1.5}
              strokeOpacity={0.35}
            />
          )
        })}

        {/* 섹터 점 — 색=서빙 cd_state, 출발 섹터=확대+링 */}
        {sectors.map((s) => {
          const isFrom = fromSymbol != null && s.symbol === fromSymbol
          const cx = px(s.rel_strength_5d)
          const cy = py(s.momentum_5d)
          const fill = cdStateDotFill(s.cd_state ?? null)
          return (
            <g key={s.symbol}>
              {isFrom ? (
                <circle
                  data-testid={`rrg-ring-${s.symbol}`}
                  cx={cx}
                  cy={cy}
                  r={9}
                  fill="none"
                  stroke={fill}
                  strokeWidth={1.5}
                />
              ) : null}
              <circle
                data-testid={`rrg-dot-${s.symbol}`}
                cx={cx}
                cy={cy}
                r={isFrom ? 6 : 4}
                fill={fill}
              />
              <text x={cx + 7} y={cy + 3} fontSize={9} fill={isFrom ? '#0f172a' : '#334155'} fontWeight={isFrom ? 700 : 400}>
                {translate(`sector.${s.symbol}`, labels, s.symbol)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
