// verdict 라벨 단일 소스 (TIMING-P2 §6) — VerdictBadge·CloseModal이 이 모듈만 소비(분산 해소).
// 매수 타이밍 행동어: 익절/부분 실현/손절/기한만료. inconclusive는 존치(중립).
import { GRADE_CHIP } from '@/components/common/colorSemantics'
import type { ProposedVerdict, Verdict } from '@/types/monitor'

// colorSemantics(GRADE_CHIP)는 gray/yellow/orange/red까지 — validated(익절)의 green은
// 방향축 밖이라 여기서만 로컬 정의(단일 소비처).
const GREEN_CHIP =
  'bg-green-50 text-green-700 border-green-300 dark:bg-green-900/25 dark:text-green-300 dark:border-green-700'

export interface VerdictMeta {
  label: string
  chip: string
}

// outcome/verdict → 행동어 라벨 + 배지 색. 5종(익절/부분 실현/손절/기한만료/불명확).
export const VERDICT_META: Record<Verdict | 'expired', VerdictMeta> = {
  validated: { label: '익절', chip: GREEN_CHIP },
  partial: { label: '부분 실현', chip: GRADE_CHIP.yellow },
  invalidated: { label: '손절', chip: GRADE_CHIP.red },
  expired: { label: '기한만료', chip: GRADE_CHIP.gray },
  inconclusive: { label: '불명확', chip: GRADE_CHIP.gray },
}

export function verdictMeta(v: Verdict): VerdictMeta {
  return VERDICT_META[v] ?? VERDICT_META.inconclusive
}

// 마감 모달에서 사용자가 고를 수 있는 최종 판정 (inconclusive 제외 — 엣지, 버튼 미노출).
export const VERDICT_OPTIONS: { key: ProposedVerdict; label: string }[] = [
  { key: 'validated', label: VERDICT_META.validated.label },
  { key: 'partial', label: VERDICT_META.partial.label },
  { key: 'invalidated', label: VERDICT_META.invalidated.label },
  { key: 'expired', label: VERDICT_META.expired.label },
]
