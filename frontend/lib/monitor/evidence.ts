// Claim 근거 표시 유틸 (RECON-SWAP-0813 PART 1/3-A) — 렌더 전용, 판정은 BE evidence-status 단일 소스.
import type { EvidenceKind, EvidenceLifeStatus } from '@/types/monitor'

// 출처 3색 배지(수동/규칙/통계). 근거는 auto=규칙·manual=수동 둘 중 하나만 쓴다.
// stat(통계)은 대결 화면 통계층 카드가 쓴다 — 3색 체계를 여기서 단일 정의(중복 정의 금지).
export type SourceTone = 'manual' | 'rule' | 'stat'

export const SOURCE_TONE_META: Record<SourceTone, { label: string; cls: string }> = {
  manual: {
    label: '수동',
    cls: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  },
  rule: {
    label: '규칙',
    cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  },
  stat: {
    label: '통계',
    cls: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
  },
}

export function evidenceKindToTone(kind: EvidenceKind): SourceTone {
  return kind === 'auto' ? 'rule' : 'manual'
}

// 근거 생사 상태 배지(계약층 — evidence-status 응답 status 미러 표시).
export const EVIDENCE_STATUS_META: Record<EvidenceLifeStatus, { label: string; cls: string }> = {
  alive: {
    label: '생존',
    cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  },
  dead: {
    label: '소멸',
    cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  },
  expired: {
    label: '기한만료',
    cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  },
  unknown: {
    label: '판정불가',
    cls: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
  },
}

// 수동형 유통기한 D-n — BE _judge_manual과 동일 산식(baseline + recheck_period_days − 오늘).
// ⚠️ 표시 보조용 클라이언트 재계산이다. "생존/기한만료" 판정 자체의 단일 소스는 여전히
// evidence-status 응답(status 필드) — 이 함수는 그 옆에 붙는 "D-n" 카운트다운 라벨만 만든다.
export function manualExpiryDday(evidence: {
  last_confirmed_at: string | null
  recheck_period_days: number
  created_at: string
}): number {
  const baselineStr = evidence.last_confirmed_at ?? evidence.created_at.slice(0, 10)
  const due = new Date(`${baselineStr}T00:00:00`)
  due.setDate(due.getDate() + evidence.recheck_period_days)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((due.getTime() - today.getTime()) / 86400000)
}
