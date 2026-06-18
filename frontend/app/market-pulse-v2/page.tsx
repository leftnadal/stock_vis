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
import { RegimeCardSummary } from './cards/RegimeCardSummary'
import { SectorCardSummary } from './cards/SectorCardSummary'
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
      <TickerBar items={overview.ticker_bar} />
      <div className="px-2 py-3">
        <StatusBanner status={meta.status} reason={meta.status_reason} labels={labels} />

        <AnomalyPanel data={overview.anomaly} labels={labels} />

        <section className="mt-4 grid gap-3 sm:grid-cols-2">
          <RegimeCardSummary
            data={overview.cards.regime}
            labels={labels}
            onOpen={() => setOpenCard('regime')}
            sense={selectSense(translations, 'regime')}
          />
          <BreadthCardSummary data={overview.cards.breadth} labels={labels} onOpen={() => setOpenCard('breadth')} sense={selectSense(translations, 'breadth')} />
          <SectorCardSummary data={overview.cards.sector} labels={labels} onOpen={() => setOpenCard('sector')} sense={selectSense(translations, 'sector')} />
          <ConcentrationCardSummary data={overview.cards.concentration} labels={labels} onOpen={() => setOpenCard('concentration')} sense={selectSense(translations, 'concentration')} />
          <BriefCardSummary data={overview.cards.brief} onOpen={() => setOpenCard('brief')} />
        </section>

        <NewsPanel items={overview.news} labels={labels} />

        <footer className="text-[10px] text-slate-400 mt-6 px-1 py-2">
          generated_at {meta.generated_at} · {meta.latency_ms}ms · cache {meta.cache || '—'}
          {' · '}
          {meta.data_finalized ? 'finalized' : 'live'}
          {' · '}
          status {translate(`status.${meta.status}`, labels, meta.status)}
        </footer>
      </div>

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
