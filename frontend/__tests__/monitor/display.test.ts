// Monitor 표시 유틸 검증 (MON-P3-S1) — BE 미러 정합
import { describe, expect, it } from 'vitest'

import {
  ddayLabel,
  degreeToColor,
  degreeToLabel,
  scoreToDegree,
  scoreToPhaseMeta,
  stateMeta,
} from '@/lib/monitor/display'

describe('scoreToDegree', () => {
  it('score→degree 매핑 (1→0, 0→90, -1→180)', () => {
    expect(scoreToDegree(1)).toBe(0)
    expect(scoreToDegree(0)).toBe(90)
    expect(scoreToDegree(-1)).toBe(180)
  })
})

describe('degreeToColor/Label', () => {
  it('밴드별 색·라벨', () => {
    expect(degreeToColor(10)).toBe('#2563EB')
    expect(degreeToColor(90)).toBe('#9CA3AF')
    expect(degreeToColor(180)).toBe('#DC2626')
    expect(degreeToLabel(10)).toBe('강하게 지지')
    expect(degreeToLabel(90)).toBe('중립')
  })
})

describe('scoreToPhaseMeta', () => {
  it('달 위상 구간', () => {
    expect(scoreToPhaseMeta(0.8).phase).toBe('full_moon')
    expect(scoreToPhaseMeta(0).phase).toBe('half_moon')
    expect(scoreToPhaseMeta(-0.8).phase).toBe('new_moon')
  })
})

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
