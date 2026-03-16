import { differenceInDays } from 'date-fns'
import type { ThesisState, ThesisStateIconKey, ThesisStatus } from './types'

export function degreeToColor(degree: number): string {
  const d = Math.max(0, Math.min(180, degree))
  if (d < 36)  return '#2563EB'
  if (d < 72)  return '#60A5FA'
  if (d < 108) return '#D1D5DB'
  if (d < 144) return '#FB923C'
  return '#EF4444'
}

export function degreeToArrow(degree: number): string {
  const d = Math.max(0, Math.min(180, degree))
  if (d < 22.5)  return '\u2191'
  if (d < 67.5)  return '\u2197'
  if (d < 112.5) return '\u2192'
  if (d < 157.5) return '\u2198'
  return '\u2193'
}

export function degreeToLabel(degree: number): string {
  const d = Math.max(0, Math.min(180, degree))
  if (d < 36)  return '강하게 지지'
  if (d < 72)  return '지지하는 편'
  if (d < 108) return '중립'
  if (d < 144) return '약화하는 편'
  return '강하게 반박'
}

export function scoreToPhaseMeta(score: number): {
  phase: string; label: string
} {
  if (score > 0.6)  return { phase: 'full_moon', label: '가설이 빛나고 있어요' }
  if (score > 0.2)  return { phase: 'waxing',    label: '조금씩 밝아지고 있어요' }
  if (score > -0.2) return { phase: 'half_moon', label: '반반이에요' }
  if (score > -0.6) return { phase: 'waning',    label: '조금씩 어두워지고 있어요' }
  return { phase: 'new_moon', label: '가설이 힘을 잃고 있어요' }
}

// ── 상태 표시 정보 (R2: 색상 분리, M6: icon 타입 안전) ──
interface StateDisplayInfo {
  label: string
  colorClass: string
  icon: ThesisStateIconKey
}

export function stateToDisplay(state: ThesisState): StateDisplayInfo {
  const map: Record<ThesisState, StateDisplayInfo> = {
    warming_up:       { label: '데이터 수집 중', colorClass: 'text-gray-400 bg-gray-800 border-gray-700',       icon: 'loader' },
    active:           { label: '추적 중',        colorClass: 'text-blue-400 bg-blue-900/30 border-blue-800',     icon: 'eye' },
    strengthening:    { label: '지지 신호 증가', colorClass: 'text-green-400 bg-green-900/30 border-green-800',  icon: 'trending_up' },
    weakening:        { label: '반박 신호 증가', colorClass: 'text-orange-400 bg-orange-900/30 border-orange-800', icon: 'trending_down' },
    critical:         { label: '주의 필요',      colorClass: 'text-red-400 bg-red-900/30 border-red-800',        icon: 'alert_triangle' },
    needs_review:     { label: '점검 필요',      colorClass: 'text-yellow-400 bg-yellow-900/30 border-yellow-800', icon: 'clock' },
    expired:          { label: '기간 만료',      colorClass: 'text-amber-400 bg-amber-900/30 border-amber-800',  icon: 'timer' },
    closed_correct:   { label: '적중',           colorClass: 'text-green-400 bg-green-900/30 border-green-800',  icon: 'check_circle' },
    closed_incorrect: { label: '빗나감',         colorClass: 'text-red-400 bg-red-900/30 border-red-800',        icon: 'x_circle' },
    closed_neutral:   { label: '미확정',         colorClass: 'text-gray-500 bg-gray-800/50 border-gray-700',     icon: 'minus_circle' },
  }
  return map[state] ?? map.active
}

export function daysWatching(createdAt: string): number {
  return Math.max(0, differenceInDays(new Date(), new Date(createdAt)))
}

// ── 상대 시간 포맷 (M7) ──
// 사용처: TodayChangeCard, 알림 목록(FE-PR-6), 대시보드(FE-PR-5)
export function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  // 미래 시간 방어 (P3): 서버 시계 차이/timezone 변환 문제로 음수 diff 가능
  if (diff < 0) return '방금 전'
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '방금 전'
  if (minutes < 60) return `${minutes}분 전`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}일 전`
  return new Date(dateStr).toLocaleDateString('ko-KR', {
    month: 'short',
    day: 'numeric',
  })
}

// ── 가설 상태 우선순위 (낮을수록 먼저 표시) (M8) ──
// critical(즉시 대응) > needs_review(주의) > weakening(반박 증가) > strengthening(확인) > active/warming_up(안정)
const STATE_PRIORITY: Record<ThesisState, number> = {
  critical:         0,
  needs_review:     1,
  weakening:        2,
  strengthening:    3,
  active:           4,
  warming_up:       5,
  expired:          6,
  closed_correct:   7,
  closed_incorrect: 7,
  closed_neutral:   7,
}

export function sortThesesByPriority<
  T extends { current_state: ThesisState; created_at: string },
>(theses: T[]): T[] {
  return [...theses].sort(
    (a, b) =>
      (STATE_PRIORITY[a.current_state] ?? 99) -
        (STATE_PRIORITY[b.current_state] ?? 99) ||
      // 2차 정렬 (P4): 동순위 시 최신 생성순 — 목록 순서 안정성 보장
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
}

// ── PR-5: score → ThesisBadge 상태 유추 ──
// 기술 부채: 백엔드에 current_state 필드 추가 시 이 함수만 교체
export function scoreToBadgeState(
  score: number,
  status: ThesisStatus,
): ThesisState {
  if (status !== 'active') return 'active'
  if (score > 0.2) return 'strengthening'
  if (score < -0.2) return 'weakening'
  return 'active'
}

// ── PR-5: hex color 검증 ──
const HEX_COLOR_RE = /^#[0-9A-Fa-f]{6}$/

export function sanitizeHexColor(color: string, fallback = '#9CA3AF'): string {
  return HEX_COLOR_RE.test(color) ? color : fallback
}

// ── PR-6: 알림 severity 스타일 ──
export function severityToStyle(severity: string): {
  label: string
  className: string
} {
  switch (severity) {
    case 'critical':
      return { label: '긴급', className: 'text-red-400 bg-red-900/30' }
    case 'warning':
      return { label: '주의', className: 'text-yellow-400 bg-yellow-900/30' }
    default:
      return { label: '정보', className: 'text-blue-400 bg-blue-900/30' }
  }
}
