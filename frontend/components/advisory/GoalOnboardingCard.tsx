'use client'

// 목표 부재 시 온보딩 카드 (Slice 20b-f2) — GoalForm(mode="create") + POST 생성.
// 성공 시 useCreateGoal이 knobs/latest/summary 재검증 → 목표 부재 화면이 권유 화면으로 전환.
import { GoalForm, type GoalFormValues } from '@/components/advisory/GoalForm'
import { useCreateGoal } from '@/hooks/useAdvisory'
import type { GoalCreateInput } from '@/types/advisory'

export function GoalOnboardingCard() {
  const createM = useCreateGoal()

  const handleSubmit = async (v: GoalFormValues) => {
    const input: GoalCreateInput = {
      target_return_pct: v.target_return_pct,
      horizon_months: v.horizon_months,
      risk_tolerance: v.risk_tolerance,
      aggressiveness_offset: v.aggressiveness_offset,
      growth_boost: v.growth_boost,
      diversification_weight: v.diversification_weight,
      concentration_limit: v.concentration_limit,
      exploration_ratio: v.exploration_ratio,
    }
    // 성공 시 onSuccess가 3키 재검증 → 화면 전환. 실패(409/400)는 throw → GoalForm 인라인 에러.
    await createM.mutateAsync(input)
  }

  return (
    <div
      data-testid="goal-onboarding-card"
      className="flex flex-col gap-4 rounded-2xl border border-blue-200 bg-blue-50/40 p-6 dark:border-blue-900 dark:bg-blue-900/10"
    >
      <div>
        <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
          투자 목표를 만들어 코치를 시작하세요
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          목표 수익률·기간·성향을 설정하면 매일 밤 자동 진단이 기록되고, 배치 갭·모드가 계산됩니다.
          손잡이는 기본(보수)값에서 시작해 언제든 조정할 수 있어요.
        </p>
      </div>
      <GoalForm
        mode="create"
        onSubmit={handleSubmit}
        isPending={createM.isPending}
        submitLabel="목표 만들기"
      />
    </div>
  )
}
