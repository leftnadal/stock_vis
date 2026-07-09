// Monitor 시각화 유틸 (MON-P3-S1) — BE arrow_calculator/state_machine 미러.
// score(-1~1) → 각도/색/라벨/달위상. 서버 계산과 FE 표시를 한 소스로 정합.

// COLOR_BANDS (arrow_calculator.py와 동일)
const COLOR_BANDS: [number, number, string][] = [
  [0, 45, '#2563EB'], // 강한 지지
  [45, 75, '#60A5FA'], // 지지
  [75, 105, '#9CA3AF'], // 중립
  [105, 135, '#FB923C'], // 약화
  [135, 180, '#DC2626'], // 강한 반박
]

const LABEL_BANDS: [number, number, string][] = [
  [0, 30, '강하게 지지'],
  [30, 60, '지지하는 중'],
  [60, 80, '살짝 지지'],
  [80, 100, '중립'],
  [100, 120, '살짝 약화'],
  [120, 150, '약화 중'],
  [150, 180, '강하게 반박'],
]

export function scoreToDegree(score: number): number {
  return 90 - score * 90
}

export function degreeToColor(degree: number): string {
  for (const [low, high, color] of COLOR_BANDS) {
    if (degree >= low && degree < high) return color
  }
  return '#DC2626'
}

export function degreeToLabel(degree: number): string {
  for (const [low, high, label] of LABEL_BANDS) {
    if (degree >= low && degree < high) return label
  }
  return '강하게 반박'
}

export interface PhaseMeta {
  phase: 'full_moon' | 'waxing' | 'half_moon' | 'waning' | 'new_moon'
  label: string
  icon: string
}

// score_to_phase (state_machine.py와 동일)
export function scoreToPhaseMeta(score: number): PhaseMeta {
  if (score > 0.6) return { phase: 'full_moon', label: '가설이 빛나고 있어요', icon: '🌕' }
  if (score > 0.2) return { phase: 'waxing', label: '조금씩 밝아지고 있어요', icon: '🌔' }
  if (score > -0.2) return { phase: 'half_moon', label: '반반이에요', icon: '🌓' }
  if (score > -0.6) return { phase: 'waning', label: '조금씩 어두워지고 있어요', icon: '🌒' }
  return { phase: 'new_moon', label: '가설이 힘을 잃고 있어요', icon: '🌑' }
}

// 상태 심각도 표시 메타 (위험→약화→관찰→유지)
import type { MonitorState } from '@/types/monitor'

export interface StateMeta {
  label: string
  tone: 'danger' | 'warn' | 'watch' | 'stable'
}

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

// D-day 계산 (마감일 → "D-3" / "D-day" / "D+2")
export function ddayLabel(deadline: string | null): string | null {
  if (!deadline) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(deadline + 'T00:00:00')
  const diff = Math.round((due.getTime() - today.getTime()) / 86400000)
  if (diff === 0) return 'D-day'
  return diff > 0 ? `D-${diff}` : `D+${-diff}`
}
