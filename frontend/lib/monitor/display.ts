// Monitor 표시 유틸 (MON-P3-S1) — **렌더 전용**.
// ⚠️ 값의 진실 = API 응답(스냅샷 파생 `monitor.display`: degree·color·label·phase).
// 점수→각도·달위상 재계산은 BE 엔진(arrow_calculator·state_machine)이 단일 소스이므로
// 여기서 하지 않는다. 아래는 API가 주는 값(current_state·deadline)의 순수 UI 매핑만.
import type { MonitorState } from '@/types/monitor'

export interface StateMeta {
  label: string
  tone: 'danger' | 'warn' | 'watch' | 'stable'
}

// current_state(API 판정) → UI 톤. 위험→약화→관찰→유지.
const STATE_META: Record<MonitorState, StateMeta> = {
  critical: { label: '주의 필요', tone: 'danger' },
  expired: { label: '기간 만료', tone: 'danger' },
  needs_review: { label: '점검 필요', tone: 'danger' },
  weakening: { label: '약화 추세', tone: 'warn' },
  warming_up: { label: '데이터 수집 중', tone: 'watch' },
  active: { label: '활성 관제 중', tone: 'watch' },
  strengthening: { label: '강화 추세', tone: 'stable' },
  paused: { label: '일시정지', tone: 'stable' },
}

export function stateMeta(state: MonitorState): StateMeta {
  return STATE_META[state] ?? { label: state, tone: 'watch' }
}

// 마감일(API 필드) → "D-3" / "D-day" / "D+2". 날짜 포맷팅(판정 아님).
export function ddayLabel(deadline: string | null): string | null {
  if (!deadline) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(deadline + 'T00:00:00')
  const diff = Math.round((due.getTime() - today.getTime()) / 86400000)
  if (diff === 0) return 'D-day'
  return diff > 0 ? `D-${diff}` : `D+${-diff}`
}

// score(-1~1) → 달 채움 비율(0~100). 순수 기하 렌더(임계·판정 없음, 진행바 폭과 동급).
export function scoreToFillPercent(score: number): number {
  return Math.round(((Math.max(-1, Math.min(1, score)) + 1) / 2) * 100)
}
