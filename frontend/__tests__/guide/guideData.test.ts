// 가이드 데이터 계약 — 에이전트 루브릭 단일 출처의 무결성 (D-GUIDE-TRACK)
import { describe, expect, it } from 'vitest'

import { GUIDE_SCREENS, getGuideById, getGuideForRoute } from '@/lib/guide'

describe('GUIDE_SCREENS 계약', () => {
  it('id·route가 중복되지 않는다', () => {
    expect(new Set(GUIDE_SCREENS.map((s) => s.id)).size).toBe(GUIDE_SCREENS.length)
    expect(new Set(GUIDE_SCREENS.map((s) => s.route)).size).toBe(GUIDE_SCREENS.length)
  })

  it('모든 화면이 coreQuestion(물음표로 끝나는 질문)을 갖는다 — 루브릭 기준 문장', () => {
    for (const s of GUIDE_SCREENS) {
      expect(s.coreQuestion.trim().endsWith('?'), s.id).toBe(true)
    }
  })

  it('learnings 2~4개 · regions 3~5개', () => {
    for (const s of GUIDE_SCREENS) {
      expect(s.learnings.length, `${s.id} learnings`).toBeGreaterThanOrEqual(2)
      expect(s.learnings.length, `${s.id} learnings`).toBeLessThanOrEqual(4)
      expect(s.regions.length, `${s.id} regions`).toBeGreaterThanOrEqual(3)
      expect(s.regions.length, `${s.id} regions`).toBeLessThanOrEqual(5)
    }
  })

  it('region anchor는 화면 안에서 고유하다', () => {
    for (const s of GUIDE_SCREENS) {
      const anchors = s.regions.map((r) => r.anchor)
      expect(new Set(anchors).size, s.id).toBe(anchors.length)
    }
  })

  it('nextAction.route는 실재 라우트를 가리킨다', () => {
    const known = new Set([...GUIDE_SCREENS.map((s) => s.route), '/guide'])
    for (const s of GUIDE_SCREENS) {
      if (s.nextAction) expect(known.has(s.nextAction.route), `${s.id} → ${s.nextAction.route}`).toBe(true)
    }
  })

  it('조회 헬퍼는 정확 일치만 인정한다', () => {
    expect(getGuideForRoute('/monitor')?.id).toBe('monitor.main')
    expect(getGuideForRoute('/monitor/new')).toBeUndefined()
    expect(getGuideById('portfolio.main')?.route).toBe('/portfolio')
  })
})
