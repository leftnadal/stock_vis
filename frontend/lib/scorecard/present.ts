// D1-SCOREBOARD — 성적판 표시 순수 헬퍼 (판정 문장·라벨·포맷).
// 어휘는 BE analyst_scoring 판정 정의와 일치(0-5 실측): hold=방향 판정 대상 아님,
// 무목표가=진행률 제외. 순수 함수 → 단위 테스트 직접 커버.
import type { ScorecardBoard, ScorecardSignal } from '@/types/scorecard'

export function fmtSignedPct(n: number | null | undefined, digits = 1): string {
  if (n == null) return '—'
  return `${n >= 0 ? '+' : ''}${n.toFixed(digits)}%`
}

export function fmtPct(n: number | null | undefined, digits = 1): string {
  if (n == null) return '—'
  return `${n.toFixed(digits)}%`
}

export function hitRatePct(hits: number, total: number): number | null {
  return total > 0 ? (hits / total) * 100 : null
}

const UNSCOREABLE_KO: Record<string, string> = {
  corporate_action: '기간 중 분할 발생 → 채점 불가',
  series_break: '거래 단절 → 채점 불가',
  no_data: '가격 데이터 없음 → 채점 불가',
  no_spot: '기준가 부재 → 채점 불가',
}

export function unscoreableLabelKo(reason: string | null): string {
  if (!reason) return '채점 불가'
  return UNSCOREABLE_KO[reason] ?? `채점 불가 (${reason})`
}

// 표본 라벨: 방향 적중 분모가 유의 최소 표본(significance_threshold) 미만이면 '참고용'.
export function sampleLabel(board: ScorecardBoard): string {
  const total = board.direction_hit.total
  if (total >= board.significance_threshold) return '유의 표본'
  return `참고용 (표본 ${total}/${board.significance_threshold})`
}

// 신호 1건 판정 문장 (공감 층). 방향/판정/상태에 따라 어휘 분기.
export function verdictSentence(s: ScorecardSignal): string {
  if (s.status === 'pending') {
    const d = s.pending_d_day
    const dtag = d != null && d >= 0 ? `D-${d}` : 'D-?'
    const mat = s.maturity_date ? ` (예상 만기 ${s.maturity_date})` : ''
    return `만기 ${dtag} 대기 중${mat}`
  }
  if (s.status === 'unscoreable') {
    return unscoreableLabelKo(s.unscoreable_reason)
  }
  const r = s.realized
  if (!r || r.return_pct == null) return '실현값 없음'
  const ret = fmtSignedPct(r.return_pct)
  const move = r.return_pct >= 0 ? '상승' : '하락'
  if (s.direction === 'up') {
    return r.verdict === 'hit'
      ? `상승 전망 → ${ret} ${move} (적중)`
      : `상승 전망이었으나 ${ret} ${move}`
  }
  if (s.direction === 'down') {
    return r.verdict === 'hit'
      ? `하락 전망 → ${ret} ${move} (적중)`
      : `하락 전망이었으나 ${ret} ${move}`
  }
  if (s.direction === 'flat') {
    return `유지 전망 → ${ret} ${move} (방향 판정 대상 아님)`
  }
  return `목표가 미제시 → ${ret} ${move}`
}

export const DIRECTION_KO: Record<'up' | 'down' | 'flat', string> = {
  up: '상승',
  down: '하락',
  flat: '유지',
}
