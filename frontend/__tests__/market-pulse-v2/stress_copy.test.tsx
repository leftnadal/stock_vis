/**
 * MPS-2 — 스트레스 카드 결정론 카피(LLM 0) 테스트.
 *
 * 커버리지:
 *   1. topPercent = 100 − value(from-below, D-MPS-COPY F2 변환)
 *   2. 수준 3종(severe에 "위기" 어휘 금지 = severe→"심화")
 *   3. 백분위 분기: caution/severe = "지난 3년 중 상위 N%" / stable = 중립("상위 64.9%" 어색문구 금지)
 *   4. 방향 9조합 + 괴리(uptrend∧worsening) 전용 강조 + 역괴리(downtrend∧easing)
 *   5. ★금지규칙 2 전수 스캔: 전 조합(3 band × 9 방향 × 백분위) 금지 어휘 부재
 *      (위기/crisis·유사/닮·과거 특정 연도) = 백엔드 test_band_vocab_excludes_crisis의 FE 짝
 */
import { describe, it, expect } from 'vitest'

import {
  topPercent,
  buildStressCopy,
  type LevelBand,
  type StressState,
  type PriceState,
} from '@/app/market-pulse-v2/stressCopy'

const BANDS: LevelBand[] = ['stable', 'caution', 'severe']
const STRESS: StressState[] = ['worsening', 'easing', 'mixed']
const PRICE: PriceState[] = ['uptrend', 'downtrend', 'mixed']

// 금지 패턴: 위기/crisis(대소문자), 유사성 어휘, 과거 특정 연도(4자리)
const FORBIDDEN = [/위기/, /crisis/i, /유사/, /닮/, /(19|20)\d{2}/]

describe('topPercent (F2 변환)', () => {
  it('상위 N% = 100 − value(from-below)', () => {
    expect(topPercent(92)).toBe(8)
    expect(topPercent(35.1)).toBe(64.9)
    expect(topPercent(100)).toBe(0)
  })
})

describe('수준 서술(level)', () => {
  it('severe는 "심화"이며 "위기" 어휘 금지', () => {
    const c = buildStressCopy({ levelBand: 'severe', percentileValue: 92, stressState: 'mixed', priceState: 'mixed' })
    expect(c.level).toContain('심화')
    expect(c.level).not.toMatch(/위기|crisis/i)
  })
  it('stable/caution 각 문구', () => {
    expect(buildStressCopy({ levelBand: 'stable', percentileValue: 30, stressState: 'mixed', priceState: 'mixed' }).level).toContain('낮')
    expect(buildStressCopy({ levelBand: 'caution', percentileValue: 60, stressState: 'mixed', priceState: 'mixed' }).level).toContain('주의')
  })
})

describe('백분위 분기(F2)', () => {
  it('severe/caution = "지난 3년 중 상위 N%"', () => {
    const sev = buildStressCopy({ levelBand: 'severe', percentileValue: 94, stressState: 'worsening', priceState: 'uptrend' })
    expect(sev.percentile).toContain('상위 6%')
    expect(sev.percentile).toContain('지난 3년')
  })
  it('stable = 중립 서술, "상위 64.9%" 어색문구 미생성 + "지난 3년 대비" 시계열 기준 명시', () => {
    const st = buildStressCopy({ levelBand: 'stable', percentileValue: 35.1, stressState: 'mixed', priceState: 'mixed' })
    expect(st.percentile).not.toContain('상위')
    expect(st.percentile).toContain('지난 3년') // stable도 caution/severe와 동일 3년 시계열 기준 명시(D-MPS-COPY)
  })
})

describe('방향 9조합 + 괴리', () => {
  it('괴리(가격 상승 ∧ 스트레스 악화) = 전용 강조 + flag', () => {
    const c = buildStressCopy({ levelBand: 'severe', percentileValue: 92, stressState: 'worsening', priceState: 'uptrend' })
    expect(c.divergence).toBe(true)
    expect(c.direction).toContain('괴리')
  })
  it('역괴리(가격 하락 ∧ 스트레스 완화) = 구분 서술 + flag', () => {
    const c = buildStressCopy({ levelBand: 'stable', percentileValue: 20, stressState: 'easing', priceState: 'downtrend' })
    expect(c.reverseDivergence).toBe(true)
    expect(c.direction).toContain('역괴리')
  })
  it('일반 조합은 괴리 flag off', () => {
    const c = buildStressCopy({ levelBand: 'caution', percentileValue: 55, stressState: 'mixed', priceState: 'mixed' })
    expect(c.divergence).toBe(false)
    expect(c.reverseDivergence).toBe(false)
  })
  it('9조합 direction 문구가 stress·price 양쪽을 언급', () => {
    for (const s of STRESS) {
      for (const p of PRICE) {
        const c = buildStressCopy({ levelBand: 'caution', percentileValue: 60, stressState: s, priceState: p })
        expect(c.direction).toMatch(/스트레스/)
        expect(c.direction).toMatch(/가격/)
      }
    }
  })
})

describe('★금지규칙 2 전수 스캔(FE 짝)', () => {
  it('전 조합(3×3×3 × 백분위 2종)에서 금지 어휘 부재', () => {
    const pcts = [15, 94] // stable-ish 낮음 / severe-ish 높음
    for (const b of BANDS) {
      for (const s of STRESS) {
        for (const p of PRICE) {
          for (const v of pcts) {
            const c = buildStressCopy({ levelBand: b, percentileValue: v, stressState: s, priceState: p })
            const all = `${c.level} | ${c.percentile} | ${c.direction}`
            for (const re of FORBIDDEN) {
              expect(all, `조합 ${b}/${s}/${p}/${v}: "${all}"`).not.toMatch(re)
            }
          }
        }
      }
    }
  })
})
