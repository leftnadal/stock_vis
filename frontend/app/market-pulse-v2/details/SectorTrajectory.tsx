'use client'

/**
 * MP2-TREND S1 적용처 1호 — 섹터 순위 궤적.
 *
 * 공용 MultiLineTrendChart에 sector_history(rank additive)를 꽂는다. y축=rank(1위 상단·반전).
 * 강조 기본 = 현재 leaders(rank 상위 2) + laggards(하위 2) — payload.sectors의 서버 rank 사용
 *   (FE 델타 재계산 금지 규약 → 서버 제공 rank 기반 "진입 컨텍스트"). legend로 임의 토글.
 * rel_strength는 리드아웃 부기(note)로 유지. overlays(전환일 세로선)는 1호 미포함(2호 소관).
 */
import { useMemo } from 'react'

import { MultiLineTrendChart, type TrendSeries } from '@/components/charts/MultiLineTrendChart'
import { translate } from '@/lib/i18n/marketPulse'
import type { SectorDetail } from '@/lib/api/marketPulseV2'

export function SectorTrajectory({
  payload,
  labels,
}: {
  payload: SectorDetail
  labels?: Record<string, string>
}) {
  const history = payload.sector_history ?? []
  const sectors = payload.sectors ?? []

  const series: TrendSeries[] = useMemo(
    () =>
      history.map((sh) => ({
        key: sh.symbol,
        label: translate(`sector.${sh.symbol}`, labels, sh.symbol),
        points: sh.history
          .filter((p) => typeof p.rank === 'number')
          .map((p) => ({
            date: p.date,
            value: p.rank as number,
            note: `강도 ${p.rel_strength >= 0 ? '+' : ''}${p.rel_strength.toFixed(2)}`,
          })),
      })),
    [history, labels],
  )

  // 강조 기본: 서버 rank 기준 leaders(작은 rank 2) + laggards(큰 rank 2). 델타 재계산 없음.
  const emphasisDefault = useMemo(() => {
    const ranked = [...sectors].filter((s) => typeof s.rank === 'number').sort((a, b) => a.rank - b.rank)
    const leaders = ranked.slice(0, 2).map((s) => s.symbol)
    const laggards = ranked.slice(-2).map((s) => s.symbol)
    return Array.from(new Set([...leaders, ...laggards]))
  }, [sectors])

  const entityCount = series.length || 11

  if (series.length === 0) {
    return <p data-testid="sector-trajectory-empty" className="text-sm text-slate-400">순위 궤적 데이터가 아직 없습니다.</p>
  }

  return (
    <section data-testid="sector-trajectory">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">섹터 순위 궤적</p>
      <MultiLineTrendChart
        series={series}
        yAxis={{ inverted: true, domain: [1, entityCount], tickFormat: (v) => `${v}위` }}
        ranges={[7, 30]}
        emphasis={{ default: emphasisDefault, legendToggle: true }}
        overlays={{}}
        readout={{ pinLatest: true }}
      />
    </section>
  )
}
