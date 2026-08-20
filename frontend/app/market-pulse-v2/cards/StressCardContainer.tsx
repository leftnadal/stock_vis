/**
 * MPS-2 — StressCard 컨테이너 (fetch + 로딩/에러/available 분기).
 *
 * 소속: market-pulse-v2/cards. useRegimeStress로 regime/stress 조회 → 봉투 언랩 후 뷰 주입.
 *   컨테이너(fetch+분기)/순수 뷰 분리 관례(AnalogCardContainer 동형).
 */
'use client'

import { CardShell } from './CardShell'
import { StressCard } from './StressCard'
import { useRegimeStress } from '@/hooks/useMarketPulseV2'

export function StressCardContainer() {
  const { data, isLoading, isError } = useRegimeStress(true)

  if (isLoading) {
    return (
      <CardShell titleEn="Market Stress" titleKo="시장 스트레스">
        <div data-testid="stress-loading" className="text-sm text-slate-400">
          불러오는 중…
        </div>
      </CardShell>
    )
  }

  if (isError || !data) {
    return (
      <CardShell titleEn="Market Stress" titleKo="시장 스트레스">
        <div data-testid="stress-error" className="text-sm text-rose-600">
          스트레스 지표를 불러오지 못했습니다.
        </div>
      </CardShell>
    )
  }

  return <StressCard data={data.data} />
}
