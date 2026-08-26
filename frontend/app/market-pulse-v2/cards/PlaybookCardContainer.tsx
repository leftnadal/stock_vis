'use client'

/**
 * PlaybookCardContainer (1.6-S1) — usePlaybook fetch + 봉투 언랩 후 순수 뷰 주입.
 * StressCardContainer 동형(컨테이너=fetch/분기, 뷰=표시).
 *
 * INC-P16-1 Part B: fold 아래 카드라 뷰포트 진입 시점까지 fetch를 늦춘다(useInViewOnce).
 * 진입 후 렌더 결과는 1.6-S1과 동일 — lazy는 fetch 시점만 늦추고 뷰는 불변.
 */
import { useInViewOnce } from '@/hooks/useInViewOnce'
import { usePlaybook } from '@/hooks/useMarketPulseV2'

import { PlaybookCard } from './PlaybookCard'
import { CardShell } from './CardShell'

export function PlaybookCardContainer() {
  const { ref, hasEntered } = useInViewOnce<HTMLDivElement>()
  const { data, isLoading, isError } = usePlaybook(hasEntered)

  // 뷰포트 진입 전: fetch 하지 않고 자리표시(loading과 동일 셸 → 진입 시 레이아웃 시프트 0).
  // ref로 진입을 감지 → hasEntered 래치 → usePlaybook 활성화.
  if (!hasEntered) {
    return (
      <div ref={ref}>
        <CardShell titleEn="Macro Playbook" titleKo="거시 플레이북">
          <p className="text-sm text-slate-400">불러오는 중…</p>
        </CardShell>
      </div>
    )
  }

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
