import { describe, it, expect } from 'vitest'

describe('Vitest 인프라 확인', () => {
  it('테스트 환경이 정상 동작한다', () => {
    expect(1 + 1).toBe(2)
  })

  it('jsdom 환경이 설정되어 있다', () => {
    expect(typeof document).toBe('object')
    expect(typeof window).toBe('object')
  })
})
