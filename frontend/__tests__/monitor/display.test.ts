// Monitor 표시 유틸 검증 (MON-P3-S1) — 렌더 전용 매핑만 (재계산 제거됨)
import { describe, expect, it } from 'vitest'

import { ddayLabel, scoreToFillPercent, stateMeta } from '@/lib/monitor/display'

describe('stateMeta', () => {
  it('상태→톤 (위험/약화/관찰/유지)', () => {
    expect(stateMeta('critical').tone).toBe('danger')
    expect(stateMeta('weakening').tone).toBe('warn')
    expect(stateMeta('active').tone).toBe('watch')
    expect(stateMeta('strengthening').tone).toBe('stable')
  })
})

describe('ddayLabel', () => {
  it('null이면 null', () => {
    expect(ddayLabel(null)).toBeNull()
  })
  it('오늘이면 D-day', () => {
    const today = new Date()
    const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    expect(ddayLabel(iso)).toBe('D-day')
  })
})

describe('scoreToFillPercent', () => {
  it('score→달 채움 비율 (순수 기하, -1→0, 0→50, 1→100)', () => {
    expect(scoreToFillPercent(-1)).toBe(0)
    expect(scoreToFillPercent(0)).toBe(50)
    expect(scoreToFillPercent(1)).toBe(100)
  })
})
