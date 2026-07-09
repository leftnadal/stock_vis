'use client'

/**
 * MP2-SECTOR-CD Slice 1 — 섹터 판단(CD) 패널.
 *
 * 제품 목적: "이 섹터 지금 진입할 만한가"를 5초 즉답. rel_strength_5d(x, 5일 상대수익, CD-STAB A′) ×
 *   momentum_5d(y, 상승 동력)의 사분면 판단.
 * 판정 로직 재계산 0: BE가 서빙한 cd_state를 뱃지·문구에만 사용. 사분면 미니맵의 점 좌표는
 *   서빙된 rel_strength_5d·momentum_5d 원값을 그대로 좌표화(재분류 금지, cd_state와 동일 x축).
 * CD_STANCE = FE 정적 판정 문구(REGIME_STANCE 톤 동형, LLM 0) — 4상태 + 유보 = 5문구.
 * 회전 맵 어포던스: 행 전체 탭 → rotation?from=<그 행 symbol>(S3 보완, per-row) +
 *   상단 "회전 맵 전체 보기 →"(from=리더). D-SECTOR-NAV 이행.
 */
import Link from 'next/link'

import { translate } from '@/lib/i18n/marketPulse'
import type { SectorDetail as Detail, SectorRow } from '@/lib/api/marketPulseV2'
import {
  CD_STATE_ORDER,
  cdStateBadgeClass,
  cdStateDotFill,
  cdStateLabel,
  type CdState,
} from '../sectorColor'

// CD_STANCE — 4상태 + 유보 정적 판정 문구(판단중심, 매매 지시 아님).
const CD_STANCE: Record<CdState | 'reserved', string> = {
  leading_strengthening: '시장을 앞서며 상승 동력도 가속 — 추세가 가장 우호적인 구간.',
  leading_weakening: '아직 시장 우위지만 상승 동력은 둔화 — 과열·이익 관리 관점.',
  lagging_improving: '시장에는 뒤처지나 반등 신호 — 바닥 확인·선취 관찰 구간.',
  lagging_deteriorating: '시장 대비 약세에 하락도 지속 — 신규 진입은 신중.',
  reserved: '모멘텀 산출 이력이 부족해 판정을 유보합니다.',
}

function stanceCopy(state: CdState | null | undefined): string {
  return state == null ? CD_STANCE.reserved : CD_STANCE[state]
}

