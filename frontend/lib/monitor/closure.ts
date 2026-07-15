// Claim 마감 파생 유틸 (MON-CLOSE-UI Phase 2·P1.5) — 렌더 전용.
// ⚠️ Monitor.State는 Claim 마감과 무관하게 계속 갱신된다(D-MONITOR-REBUILD 불변) — 이
// 파일은 카드/상세의 "몇 건 중 몇 건 마감" 파생 + 동결값 표시 우선순위를 담당한다.
// P1.5에서 BE가 ClosureSnapshot을 노출 → resolved Claim은 closure_snapshot.overall_score
// (마감 시점 불변 동결값)를 우선 사용, PENDING은 live 값. frozenScore 참조.
import type { Claim, ClaimOutcome, Verdict } from '@/types/monitor'

export interface ClaimClosureSummary {
  total: number
  resolved: number
  isFullyClosed: boolean
  lastResolvedClaim: Claim | null
}

// 모니터 소속 Claim 배열 → 마감 파생 요약. claims=[]면 항상 "진행 중"(has_claim=false와 동치).
export function summarizeClaimClosure(claims: Claim[]): ClaimClosureSummary {
  const total = claims.length
  const resolvedClaims = claims.filter((c) => c.outcome !== 'pending')
  const resolved = resolvedClaims.length
  const lastResolvedClaim = resolvedClaims.length
    ? resolvedClaims.reduce((a, b) => ((a.resolved_at ?? '') > (b.resolved_at ?? '') ? a : b))
    : null

  return {
    total,
    resolved,
    isFullyClosed: total > 0 && resolved === total,
    lastResolvedClaim,
  }
}

// outcome→VerdictBadge 표시값. pending은 호출측이 걸러야 하지만(마감 버튼 분기)
// 방어적으로 중립(inconclusive)로 폴백.
export function outcomeToVerdict(outcome: ClaimOutcome): Verdict {
  return outcome === 'pending' ? 'inconclusive' : outcome
}

// 표시 우선순위(P1.5): resolved Claim = 동결값(closure_snapshot.overall_score),
// PENDING/누락 = liveFallback. closure_snapshot이 null인 resolved(이론상 없음)는 조용히 live 폴백.
export function frozenScore(
  claim: Claim | null | undefined,
  liveFallback: number | null = null,
): number | null {
  if (!claim) return liveFallback
  return claim.closure_snapshot?.overall_score ?? liveFallback
}
