/**
 * MP-A3-TAIL rev2 — 커스텀 leader-line 외부 라벨 배치 로직 단위 테스트.
 *
 * 검증:
 *   1. polarToCart: 기본 좌표 변환 정확성
 *   2. computeLabelLayout: 좌/우 분기, %포맷, 임계값 필터, 좌표 계산
 *   3. computeAllLabelLayouts: 양방향 nudge(아래 방향), 상단 클리핑 방지, 다중 인스턴스 독립성
 */
import { describe, expect, it } from 'vitest'
import {
  polarToCart,
  computeLabelLayout,
  computeAllLabelLayouts,
} from '@/app/market-pulse-v2/details/ConcentrationDetail'

const CX = 200
const CY = 160
const OUTER_R = 90
const SVG_H = 320

// ── polarToCart ─────────────────────────────────────────────────────────────
describe('polarToCart', () => {
  it('0도(3시 방향) → cx+r, cy', () => {
    const p = polarToCart(CX, CY, OUTER_R, 0)
    expect(p.x).toBeCloseTo(CX + OUTER_R, 1)
    expect(p.y).toBeCloseTo(CY, 1)
  })

  it('90도(12시 방향, recharts CCW) → cx, cy-r', () => {
    const p = polarToCart(CX, CY, OUTER_R, 90)
    expect(p.x).toBeCloseTo(CX, 1)
    expect(p.y).toBeCloseTo(CY - OUTER_R, 1)
  })

  it('180도(9시 방향) → cx-r, cy', () => {
    const p = polarToCart(CX, CY, OUTER_R, 180)
    expect(p.x).toBeCloseTo(CX - OUTER_R, 1)
    expect(p.y).toBeCloseTo(CY, 1)
  })

  it('270도(6시 방향) → cx, cy+r', () => {
    const p = polarToCart(CX, CY, OUTER_R, 270)
    expect(p.x).toBeCloseTo(CX, 1)
    expect(p.y).toBeCloseTo(CY + OUTER_R, 1)
  })
})

// ── computeLabelLayout ──────────────────────────────────────────────────────
describe('computeLabelLayout', () => {
  it('우측(0도) → isRight=true, textAnchor=start', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 0, 0.054)
    expect(layout).not.toBeNull()
    expect(layout!.isRight).toBe(true)
    expect(layout!.textAnchor).toBe('start')
  })

  it('좌측(180도) → isRight=false, textAnchor=end', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 180, 0.054)
    expect(layout).not.toBeNull()
    expect(layout!.isRight).toBe(false)
    expect(layout!.textAnchor).toBe('end')
  })

  it('정확히 90도(12시, cos=0) → isRight=true(cos≥0 경계)', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 90, 0.05)
    expect(layout!.isRight).toBe(true)
  })

  it('정확히 91도(좌측) → isRight=false', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 91, 0.05)
    expect(layout!.isRight).toBe(false)
  })

  it('%포맷: 0.054 → "5.4%"', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 45, 0.054)
    expect(layout!.label).toBe('5.4%')
  })

  it('%포맷: 0.033 → "3.3%"', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 120, 0.033)
    expect(layout!.label).toBe('3.3%')
  })

  it('%포맷: 0.615 (others) → "61.5%"', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 300, 0.615)
    expect(layout!.label).toBe('61.5%')
  })

  it('threshold 미달(value < threshold) → null 반환', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 45, 0.02, 0.03)
    expect(layout).toBeNull()
  })

  it('threshold 0(기본) → 아주 작은 조각도 라벨 반환', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 45, 0.001, 0)
    expect(layout).not.toBeNull()
    expect(layout!.label).toBe('0.1%')
  })

  it('우측 라벨 px1.x가 cx+outerRadius보다 큼(외곽 배치)', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 0, 0.05)
    expect(layout!.px1.x).toBeGreaterThan(CX + OUTER_R)
  })

  it('좌측 라벨 px1.x가 cx-outerRadius보다 작음(외곽 배치)', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 180, 0.05)
    expect(layout!.px1.x).toBeLessThan(CX - OUTER_R)
  })

  it('우측 tx가 px2.x보다 큼(수평 연장)', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 30, 0.05)
    expect(layout!.tx).toBeGreaterThan(layout!.px2.x)
  })

  it('좌측 tx가 px2.x보다 작음(수평 연장)', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 150, 0.05)
    expect(layout!.tx).toBeLessThan(layout!.px2.x)
  })

  it('꺾임점(px2)이 기준점(px1)보다 outerRadius에서 더 멀리 위치', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 45, 0.05)
    const dist1 = Math.hypot(layout!.px1.x - CX, layout!.px1.y - CY)
    const dist2 = Math.hypot(layout!.px2.x - CX, layout!.px2.y - CY)
    expect(dist2).toBeGreaterThan(dist1)
  })

  it('ty가 py2.y와 동일(nudge 이전)', () => {
    const layout = computeLabelLayout(CX, CY, OUTER_R, 45, 0.05)
    expect(layout!.ty).toBeCloseTo(layout!.px2.y, 5)
  })
})

