// 2종 대결 화면 순수 로직 (RECON-SWAP-0813 PART 3-B) — 규칙 기반, LLM 호출 없음.
// ⚠️ 불변 요소: 여기서 산출하는 값은 전부 "사실 나열"이다 — 어느 쪽도 이기지 않는다(종합 도장 금지).
import type { EvidenceStatusResponse, SwapHoldLog } from '@/types/monitor'

// ── 마찰층(간이 어림) ──

export type FrictionDirection = 'cost' | 'relief' | 'neutral' | 'unheld'

export interface FrictionEstimate {
  direction: FrictionDirection
  unrealizedPct: number | null
  note: string
}

// 마찰층 간이 어림 — Wallet 평단·현재가 "부호"만 본다(세율·수수료율 실측 미반영).
// 정식 산식은 SPIN-2 예정(표기) — 반드시 "어림" 배지와 함께 노출한다.
export function estimateFriction(
  avgCost: string | null | undefined,
  currentPrice: string | null | undefined
): FrictionEstimate {
  if (avgCost == null || currentPrice == null) {
    return { direction: 'unheld', unrealizedPct: null, note: '미보유 — 마찰 방향 산출 대상 아님' }
  }
  const a = Number(avgCost)
  const c = Number(currentPrice)
  if (!Number.isFinite(a) || a <= 0 || !Number.isFinite(c)) {
    return { direction: 'neutral', unrealizedPct: null, note: '가격 정보 부족 — 마찰 방향 산출 불가' }
  }
  const pct = (c / a - 1) * 100
  if (pct > 1) {
    return {
      direction: 'cost',
      unrealizedPct: pct,
      note: '평가이익 상태 — 지금 정리하면 세금·수수료 비용이 발생하는 방향(어림)',
    }
  }
  if (pct < -1) {
    return {
      direction: 'relief',
      unrealizedPct: pct,
      note: '평가손실 상태 — 손실 상계 여지가 있는 방향(어림)',
    }
  }
  return { direction: 'neutral', unrealizedPct: pct, note: '손익 중립 구간 — 마찰 방향 미미(어림)' }
}

// ── 판단 성립 조건 ──

export interface JudgmentAvailability {
  available: boolean
  reasons: string[]
  nextConditions: string[]
}

// 판단 성립 조건 (RECON-SWAP-0813 3-B) — 근거 unknown 다수·데이터 부족 시 정식 "판단 불가".
export function checkJudgmentAvailability(params: {
  hasClaim: boolean
  evidenceTotal: number
  unknownCount: number
}): JudgmentAvailability {
  const reasons: string[] = []
  const nextConditions: string[] = []
  if (!params.hasClaim) {
    reasons.push('등록된 매수 시나리오(Claim)가 없어요')
    nextConditions.push('대상에 시나리오를 먼저 등록하세요')
  }
  if (params.evidenceTotal === 0) {
    reasons.push('등록된 근거가 없어요')
    nextConditions.push('근거를 최소 1건 등록하세요')
  } else if (params.unknownCount / params.evidenceTotal >= 0.5) {
    const pct = Math.round((params.unknownCount / params.evidenceTotal) * 100)
    reasons.push(`근거 판정불가 비율 ${pct}%로 근거 대부분을 신뢰할 수 없어요`)
    nextConditions.push('지표 데이터가 더 쌓인 뒤 재관측하세요')
  }
  return { available: reasons.length === 0, reasons, nextConditions }
}

// ── 반론 의무 슬롯(규칙 템플릿, LLM 금지) ──

export interface CounterArgumentInput {
  sideLabel: string
  evidenceTotal: number
  evidenceAlive: number
  manualCount: number
  deadOrExpiredCount: number
  gapMultiplier: number
  friction: FrictionDirection
}

export interface CounterArgument {
  headline: string
  facts: string[]
}

// 반론 의무 슬롯 — 규칙이 산출한 "사실"만 조합한다(추천·점수화 금지, ADR §6/불변 요소).
// facts는 최대 3개로 고정 — 양측 슬롯의 "동분량"을 형태로 보장한다.
export function buildCounterArgument(input: CounterArgumentInput): CounterArgument {
  const facts: string[] = []

  if (input.evidenceTotal > 0) {
    const manualRatio = input.manualCount / input.evidenceTotal
    if (manualRatio >= 0.5) {
      facts.push(
        `근거 ${input.evidenceTotal}건 중 수동형 ${input.manualCount}건(${Math.round(manualRatio * 100)}%) — 자동 감시 밖`
      )
    }
    if (input.deadOrExpiredCount > 0) {
      facts.push(
        `근거 ${input.deadOrExpiredCount}건 소멸/기한만료 — 생존 ${input.evidenceAlive}/${input.evidenceTotal}`
      )
    }
  } else {
    facts.push('등록된 근거 없음 — 관측 근거 자체가 없어요')
  }

  if (input.gapMultiplier >= 1.5) {
    facts.push(`갭 체질 배수 ${input.gapMultiplier.toFixed(1)}배 — 유니버스 대비 갭 위험이 높아요`)
  }

  if (input.friction === 'cost') {
    facts.push('평가이익 상태 — 지금 정리하면 비용(어림)이 발생하는 방향이에요')
  }

  if (facts.length === 0) {
    facts.push('특이 리스크 신호가 없어요 — 반론 근거가 약해요')
  }

  return {
    headline: `${input.sideLabel} 반대 근거`,
    facts: facts.slice(0, 3),
  }
}

