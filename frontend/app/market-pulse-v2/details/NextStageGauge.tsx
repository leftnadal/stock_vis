'use client'

import type { RegimeId, RegimeMargin } from '@/lib/api/marketPulseV2'
import { regimeTone } from '../meaning'

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v))
}

/**
 * MP-UX-B3 — 단일 지표 "다음 단계까지 임박도" 게이지 (한 행, 부호화 양방향).
 *
 * 축 = BE `to_threshold` 부호 규약 그대로(>0 = 아직 안 닿음, <=0 = 돌파). op `<`/`>` 혼재는
 *   BE가 부호 정규화 → FE는 부호/임계 판정·재계산 0(발명 0). 길이는 |to_threshold|/scaleRef
 *   표시 정규화에만 쓰고 판정엔 미사용. null to_threshold는 호출부(RegimeNextStage)에서 제외.
 * 중앙선(0) = 임계 도달. 왼쪽 = 아직(to_threshold>0), 오른쪽 + 강조색 = 돌파(<=0).
 * 색 = meaning.ts regimeTone(다음 단계) 단일소스.
 */
export function NextStageGauge({
  margin,
  isClosest,
  nextStage,
  scaleRef,
  indicatorLabel,
}: {
  margin: RegimeMargin
  isClosest: boolean
  nextStage: RegimeId
  scaleRef: number
  indicatorLabel: string
}) {
  const d = margin.to_threshold as number // 호출부에서 null 제외 보장
  const breached = d <= 0
  const frac = clamp(Math.abs(d) / (scaleRef || 1), 0, 1)
  const widthPct = (frac * 50).toFixed(1) // 중앙선 기준 절반 폭에 매핑
  const tone = regimeTone(nextStage) // 돌파 강조색(단일소스)

  return (
    <li
      className={`flex items-center gap-2 text-xs ${isClosest ? 'font-semibold' : ''}`}
      data-indicator={margin.indicator}
      data-breached={breached ? 'true' : 'false'}
      data-direction={breached ? 'right' : 'left'}
      data-closest={isClosest ? 'true' : 'false'}
    >
      <span className="w-28 shrink-0 truncate text-slate-700">
        {isClosest ? '▸ ' : ''}
        {indicatorLabel}
      </span>
      <span className="relative h-2 flex-1 rounded bg-slate-100" aria-hidden="true">
        {/* 중앙선 = 임계 도달선 */}
        <span className="absolute left-1/2 top-0 h-2 w-px -translate-x-1/2 bg-slate-300" />
        {/* 바: 아직 → 중앙에서 왼쪽 / 돌파 → 중앙에서 오른쪽(강조 tone) */}
        <span
          className={`absolute top-0 h-2 rounded ${breached ? `border ${tone}` : 'bg-slate-400'}`}
          style={breached ? { left: '50%', width: `${widthPct}%` } : { right: '50%', width: `${widthPct}%` }}
        />
      </span>
      <span
        className={`w-16 shrink-0 text-right tabular-nums ${breached ? 'text-rose-600' : 'text-slate-500'}`}
      >
        {breached ? '돌파' : `${d} 남음`}
      </span>
    </li>
  )
}
