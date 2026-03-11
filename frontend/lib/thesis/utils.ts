import { differenceInDays } from 'date-fns'
import type { ThesisState } from './types'

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

export function stateToDisplay(state: ThesisState): {
  label: string; colorClass: string
} {
  switch (state) {
    case 'warming_up':       return { label: '데이터 수집 중', colorClass: 'text-gray-400 bg-gray-800' }
    case 'active':           return { label: '관제 중',       colorClass: 'text-blue-400 bg-blue-900/50' }
    case 'strengthening':    return { label: '강화 추세',     colorClass: 'text-green-400 bg-green-900/50' }
    case 'weakening':        return { label: '약화 추세',     colorClass: 'text-orange-400 bg-orange-900/50' }
    case 'critical':         return { label: '주의 필요',     colorClass: 'text-red-400 bg-red-900/50' }
    case 'needs_review':     return { label: '점검 필요',     colorClass: 'text-yellow-400 bg-yellow-900/50' }
    case 'expired':          return { label: '기간 만료',     colorClass: 'text-gray-500 bg-gray-800' }
    case 'closed_correct':   return { label: '적중',          colorClass: 'text-green-400 bg-green-900/50' }
    case 'closed_incorrect': return { label: '미적중',        colorClass: 'text-red-400 bg-red-900/50' }
    case 'closed_neutral':   return { label: '중립 마감',     colorClass: 'text-gray-400 bg-gray-800' }
    default:                 return { label: '알 수 없음',    colorClass: 'text-gray-500 bg-gray-800' }
  }
}

export function daysWatching(createdAt: string): number {
  return Math.max(0, differenceInDays(new Date(), new Date(createdAt)))
}