// evidence-status 응답 → 반론 슬롯 입력으로 축약(집계만, 판정 없음).
export function summarizeEvidenceStatus(status: EvidenceStatusResponse | undefined) {
  const results = status?.results ?? []
  return {
    total: status?.total ?? 0,
    alive: status?.alive ?? 0,
    manualCount: results.filter((r) => r.kind === 'manual').length,
    unknownCount: results.filter((r) => r.status === 'unknown').length,
    deadOrExpiredCount: results.filter((r) => r.status === 'dead' || r.status === 'expired')
      .length,
  }
}

// ── P-1 보류 계기판 ──

export interface HoldGaugeSummary {
  count: number
  firstHeldAt: string | null
  // 2회째부터만 값 채움(1회째는 "누적"이라 부를 근거 없음) — 불변 요소 문구와 동일 원칙(과장 금지).
  cumulativeDays: number | null
}

// ── P-2b: 목표 상향 재커밋(원 목표 도달 시 지정 문구로 회고 재인용 대비) ──
export const P2B_RECOMMIT_SENTENCE = '원 목표 도달 — 익절 기회 포기'

export function summarizeHoldGauge(logs: SwapHoldLog[]): HoldGaugeSummary {
  if (logs.length === 0) return { count: 0, firstHeldAt: null, cumulativeDays: null }
  const sorted = [...logs].sort((a, b) => a.held_at.localeCompare(b.held_at))
  const firstHeldAt = sorted[0].held_at
  const cumulativeDays =
    logs.length >= 2
      ? Math.max(0, Math.round((Date.now() - new Date(firstHeldAt).getTime()) / 86400000))
      : null
  return { count: logs.length, firstHeldAt, cumulativeDays }
}

// ── P-1 보류 계기판 "양측 기간 성과·격차" (스냅샷 기반, 갭 2) ──
// 앵커 = 최초 보류 로그(summarizeHoldGauge와 동일 기준점)의 hold_price/candidate_price.
// anchor_missing = 스냅샷 신설 이전 구 기록(가격 null) — 조작 없이 정직 표기.
// no_current_price = 앵커는 있으나 지금 대조할 현재가 소스가 없음(예: 후보 미보유 → 가격 API 부재).
export type PerformanceGapReason = 'anchor_missing' | 'no_current_price' | null

export interface HoldGaugePerformance {
  holdPerformancePct: number | null
  holdPerformanceReason: PerformanceGapReason
  candidatePerformancePct: number | null
  candidatePerformanceReason: PerformanceGapReason
  gapPct: number | null // 보유 성과 − 후보 성과
}

function sidePerformance(
  anchorPrice: string | null,
  currentPrice: string | null | undefined
): { pct: number | null; reason: PerformanceGapReason } {
  if (anchorPrice == null) return { pct: null, reason: 'anchor_missing' }
  const anchor = Number(anchorPrice)
  if (!Number.isFinite(anchor) || anchor <= 0) return { pct: null, reason: 'anchor_missing' }
  if (currentPrice == null) return { pct: null, reason: 'no_current_price' }
  const current = Number(currentPrice)
  if (!Number.isFinite(current)) return { pct: null, reason: 'no_current_price' }
  return { pct: (current / anchor - 1) * 100, reason: null }
}

// PART C-4 — BE가 held_at 스냅샷→최신 종가(DailyPrice)로 계산한 서버 산출 성과가 있으면
// 그걸 우선 소비한다(후보 미보유라도 DailyPrice 이력만 있으면 산출됨 — "현재가 데이터 없음"
// 오표기 해소). BE 필드가 없는(구 배포·구 기록) 로그만 기존 Wallet 현재가 계산으로 폴백한다.
export function computeHoldGaugePerformance(
  logs: SwapHoldLog[],
  currentHoldPrice: string | null | undefined,
  currentCandidatePrice: string | null | undefined
): HoldGaugePerformance {
  if (logs.length < 2) {
    return {
      holdPerformancePct: null,
      holdPerformanceReason: null,
      candidatePerformancePct: null,
      candidatePerformanceReason: null,
      gapPct: null,
    }
  }
  const anchor = [...logs].sort((a, b) => a.held_at.localeCompare(b.held_at))[0]

  // BE 필드가 "정의(defined)"되어 있으면(응답에 키가 존재) 그 값을 신뢰한다 — null이어도 BE가
  // 계산을 시도했으나 데이터가 없다는 뜻(no_current_price)이지 "구 기록"은 아니다. 필드 자체가
  // 없는(undefined, 구 배포 응답) 경우에만 기존 Wallet 현재가 계산 폴백(anchor_missing 판정 포함)으로 내려간다.
  const hold =
    anchor.hold_performance_pct !== undefined
      ? {
          pct: anchor.hold_performance_pct,
          reason: (anchor.hold_performance_pct == null
            ? 'no_current_price'
            : null) as PerformanceGapReason,
        }
      : sidePerformance(anchor.hold_price, currentHoldPrice)

  const candidate =
    anchor.candidate_performance_pct !== undefined
      ? {
          pct: anchor.candidate_performance_pct,
          reason: (anchor.candidate_performance_pct == null
            ? 'no_current_price'
            : null) as PerformanceGapReason,
        }
      : sidePerformance(anchor.candidate_price, currentCandidatePrice)

  return {
    holdPerformancePct: hold.pct,
    holdPerformanceReason: hold.reason,
    candidatePerformancePct: candidate.pct,
    candidatePerformanceReason: candidate.reason,
    gapPct: hold.pct != null && candidate.pct != null ? hold.pct - candidate.pct : null,
  }
}
