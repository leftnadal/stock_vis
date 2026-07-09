'use client'

/**
 * MP2-TREND S1 적용처 1호 — 섹터 순위 궤적.
 *
 * 공용 MultiLineTrendChart에 sector_history(rank additive)를 꽂는다. y축=rank(1위 상단·반전).
 * 강조 기본 = 현재 leaders(rank 상위 2) + laggards(하위 2) — payload.sectors의 서버 rank 사용
 *   (FE 델타 재계산 금지 규약 → 서버 제공 rank 기반 "진입 컨텍스트"). legend로 임의 토글.
 * rel_strength는 리드아웃 부기(note)로 유지.
 * MP2-TREND S2: overlays.vlines(전환일 세로선, 공용 계약 실증) + emphasisOverride(델타 컨텍스트 복원).
 * MP2-SECTOR-CD S2: 모드 토글 [순위 | 모멘텀]. 디폴트=순위(기존 동작 무영향). 모멘텀 모드는
 *   momentum_5d 라인 + 판정선 hline(서빙 cd_momentum_baseline) + 국면 스트립 레인.
 */
import { useMemo, useState } from 'react'

import { MultiLineTrendChart, type TrendSeries } from '@/components/charts/MultiLineTrendChart'
import { translate } from '@/lib/i18n/marketPulse'
import type { SectorDetail } from '@/lib/api/marketPulseV2'
import { RegimeStrip } from './RegimeStrip'
import { transitionVlines } from './trendOverlays'

// 모멘텀 모드 표시 창(일). 국면 스트립과 동일 날짜 창을 쓰기 위해 고정(랭킹 뷰는 7/30 토글 유지).
const MOMENTUM_WINDOW = 30

export function SectorTrajectory({
  payload,
  labels,
  transitionDates = [],
  emphasisOverride,
  regimeHistory = [],
}: {
  payload: SectorDetail
  labels?: Record<string, string>
  // MP2-TREND S2: 전환일 세로선(regime 계약 공용 소비, 없으면 무영향 E4).
  transitionDates?: string[]
  // MP2-TREND S2(D-TREND-EMPHASIS 옵션 B): 델타 카드가 전달한 상위 변동 섹터. 없으면 기본(leaders/laggards).
  emphasisOverride?: string[]
  // MP2-SECTOR-CD S2: 국면 스트립 데이터원(regime_history_30d 기서빙). 없으면 스트립 미렌더.
  regimeHistory?: { date: string; stage: string }[]
}) {
  const history = payload.sector_history ?? []
  const sectors = payload.sectors ?? []
  const [mode, setMode] = useState<'rank' | 'momentum'>('rank')

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

  // MP2-SECTOR-CD S2: 모멘텀 시리즈 — momentum_5d 저장값 노출. null(결측)은 점 생략 → connectNulls=false로 선 끊김.
  const momentumSeries: TrendSeries[] = useMemo(
    () =>
      history.map((sh) => ({
        key: sh.symbol,
        label: translate(`sector.${sh.symbol}`, labels, sh.symbol),
        points: sh.history
          .filter((p) => typeof p.momentum_5d === 'number')
          .map((p) => ({
            date: p.date,
            value: p.momentum_5d as number,
            note: `강도 ${p.rel_strength >= 0 ? '+' : ''}${p.rel_strength.toFixed(2)}`,
          })),
      })),
    [history, labels],
  )

  // 강조 기본: 델타 컨텍스트(emphasisOverride)가 있으면 그것을 우선(D-TREND-EMPHASIS 옵션 B),
  //   없으면 서버 rank 기준 leaders(작은 rank 2) + laggards(큰 rank 2). 델타 재계산 없음.
  const emphasisDefault = useMemo(() => {
    if (emphasisOverride && emphasisOverride.length > 0) {
      return Array.from(new Set(emphasisOverride))
    }
    const ranked = [...sectors].filter((s) => typeof s.rank === 'number').sort((a, b) => a.rank - b.rank)
    const leaders = ranked.slice(0, 2).map((s) => s.symbol)
    const laggards = ranked.slice(-2).map((s) => s.symbol)
    return Array.from(new Set([...leaders, ...laggards]))
  }, [sectors, emphasisOverride])

  const vlines = useMemo(() => transitionVlines(transitionDates), [transitionDates])

  // 모멘텀 판정선 = 서빙된 baseline(규칙 #3, y=0 하드코딩 금지). 미서빙 시 hline 생략.
  const momentumHlines = useMemo(() => {
    const b = payload.cd_momentum_baseline
    return typeof b === 'number' ? [{ value: b, label: '판정선' }] : []
  }, [payload.cd_momentum_baseline])

  // 국면 스트립 날짜 창 = 모멘텀 차트와 동일(전 시리즈 통합 날짜 최근 MOMENTUM_WINDOW).
  const stripDates = useMemo(() => {
    const set = new Set<string>()
    momentumSeries.forEach((s) => s.points.forEach((p) => set.add(p.date)))
    const all = Array.from(set).sort()
    return all.slice(Math.max(0, all.length - MOMENTUM_WINDOW))
  }, [momentumSeries])

  const entityCount = series.length || 11

  if (series.length === 0) {
    return <p data-testid="sector-trajectory-empty" className="text-sm text-slate-400">순위 궤적 데이터가 아직 없습니다.</p>
  }

  return (
    <section data-testid="sector-trajectory">
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          {mode === 'rank' ? '섹터 순위 궤적' : '섹터 5일 모멘텀'}
        </p>
        {/* MP2-SECTOR-CD S2: 모드 토글 [순위 | 모멘텀]. 디폴트=순위(no-impact). RegimeComponents 동형. */}
        <div role="tablist" className="flex rounded border border-slate-200 overflow-hidden text-[11px]">
          <button
            type="button"
            role="tab"
            data-testid="traj-mode-rank"
            aria-selected={mode === 'rank'}
            onClick={() => setMode('rank')}
            className={`px-2 py-0.5 ${mode === 'rank' ? 'bg-slate-800 text-white' : 'bg-white text-slate-600'}`}
          >
            순위
          </button>
          <button
            type="button"
            role="tab"
            data-testid="traj-mode-momentum"
            aria-selected={mode === 'momentum'}
            onClick={() => setMode('momentum')}
            className={`px-2 py-0.5 border-l border-slate-200 ${
              mode === 'momentum' ? 'bg-slate-800 text-white' : 'bg-white text-slate-600'
            }`}
          >
            모멘텀
          </button>
        </div>
      </div>

      {mode === 'rank' ? (
        <MultiLineTrendChart
          series={series}
          yAxis={{ inverted: true, domain: [1, entityCount], tickFormat: (v) => `${v}위` }}
          ranges={[7, 30]}
          emphasis={{ default: emphasisDefault, legendToggle: true }}
          overlays={{ vlines }}
          readout={{ pinLatest: true }}
        />
      ) : (
        <>
          <MultiLineTrendChart
            series={momentumSeries}
            yAxis={{ domain: ['auto', 'auto'], tickFormat: (v) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%` }}
            ranges={[MOMENTUM_WINDOW]}
            emphasis={{ default: emphasisDefault, legendToggle: true }}
            overlays={{ vlines, hlines: momentumHlines }}
            readout={{ pinLatest: true }}
            connectNulls={false}
          />
          {/* 국면 스트립 레인 — 차트와 동일 날짜 창(D-SECTOR-MOM-LANE 변형2). */}
          <RegimeStrip dates={stripDates} regimeHistory={regimeHistory} labels={labels} />
        </>
      )}
    </section>
  )
}
