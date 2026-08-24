'use client'

/**
 * PlaybookCardContainer (1.6-S1) — usePlaybook fetch + 봉투 언랩 후 순수 뷰 주입.
 * StressCardContainer 동형(컨테이너=fetch/분기, 뷰=표시).
 */
import { usePlaybook } from '@/hooks/useMarketPulseV2'

import { PlaybookCard } from './PlaybookCard'
import { CardShell } from './CardShell'

export function PlaybookCardContainer() {
  const { data, isLoading, isError } = usePlaybook(true)

  if (isLoading) {
    return (
      <CardShell titleEn="Macro Playbook" titleKo="거시 플레이북">
        <p className="text-sm text-slate-400">불러오는 중…</p>
      </CardShell>
    )
  }
  if (isError || !data) {
    return (
      <CardShell titleEn="Macro Playbook" titleKo="거시 플레이북">
        <p className="text-sm text-slate-400">플레이북을 불러오지 못했습니다</p>
      </CardShell>
    )
  }
  return <PlaybookCard data={data.data} />
}
