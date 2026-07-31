'use client'

// 손잡이 5종 + 목표 수익률 편집 패널 (Slice 20b) — 20b-f2에서 GoalForm(mode="edit")으로
// 폼 코어 추출(D-f2-2, 행위보존). 이 컴포넌트 = 얇은 래퍼: useUpdateKnobs(PATCH) 주입.
// 저장 = PATCH advisory/knobs/. **저장 ≠ 진단 실행**(D2 — [지금 진단] 별도 경유).
import { GoalForm, type GoalFormValues } from '@/components/advisory/GoalForm'
import { useUpdateKnobs } from '@/hooks/useAdvisory'
import type { KnobsRead, KnobsUpdateInput } from '@/types/advisory'

interface KnobsPanelProps {
  knobs: KnobsRead
}

export function KnobsPanel({ knobs }: KnobsPanelProps) {
  const updateM = useUpdateKnobs()

  const handleSubmit = async (v: GoalFormValues) => {
    // 손잡이 5종은 전부 string 전송(Decimal 정밀도), target은 값 있을 때만(부분 PATCH)
    const payload: KnobsUpdateInput = {
      aggressiveness_offset: v.aggressiveness_offset,
      growth_boost: v.growth_boost,
      diversification_weight: v.diversification_weight,
      concentration_limit: v.concentration_limit,
      exploration_ratio: v.exploration_ratio,
    }
    if (v.target_return_pct !== '') payload.target_return_pct = v.target_return_pct
    await updateM.mutateAsync(payload)
  }

  return (
    <GoalForm
      mode="edit"
      initial={knobs}
      onSubmit={handleSubmit}
      isPending={updateM.isPending}
      submitLabel="손잡이 저장"
      savedLabel="저장됐어요"
    />
  )
}
