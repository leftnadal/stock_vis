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

export function CardDetailContainer({
  cardId, enabled, labels, emphasisOverride,
}: {
  cardId: CardId
  enabled: boolean
  labels?: Record<string, string>
  // MP2-TREND S2(D-TREND-EMPHASIS 옵션 B): 델타→섹터 강조 복원용. 선택적·무영향 기본값(안전판 준수).
  emphasisOverride?: string[]
}) {
  const { data, isLoading, isError, error, refetch } = useCardDetail<Record<string, unknown>>(cardId, enabled)
  // MP2-TREND S2: 전환일 세로선 공용 계약 — breadth·sector 궤적이 regime의 transition_dates를 소비.
  //   컨테이너(데이터 계층)가 조회해 순수 상세 뷰에 prop 전달(뷰는 QueryClient 불요). 캐시 5분.
  const needsTransitions = enabled && (cardId === 'breadth' || cardId === 'sector')
  const { data: regime } = useCardDetail<Regime>('regime', needsTransitions)
  const transitionDates = regime?.data?.transition_dates ?? []
  // MP2-SECTOR-CD S2: 국면 스트립 데이터원 — 동일 regime 조회의 regime_history_30d 재사용(신규 fetch 0).
  const regimeHistory = regime?.data?.regime_history_30d ?? []

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
      {/* cache_state는 디버그 메타 — 엔드유저 비노출(dev 전용). 봉투 데이터는 무변경. */}
      {process.env.NODE_ENV !== 'production' ? (
        <p className="text-xs text-slate-400 mb-2">cache: {cacheState}</p>
      ) : null}
      {cardId === 'regime' && <RegimeDetail payload={payload as unknown as Regime} labels={labels} />}
      {cardId === 'breadth' && <BreadthDetail payload={payload as unknown as Breadth} labels={labels} transitionDates={transitionDates} />}
      {cardId === 'sector' && <SectorDetail payload={payload as unknown as Sector} labels={labels} transitionDates={transitionDates} emphasisOverride={emphasisOverride} regimeHistory={regimeHistory} />}
      {cardId === 'concentration' && <ConcentrationDetail payload={payload as unknown as Concentration} labels={labels} />}
      {cardId === 'brief' && <BriefDetail payload={payload as unknown as Brief} />}
    </div>
  )
}
