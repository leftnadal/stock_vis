// 숫자 표시 규약 '가' 단일 포맷 유틸 검증 (PART B-FE, univ-p15-v01).
// 퍼센트/가격/점수·z·Δ/방향기호/대용량/지표원값 6개 타입 규약을 강제한다.
import { describe, expect, it } from 'vitest'

import {
  dirArrow,
  formatIndicator,
  formatPctRule,
  formatPrice,
  formatScore,
} from '@/utils/formatters'

describe('formatPctRule — 퍼센트 소수 2자리, 0 반올림 시 부호 제거', () => {
  it('일반 값은 소수 2자리로 반올림한다', () => {
    expect(formatPctRule(18.1818)).toBe('18.18%')
    expect(formatPctRule(-5)).toBe('-5.00%')
  })

  it('반올림 결과가 0이면 부호를 제거하고 0.00%로 고정한다', () => {
    expect(formatPctRule(-0.0023)).toBe('0.00%')
    expect(formatPctRule(0.001)).toBe('0.00%')
    expect(formatPctRule(-0.001)).toBe('0.00%')
  })

  it('signed=true면 양수에 +를 붙인다(0은 예외)', () => {
    expect(formatPctRule(10, { signed: true })).toBe('+10.00%')
    expect(formatPctRule(-10, { signed: true })).toBe('-10.00%')
    expect(formatPctRule(0, { signed: true })).toBe('0.00%')
  })

  it('signed 미지정이면 양수에 +를 붙이지 않는다', () => {
    expect(formatPctRule(18.1818)).not.toContain('+')
  })

  it('NaN/null/undefined는 안전 폴백을 반환한다', () => {
    expect(formatPctRule(null)).toBe('—')
    expect(formatPctRule(undefined)).toBe('—')
    expect(formatPctRule(NaN)).toBe('—')
  })
})

describe('formatPrice — 소수 2자리 + 통화기호 + 천단위', () => {
  it('USD 기본 통화로 포맷한다', () => {
    expect(formatPrice(1160.0618)).toBe('$1,160.06')
  })

  it('통화코드를 명시하면 해당 통화기호를 쓴다', () => {
    expect(formatPrice(1000, 'USD')).toBe('$1,000.00')
  })

  it('compact=true면 축약 1자리(K/M/B) + 통화기호를 쓴다', () => {
    expect(formatPrice(1635998208.75, 'USD', { compact: true })).toBe('$1.6B')
  })

  it('문자열 숫자(Decimal 직렬화)도 파싱해 포맷한다', () => {
    expect(formatPrice('926.73')).toBe('$926.73')
  })

  it('NaN/null/undefined는 안전 폴백을 반환한다', () => {
    expect(formatPrice(null)).toBe('—')
    expect(formatPrice(undefined)).toBe('—')
    expect(formatPrice('not-a-number')).toBe('—')
  })
})

describe('formatScore — 점수·z·Δ 소수 3자리 고정', () => {
  it('소수 3자리로 고정 표시한다', () => {
    expect(formatScore(-0.0249)).toBe('-0.025')
    expect(formatScore(0.42)).toBe('0.420')
  })

  it('signed=true면 양수에 +를 붙인다', () => {
    expect(formatScore(0.03, { signed: true })).toBe('+0.030')
    expect(formatScore(-0.025, { signed: true })).toBe('-0.025')
    expect(formatScore(0, { signed: true })).toBe('0.000')
  })

  it('digits override로 자릿수를 바꿀 수 있다', () => {
    expect(formatScore(0.123456, { digits: 2 })).toBe('0.12')
  })

  it('-0 아티팩트를 0으로 정규화한다', () => {
    expect(formatScore(-0.0001)).toBe('0.000')
  })

  it('NaN/null/undefined는 안전 폴백을 반환한다', () => {
    expect(formatScore(null)).toBe('—')
    expect(formatScore(undefined)).toBe('—')
  })
})

describe('dirArrow — 방향기호, 반올림 후 0이면 생략', () => {
  it('양수는 ▲, 음수는 ▼', () => {
    expect(dirArrow(0.03)).toBe('▲')
    expect(dirArrow(-0.03)).toBe('▼')
  })

  it('표시 정밀도로 반올림한 결과가 0이면 기호를 생략한다(▲0.00 자기모순 방지)', () => {
    expect(dirArrow(0.001, 2)).toBe('')
    expect(dirArrow(-0.001, 2)).toBe('')
    expect(dirArrow(0, 2)).toBe('')
  })

  it('displayDigits가 다르면 반올림 기준도 달라진다', () => {
    expect(dirArrow(0.0006, 3)).toBe('▲') // 3자리에선 0.001로 반올림 → 0 아님
    expect(dirArrow(0.0006, 2)).toBe('') // 2자리에선 0.00 → 생략
  })

  it('NaN/null/undefined는 빈 문자열을 반환한다', () => {
    expect(dirArrow(null)).toBe('')
    expect(dirArrow(undefined)).toBe('')
  })
})

describe('formatIndicator — 지표 원값 기본 소수 2자리', () => {
  it('기본 2자리로 반올림한다', () => {
    expect(formatIndicator(41.0)).toBe('41.00')
    expect(formatIndicator(41.4567)).toBe('41.46')
  })

  it('digits override 가능하다', () => {
    expect(formatIndicator(41.4567, 3)).toBe('41.457')
  })

  it('NaN/null/undefined는 안전 폴백을 반환한다', () => {
    expect(formatIndicator(null)).toBe('—')
    expect(formatIndicator(undefined)).toBe('—')
  })
})