function fmtPct(v: number): string {
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

// null(bench 소급 부족 → 판단 유보) = 대시. 발명·0 표기 금지(규칙 #5).
function fmtPctN(v: number | null | undefined): string {
  return typeof v === 'number' ? fmtPct(v) : '—'
}

/** 2×2 사분면 미니맵 — 서빙된 rel_strength_5d(x, CD-STAB A′)·momentum_5d(y) 원값 좌표화. */
function QuadrantMinimap({ sectors, labels }: { sectors: SectorRow[]; labels?: Record<string, string> }) {
  // cd_state 판정 = rel_strength_5d 기반 → 좌표도 동일 값(시각 모순 차단, 규칙 #2). 둘 다 있는 섹터만.
  const plotted = sectors.filter(
    (s): s is SectorRow & { rel_strength_5d: number } =>
      s.cd_state != null && typeof s.rel_strength_5d === 'number',
  )
  // 0 중심 대칭 스케일 — 양축 최대 절대값 기준(패딩 20%). 데이터 없으면 1로 폴백.
  const maxAbsX = Math.max(0.001, ...plotted.map((s) => Math.abs(s.rel_strength_5d)))
  const maxAbsY = Math.max(0.001, ...plotted.map((s) => Math.abs(s.momentum_5d)))
  const spanX = maxAbsX * 1.2
  const spanY = maxAbsY * 1.2
  const SIZE = 200
  const C = SIZE / 2
  // x: rel_strength_5d(오른쪽=우위), y: momentum_5d(위=상승, SVG y 반전).
  const px = (rel: number) => C + (rel / spanX) * (C - 12)
  const py = (mom: number) => C - (mom / spanY) * (C - 12)

  return (
    <div data-testid="cd-minimap">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width="100%" height={200} role="img" aria-label="섹터 판단 사분면">
        {/* 사분면 배경 힌트(연한 4색) */}
        <rect x={C} y={0} width={C} height={C} fill="#fff1f2" />{/* 우상 주도·강화 rose */}
        <rect x={0} y={0} width={C} height={C} fill="#f0fdfa" />{/* 좌상 부진·개선 teal */}
        <rect x={C} y={C} width={C} height={C} fill="#fffbeb" />{/* 우하 주도·둔화 amber */}
        <rect x={0} y={C} width={C} height={C} fill="#f0f9ff" />{/* 좌하 부진·악화 sky */}
        {/* 0 기준 축 */}
        <line x1={C} y1={0} x2={C} y2={SIZE} stroke="#cbd5e1" strokeWidth={1} />
        <line x1={0} y1={C} x2={SIZE} y2={C} stroke="#cbd5e1" strokeWidth={1} />
        {/* 사분면 코너 라벨 */}
        <text x={SIZE - 4} y={12} textAnchor="end" fontSize={9} fill="#9f1239">주도·강화</text>
        <text x={4} y={12} fontSize={9} fill="#0f766e">부진·개선</text>
        <text x={SIZE - 4} y={SIZE - 4} textAnchor="end" fontSize={9} fill="#b45309">주도·둔화</text>
        <text x={4} y={SIZE - 4} fontSize={9} fill="#0369a1">부진·악화</text>
        {/* 섹터 점 — 서빙 값 그대로 좌표화 */}
        {plotted.map((s) => (
          <g key={s.symbol}>
            <circle
              data-testid={`cd-dot-${s.symbol}`}
              cx={px(s.rel_strength_5d)}
              cy={py(s.momentum_5d)}
              r={4}
              fill={cdStateDotFill(s.cd_state ?? null)}
            />
            <text
              x={px(s.rel_strength_5d) + 6}
              y={py(s.momentum_5d) + 3}
              fontSize={8}
              fill="#334155"
            >
              {translate(`sector.${s.symbol}`, labels, s.symbol)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}

/** 4상태 범례. */
function CdLegend() {
  return (
    <ul data-testid="cd-legend" className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-500">
      {CD_STATE_ORDER.map((state) => (
        <li key={state} className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: cdStateDotFill(state) }} />
          {cdStateLabel(state)}
        </li>
      ))}
    </ul>
  )
}

export function SectorCdPanel({ payload, labels }: { payload: Detail; labels?: Record<string, string> }) {
  const sectors = payload.sectors ?? []
  if (sectors.length === 0) {
    return <p className="text-sm text-slate-500">섹터 판단 데이터가 아직 준비되지 않았습니다.</p>
  }

  // MP2-SECTOR-CD S3: 회전 맵 CTA — 출발 섹터 = rank-1 리더(sectors[]는 rank순). D-SECTOR-NAV 어포던스 활성화.
  const leadSymbol = sectors[0]?.symbol

  return (
    <div className="grid gap-4" data-testid="sector-cd-panel">
      <QuadrantMinimap sectors={sectors} labels={labels} />
      <div className="flex items-center justify-between">
        <CdLegend />
        {leadSymbol ? (
          <Link
            href={`/market-pulse-v2/rotation?from=${leadSymbol}`}
            data-testid="rrg-cta"
            className="shrink-0 rounded border border-slate-200 px-2 py-0.5 text-[11px] font-medium text-slate-600 hover:bg-slate-50"
          >
            회전 맵 전체 보기 →
          </Link>
        ) : null}
      </div>

      <ul className="grid gap-2">
        {sectors.map((s) => {
          const label = translate(`sector.${s.symbol}`, labels, s.symbol)
          const reserved = s.cd_state == null
          return (
            <li
              key={s.symbol}
              data-testid={`cd-row-${s.symbol}`}
              className="rounded border border-slate-200 bg-white"
            >
              {/* MP2-SECTOR-CD S3 보완: 행 전체 = 회전 맵 진입(그 행 symbol이 from). 기존 행 탭 인터랙션 부재로 충돌 0. */}
              <Link
                href={`/market-pulse-v2/rotation?from=${s.symbol}`}
                data-testid={`cd-row-link-${s.symbol}`}
                aria-label={`${label} 회전 맵에서 보기`}
                className="block rounded px-3 py-2 hover:bg-slate-50"
              >
                <div className="flex items-center gap-2">
                  <span className="w-6 shrink-0 text-xs tabular-nums text-slate-400">#{s.rank}</span>
                  <span className="w-16 shrink-0 text-sm font-medium text-slate-800">{label}</span>
                  <span
                    data-testid={`cd-badge-${s.symbol}`}
                    className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${cdStateBadgeClass(
                      s.cd_state ?? null,
                    )}`}
                  >
                    {cdStateLabel(s.cd_state ?? null)}
                  </span>
                  {/* 우측 화살표 어포던스 — 행이 회전 맵 진입임을 표시 */}
                  <span aria-hidden className="ml-auto shrink-0 text-slate-300">→</span>
                </div>
                <p
                  data-testid={`cd-stance-${s.symbol}`}
                  className={`mt-1 text-xs ${reserved ? 'text-slate-400' : 'text-slate-700'}`}
                >
                  {stanceCopy(s.cd_state)}
                </p>
                {/* 근거 값 2칸 — rel_strength_5d(판단 x축)·momentum_5d 원값 */}
                <div className="mt-1 flex gap-4 text-[11px] tabular-nums text-slate-500">
                  <span data-testid={`cd-rel-${s.symbol}`}>상대강도 (5일) {fmtPctN(s.rel_strength_5d)}</span>
                  <span data-testid={`cd-mom-${s.symbol}`}>5일 모멘텀 {fmtPct(s.momentum_5d)}</span>
                </div>
              </Link>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
