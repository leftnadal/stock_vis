// 가이드 데이터 계약 — 에이전트 루브릭 단일 출처의 무결성 (D-GUIDE-TRACK)
import { statSync } from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { GUIDE_SCREENS, getGuideById, getGuideForRoute } from '@/lib/guide'

const APP_DIR = path.resolve(__dirname, '../../app')

/** 라우트에 실제 page 파일이 있는가. 가이드 등재 여부와 무관한 "실물" 판정. */
function routeExists(route: string): boolean {
  const dir = path.join(APP_DIR, ...route.split('/').filter(Boolean))
  return ['page.tsx', 'page.ts'].some((f) => {
    try {
      return statSync(path.join(dir, f)).isFile()
    } catch {
      return false
    }
  })
}

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

  // 상한 7 = S1C 승인 문구(marketPulse v2 7영역) 기준. S1의 5는 임의 상한이었음.
  it('learnings 2~4개 · regions 3~7개', () => {
    for (const s of GUIDE_SCREENS) {
      expect(s.learnings.length, `${s.id} learnings`).toBeGreaterThanOrEqual(2)
      expect(s.learnings.length, `${s.id} learnings`).toBeLessThanOrEqual(4)
      expect(s.regions.length, `${s.id} regions`).toBeGreaterThanOrEqual(3)
      expect(s.regions.length, `${s.id} regions`).toBeLessThanOrEqual(7)
    }
  })

  it('region anchor는 화면 안에서 고유하다', () => {
    for (const s of GUIDE_SCREENS) {
      const anchors = s.regions.map((r) => r.anchor)
      expect(new Set(anchors).size, s.id).toBe(anchors.length)
    }
  })

  // 판정 근거 = app/ 의 page 파일(실물). 가이드 등재 라우트 집합으로 근사하면,
  // 가이드가 없는 실재 화면을 가리킬 때 거짓 실패한다 — /chainsight 임시 이설
  // (GUIDE-CS-GUARD-1)에서 실증됐다. 이 파일 전체가 "선언 ↔ 실물" 계약이므로 실물을 본다.
  it('nextAction.route는 실재 라우트를 가리킨다', () => {
    for (const s of GUIDE_SCREENS) {
      if (s.nextAction) {
        expect(routeExists(s.nextAction.route), `${s.id} → ${s.nextAction.route}`).toBe(true)
      }
    }
  })

  it('화면 자신의 route도 실재한다', () => {
    for (const s of GUIDE_SCREENS) {
      expect(routeExists(s.route), `${s.id} → ${s.route}`).toBe(true)
    }
  })

  it('검수 대기 draft는 allowlist에 한함 (미추적 draft 잔류 금지)', () => {
    // 병진 검수 대기 중인 신규 가이드만 draft 허용(검수 후 confirmed 전환·별건).
    // stray draft(추적 안 된 미검수)는 여전히 실패시켜 게이트 유지.
    // MP2-SUBPAGES S1(2026-08-31): marketPulse.macro = 허브 가이드, 병진 검수 대기.
    const PENDING_REVIEW = new Set<string>(['marketPulse.macro'])
    const drafts = GUIDE_SCREENS.filter((s) => s.reviewStatus !== 'confirmed').map((s) => s.id)
    const untracked = drafts.filter((id) => !PENDING_REVIEW.has(id))
    expect(untracked, `미추적 draft 잔류: ${untracked.join(', ')}`).toEqual([])
  })

  it('S1C: Market Pulse 가이드는 v2 라우트에만 존재한다 (v1 은퇴 신호)', () => {
    const routes = GUIDE_SCREENS.map((s) => s.route)
    expect(routes).toContain('/market-pulse-v2')
    expect(routes).not.toContain('/market-pulse')
  })

  it('조회 헬퍼는 정확 일치만 인정한다', () => {
    expect(getGuideForRoute('/monitor')?.id).toBe('monitor.main')
    expect(getGuideForRoute('/monitor/new')).toBeUndefined()
    expect(getGuideById('portfolio.main')?.route).toBe('/portfolio')
  })
})
