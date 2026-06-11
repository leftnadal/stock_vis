'use client'

import { useCardDetail } from '@/hooks/useMarketPulseV2'
import type {
  BreadthDetail as Breadth,
  BriefDetail as Brief,
  ConcentrationDetail as Concentration,
  RegimeDetail as Regime,
  SectorDetail as Sector,
} from '@/lib/api/marketPulseV2'

import { BreadthDetail } from './BreadthDetail'
import { BriefDetail } from './BriefDetail'
import { ConcentrationDetail } from './ConcentrationDetail'
import { RegimeDetail } from './RegimeDetail'
import { SectorDetail } from './SectorDetail'

type CardId = 'regime' | 'breadth' | 'sector' | 'concentration' | 'brief'

export function CardDetailContainer({ cardId, enabled }: { cardId: CardId; enabled: boolean }) {
  const { data, isLoading, isError, error, refetch } = useCardDetail<Record<string, unknown>>(cardId, enabled)

  if (!enabled) return null
  if (isLoading) return <p className="text-sm text-slate-500">불러오는 중…</p>
  if (isError) {
    return (
      <div className="text-sm text-rose-700">
        <p>상세 정보를 불러오지 못했습니다.</p>
        <button type="button" className="mt-2 text-xs text-slate-700 underline" onClick={() => refetch()}>
          다시 시도
        </button>
        {process.env.NODE_ENV !== 'production' && error ? (
          <pre className="mt-2 text-xs">{(error as Error).message}</pre>
        ) : null}
      </div>
    )
  }
  if (!data) return null

  const payload = data.data as Record<string, unknown>
  const cacheState = data._meta.cache

  return (
    <div>
      <p className="text-xs text-slate-400 mb-2">cache: {cacheState}</p>
      {cardId === 'regime' && <RegimeDetail payload={payload as unknown as Regime} />}
      {cardId === 'breadth' && <BreadthDetail payload={payload as unknown as Breadth} />}
      {cardId === 'sector' && <SectorDetail payload={payload as unknown as Sector} />}
      {cardId === 'concentration' && <ConcentrationDetail payload={payload as unknown as Concentration} />}
      {cardId === 'brief' && <BriefDetail payload={payload as unknown as Brief} />}
    </div>
  )
}
