'use client'

/**
 * MP2-TREND S2 적용처 2호 — 시장 폭(A/D선) 궤적 + 기준선(MA20).
 *
 * 공용 MultiLineTrendChart 재사용: 주라인 = A/D(실선), 기준선 = MA20(refSeries 점선),
 *   전환일 = vlines. 리드아웃에 "기준선 대비 ±x.x% · n일째 이탈"(D-TREND-TOOLTIP, 그래프 위 박스 0).
 * 이탈 시각화 = 시작점 마커(vline) + 리드아웃 streak(사전 승인 폴백 — recharts 음영 대체).
 * FE 판단 파생 금지: 기준선 대비 %는 서빙된 두 per-date 값(ad_line, ad_line_ma20)의 단순 차 표시만.
 */
import { useMemo } from 'react'

import { MultiLineTrendChart, type TrendSeries } from '@/components/charts/MultiLineTrendChart'
import type { BreadthDetail } from '@/lib/api/marketPulseV2'
import { baselineNote, deviationStartDate, transitionVlines } from './trendOverlays'

export function BreadthTrajectory({
  payload,
  transitionDates = [],
}: {
  payload: BreadthDetail
  transitionDates?: string[]
}) {
  const history = payload.history_30d ?? []
  const streak = payload.ma_deviation_streak_days ?? 0

  const series: TrendSeries[] = useMemo(() => {
    const lastIdx = history.length - 1
    return [
      {
        key: 'ad',
        label: 'A/D',
        points: history.map((p, i) => ({
          date: p.date,
          value: p.ad_line,
          // 최신일에만 streak 부여(그 외는 per-date 기준선 대비 %만).
          note: baselineNote(p.ad_line, p.ad_line_ma20, i === lastIdx ? streak : undefined),
        })),
      },
    ]
  }, [history, streak])

  // 기준선(MA20) refSeries — null 구간(<20일)은 제외해 gap 유지.
  const refSeries: TrendSeries[] = useMemo(
    () => [
      {
        key: 'ma20',
        label: '기준선(MA20)',
        points: history
          .filter((p) => p.ad_line_ma20 != null)
          .map((p) => ({ date: p.date, value: p.ad_line_ma20 as number })),
      },
    ],
    [history],
  )

  const vlines = useMemo(() => {
    const devStart = deviationStartDate(history, streak)
    return [
      ...transitionVlines(transitionDates),
      ...(devStart ? [{ date: devStart, label: '이탈 시작' }] : []),
    ]
  }, [history, streak, transitionDates])

  if (history.length === 0) {
    return (
      <p data-testid="breadth-trajectory-empty" className="text-sm text-slate-400">
        A/D선 추이 데이터가 아직 없습니다.
      </p>
    )
  }

  return (
    <section data-testid="breadth-trajectory">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
        A/D선 추이 · 기준선(MA20)
      </p>
      <MultiLineTrendChart
        series={series}
        ranges={[7, 30]}
        emphasis={{ default: ['ad'], legendToggle: false }}
        overlays={{ refSeries, vlines }}
        readout={{ pinLatest: true }}
      />
    </section>
  )
}
