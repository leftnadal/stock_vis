// Claim 마감 파생 유틸 (MON-CLOSE-UI Phase 2) — 렌더 전용.
// ⚠️ Monitor.State는 Claim 마감과 무관하게 계속 갱신된다(D-MONITOR-REBUILD 불변) — 이
// 파일은 카드/상세의 "몇 건 중 몇 건 마감" 파생만 담당한다. 진짜 마감 시점 동결값
// (ClosureSnapshot.overall_score)은 이번 Phase의 API 계약에 노출되지 않으므로(ClaimSerializer
// 미포함, 전용 엔드포인트 없음) monitor.latest_score로 근사한다 — closure.py
// current_overall_score()의 주석대로 "최신 스냅샷 = 카드와 동일 소스"라 값 자체는 같다.
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
