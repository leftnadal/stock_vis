'use client'

import { useState } from 'react'

import { useOverview } from '@/hooks/useMarketPulseV2'
import { useMarketPulseI18n, translate } from '@/lib/i18n/marketPulse'

import { AnomalyPanel } from './components/AnomalyPanel'
import { CardDrawer } from './components/CardDrawer'
import { NewsPanel } from './components/NewsPanel'
import { StatusBanner } from './components/StatusBanner'
import { TickerBar } from './components/TickerBar'
import { BreadthCardSummary } from './cards/BreadthCardSummary'
import { BriefCardSummary } from './cards/BriefCardSummary'
import { ConcentrationCardSummary } from './cards/ConcentrationCardSummary'
import { DeltaCard } from './cards/DeltaCard'
import { RegimeCardSummary } from './cards/RegimeCardSummary'
import { SectorHeatmap } from './cards/SectorHeatmap'
import { CardDetailContainer } from './details/CardDetailContainer'
import { REGIME_TERM } from './meaning'
import { selectSense } from './translationSelector'

type CardId = 'regime' | 'breadth' | 'sector' | 'concentration' | 'brief'

const CARD_TITLE: Record<CardId, string> = {
  regime: `Market Regime · 시장 ${REGIME_TERM}`,
  breadth: 'Market Breadth · 시장 폭',
  sector: 'Sector Flow · 섹터 흐름',
  concentration: 'Concentration · 집중도',
  brief: 'Briefing · 브리핑',
}

export default function MarketPulseV2Page() {
  const { data: overview, isLoading, isError, refetch } = useOverview()
  const { data: i18n } = useMarketPulseI18n()
  const labels = i18n?.labels
  const [openCard, setOpenCard] = useState<CardId | null>(null)

  if (isLoading) {
    return (
      <PageShell title="Market Pulse v2">
        <p className="text-slate-500">불러오는 중…</p>
      </PageShell>
    )
  }
  if (isError || !overview) {
    return (
      <PageShell title="Market Pulse v2">
        <p className="text-rose-700 mb-2">데이터를 불러오지 못했습니다.</p>
        <button type="button" className="text-sm underline text-slate-700" onClick={() => refetch()}>
          다시 시도
        </button>
      </PageShell>
    )
  }

  const meta = overview._meta
  // S4: translations envelope → 카드별 sense 주입(fallback이 정상 경로 — null이면 카드는 밴드만).
  const translations = overview.translations

  return (
    <PageShell title="Market Pulse v2">
      {/* ① Ticker Bar */}
      <TickerBar items={overview.ticker_bar} />

      <div className="px-2 py-3">
        {/* ② Status Banner */}
        <StatusBanner status={meta.status} reason={meta.status_reason} labels={labels} />

        {/* ③ Regime hero (full-width) — D-MP2-SURFACE 변형1 위계 1번 */}
        <div className="mt-4">
          <RegimeCardSummary
            data={overview.cards.regime}
            labels={labels}
            onOpen={() => setOpenCard('regime')}
            sense={selectSense(translations, 'regime')}
          />
        </div>

        {/* ③b Delta Card — 어제와 달라진 것 (MP2-DELTA Slice 1) */}
        <div className="mt-4">
          <DeltaCard
            regime={overview.cards.regime}
            sectorDeltas={overview.sector_deltas}
            anomalyDelta={overview.anomaly_delta}
            labels={labels}
            onOpenTrajectory={() => setOpenCard('sector')}
          />
        </div>

        {/* ④ Anomaly Panel — 위계 2번 */}
        <AnomalyPanel data={overview.anomaly} labels={labels} />

        {/* ⑤ Sector 히트맵 (full-width) — 위계 3번 */}
        <SectorHeatmap labels={labels} onOpen={() => setOpenCard('sector')} sense={selectSense(translations, 'sector')} />

        {/* ⑥ Brief (prose) — 위계 4번 */}
        <div className="mt-4">
          <BriefCardSummary data={overview.cards.brief} onOpen={() => setOpenCard('brief')} />
        </div>

        {/* ⑦ Grid: Breadth + Concentration — 위계 5번 */}
        <section className="mt-4 grid gap-3 sm:grid-cols-2">
          <BreadthCardSummary
            data={overview.cards.breadth}
            labels={labels}
            onOpen={() => setOpenCard('breadth')}
            sense={selectSense(translations, 'breadth')}
          />
          <ConcentrationCardSummary
            data={overview.cards.concentration}
            labels={labels}
            onOpen={() => setOpenCard('concentration')}
            sense={selectSense(translations, 'concentration')}
          />
        </section>

        {/* ⑧ News */}
        <NewsPanel items={overview.news} labels={labels} />

        {/* ⑨ Footer */}
        <footer className="text-[10px] text-slate-400 mt-6 px-1 py-2">
          generated_at {meta.generated_at} · {meta.latency_ms}ms · cache {meta.cache || '—'}
          {' · '}
          {meta.data_finalized ? 'finalized' : 'live'}
          {' · '}
          status {translate(`status.${meta.status}`, labels, meta.status)}
        </footer>
      </div>

      {/* CardDrawer: 5카드 드로어 전부 살아있어야 함 (sector 포함) */}
      <CardDrawer
        open={openCard !== null}
        onClose={() => setOpenCard(null)}
        title={openCard ? CARD_TITLE[openCard] : ''}
      >
        {openCard ? <CardDetailContainer cardId={openCard} enabled={openCard !== null} labels={labels} /> : null}
      </CardDrawer>
    </PageShell>
  )
}

function PageShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <main className="max-w-3xl mx-auto pb-12">
      <header className="px-2 pt-4">
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        <p className="text-xs text-slate-500 mt-1">Phase 1 · Beta · Layer 0 + Layer 1</p>
      </header>
      {children}
    </main>
  )
}