// ── computeAllLabelLayouts ──────────────────────────────────────────────────
describe('computeAllLabelLayouts', () => {
  // S&P 500 상위 10 근사 데이터 (좌상단 밀집 재현)
  const SP500_DATA = [
    { name: 'AAPL',  value: 0.071 },
    { name: 'MSFT',  value: 0.068 },
    { name: 'NVDA',  value: 0.053 },
    { name: 'AMZN',  value: 0.045 },
    { name: 'META',  value: 0.033 },
    { name: 'GOOGL', value: 0.027 },
    { name: 'GOOG',  value: 0.025 },
    { name: 'BRK.B', value: 0.022 },
    { name: 'LLY',   value: 0.021 },
    { name: 'AVGO',  value: 0.020 },
    { name: 'others', value: 0.615 },
  ]

  // recharts 기본 startAngle=0 기준 midAngle 직접 계산
  function computeMidAngles(data: { value: number }[]): number[] {
    const total = data.reduce((s, d) => s + d.value, 0)
    const angles: number[] = []
    let acc = 0
    for (const item of data) {
      const sweep = (item.value / total) * 360
      angles.push(acc + sweep / 2)
      acc += sweep
    }
    return angles
  }

  const midAngles = computeMidAngles(SP500_DATA)

  it('모든 인덱스에 대해 y값 반환 (11개)', () => {
    const map = computeAllLabelLayouts(SP500_DATA, CX, CY, OUTER_R, midAngles, SVG_H)
    expect(map.size).toBe(11)
  })

  it('모든 y값이 Y_MIN ~ Y_MAX(경계) 안에 있음 — 클리핑 방지', () => {
    const Y_MIN = 10
    const Y_MAX = SVG_H - Y_MIN
    const map = computeAllLabelLayouts(SP500_DATA, CX, CY, OUTER_R, midAngles, SVG_H, Y_MIN)
    for (const y of map.values()) {
      expect(y).toBeGreaterThanOrEqual(Y_MIN)
      expect(y).toBeLessThanOrEqual(Y_MAX)
    }
  })

  it('같은 사이드 라벨 간 y 간격이 MIN_GAP(14) 이상', () => {
    const map = computeAllLabelLayouts(SP500_DATA, CX, CY, OUTER_R, midAngles, SVG_H)

    const leftYs: number[] = []
    const rightYs: number[] = []

    SP500_DATA.forEach((_, idx) => {
      const midAngle = midAngles[idx]
      const RAD_MID = midAngle * (Math.PI / 180)
      const isRight = Math.cos(RAD_MID) >= 0
      const y = map.get(idx)
      if (y !== undefined) {
        if (isRight) rightYs.push(y)
        else leftYs.push(y)
      }
    })

    function checkGap(ys: number[]) {
      const sorted = [...ys].sort((a, b) => a - b)
      for (let i = 1; i < sorted.length; i++) {
        const gap = sorted[i] - sorted[i - 1]
        expect(gap).toBeGreaterThanOrEqual(13.9) // 부동소수 허용
      }
    }

    checkGap(leftYs)
    checkGap(rightYs)
  })

  it('다중 인스턴스 독립성: 두 번 호출해도 동일한 결과 반환', () => {
    const map1 = computeAllLabelLayouts(SP500_DATA, CX, CY, OUTER_R, midAngles, SVG_H)
    const map2 = computeAllLabelLayouts(SP500_DATA, CX, CY, OUTER_R, midAngles, SVG_H)
    for (const [idx, y] of map1.entries()) {
      expect(map2.get(idx)).toBeCloseTo(y, 5)
    }
  })

  it('cx/cy가 다르면 다른 맵 반환 (독립 계산)', () => {
    const map1 = computeAllLabelLayouts(SP500_DATA, 200, 160, OUTER_R, midAngles, SVG_H)
    const map2 = computeAllLabelLayouts(SP500_DATA, 250, 200, OUTER_R, midAngles, SVG_H)
    let hasDiff = false
    for (const [idx, y] of map1.entries()) {
      if (Math.abs((map2.get(idx) ?? 0) - y) > 0.01) {
        hasDiff = true
        break
      }
    }
    expect(hasDiff).toBe(true)
  })

  it('빈 데이터 → 빈 맵', () => {
    const map = computeAllLabelLayouts([], CX, CY, OUTER_R, [], SVG_H)
    expect(map.size).toBe(0)
  })

  it('midAngles 배열이 빈 경우 에러 없이 빈 맵 반환', () => {
    expect(() => {
      computeAllLabelLayouts(SP500_DATA, CX, CY, OUTER_R, [], SVG_H)
    }).not.toThrow()
    const map = computeAllLabelLayouts(SP500_DATA, CX, CY, OUTER_R, [], SVG_H)
    expect(map.size).toBe(0)
  })

  it('상단(90도 근처) 조각 y가 Y_MIN 이상 보장 — 클리핑 가드', () => {
    // 12시 방향 midAngle ≈ 90도 → ty가 최상단(최소값)
    const topData = [{ name: 'A', value: 0.5 }, { name: 'B', value: 0.5 }]
    const topMidAngles = [45, 225]
    const map = computeAllLabelLayouts(topData, CX, CY, OUTER_R, topMidAngles, SVG_H, 10)
    for (const y of map.values()) {
      expect(y).toBeGreaterThanOrEqual(10)
    }
  })

  it('nudge가 아래 방향으로 작동함 — 첫 항목 기준 이후 항목이 아래에 위치', () => {
    // 같은 사이드에 인접한 두 조각: y 간격이 MIN_GAP 미만일 때 두 번째가 아래로 밀림
    const closeData = [
      { name: 'A', value: 0.1 },
      { name: 'B', value: 0.09 },  // A 바로 옆(인접 각도)
    ]
    // 두 조각 모두 우측(0~90도 범위)에 인접
    const closeMidAngles = [10, 20]
    const map = computeAllLabelLayouts(closeData, CX, CY, OUTER_R, closeMidAngles, SVG_H)
    const ys = Array.from(map.values()).sort((a, b) => a - b)
    if (ys.length >= 2) {
      expect(ys[1] - ys[0]).toBeGreaterThanOrEqual(13.9)
    }
  })
})
