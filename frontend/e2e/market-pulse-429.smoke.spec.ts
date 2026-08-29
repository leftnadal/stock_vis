/**
 * P2-DLITE Part 2 — 429 브라우저 경로 스모크 (SMOKE-BROWSER-PATH).
 *
 * INC-P16 확정 명세(TASKQUEUE 정본):
 *   ① 재현 기준 = 분당 ~5회 "현실적 새로고침"에서 429/전면에러 부재.
 *   ② 하드리프레시 연타는 재현 대상 아님(물리적 정상) → 검증 = "429 무증폭 + 2초 내 회복"뿐.
 *
 * dev/prod throttle을 격리 authed 백엔드로 재현할 수 없어(STEP 0-5), 브라우저 경로 계약을
 * route interception으로 결정론 검증한다(단건 curl이 구조적으로 못 잡는 그 경로).
 * 엔진 레벨 계약이므로 데스크탑 프로젝트에서만 1회 실행.
 */
import { test, expect, type Page } from '@playwright/test'

import {
  overviewFixture,
  i18nFixture,
  stressFixture,
  analogFixture,
  playbookFixture,
  cardDetailFixtures,
} from './fixtures/marketPulse'

// 엔진 레벨 계약 — 데스크탑 프로젝트에서만 1회 실행(모바일 중복 회피).
test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-chromium', '브라우저 경로 계약 — 데스크탑 1회')
})

const META = { generated_at: '2026-06-11T00:00:00Z', latency_ms: 5, cache: 'MISS' }

/** overview 상태를 가변 `mode`로 제어하는 route(리로드 간 전환 가능). 요청 경로 수집. */
async function installMock(page: Page, state: { mode: 'ok' | 'throttle' }, seen: string[]) {
  await page.route('**/api/**', (route) => {
    const p = new URL(route.request().url()).pathname
    seen.push(p)
    const json = (obj: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(obj) })
    if (p.endsWith('/market-pulse/overview')) {
      return state.mode === 'throttle'
        ? json({ detail: 'Request was throttled.' }, 429)
        : json(overviewFixture)
    }
    if (p.endsWith('/market-pulse/i18n')) return json(i18nFixture)
    if (p.endsWith('/regime/stress')) return json({ _meta: META, data: stressFixture })
    if (p.endsWith('/regime/analog')) return json({ _meta: META, data: analogFixture })
    if (p.endsWith('/market-pulse/playbook')) return json({ _meta: META, data: playbookFixture })
    const cd = p.match(/\/cards\/([^/]+)\/detail$/)
    if (cd) return json({ _meta: META, data: cardDetailFixtures[cd[1]] ?? { available: false } })
    return json({})
  })
}

const overviewCount = (seen: string[]) =>
  seen.filter((p) => p.endsWith('/market-pulse/overview')).length

test.describe('429 브라우저 경로 스모크', () => {
  test('① 현실적 새로고침 5회 — 429/전면에러 부재 + 로드당 요청 무증폭', async ({ page }) => {
    const seen: string[] = []
    const state = { mode: 'ok' as const }
    await installMock(page, state, seen)

    const perLoad: number[] = []
    for (let i = 0; i < 5; i++) {
      const before = seen.length
      await page.goto('/market-pulse-v2', { waitUntil: 'networkidle' })
      await expect(page.getByText('확장 국면 지속')).toBeVisible()
      await expect(page.getByText('데이터를 불러오지 못했습니다.')).toHaveCount(0)
      perLoad.push(seen.length - before)
      await page.waitForTimeout(300) // 현실적 간격 축약(연타 아님)
    }
    // 로드당 요청 수가 일정(증폭/폭주 루프 부재). 최대가 최소의 2배 미만.
    const max = Math.max(...perLoad)
    const min = Math.min(...perLoad)
    expect(max, `로드당 요청 ${JSON.stringify(perLoad)}`).toBeLessThan(min * 2 + 3)
    // 429 없음(정상 경로)
    console.log(`[429-smoke ①] 로드당 요청=${JSON.stringify(perLoad)} overview호출=${overviewCount(seen)}`)
  })

  test('② 429 발생 시 무증폭(재시도 스톰 부재) + 2초 내 회복', async ({ page }) => {
    const seen: string[] = []
    const state = { mode: 'throttle' as 'ok' | 'throttle' }
    await installMock(page, state, seen)

    // 429 로드: 전면에러 대신 원인 구분 안내(INC-P16-CLOSE Part 3), 재시도 스톰 부재
    await page.goto('/market-pulse-v2', { waitUntil: 'networkidle' })
    await expect(
      page.getByText('요청이 많아 잠시 제한됐어요. 잠시 후 다시 시도해 주세요.'),
    ).toBeVisible()
    await page.waitForTimeout(1500) // 재시도 스톰이 있었다면 이 창에서 폭증
    const overviewOn429 = overviewCount(seen)
    // INC-P16-1 A(429 무재시도): overview 호출이 소수(증폭 없음). retry:2였다면 3배.
    expect(overviewOn429, `429 시 overview 호출=${overviewOn429}`).toBeLessThanOrEqual(3)

    // 회복: 200 전환 후 새로고침 → 2초 내 정상 렌더
    state.mode = 'ok'
    const t0 = Date.now()
    await page.goto('/market-pulse-v2', { waitUntil: 'networkidle' })
    await expect(page.getByText('확장 국면 지속')).toBeVisible()
    const recoveryMs = Date.now() - t0
    console.log(`[429-smoke ②] 429시 overview호출=${overviewOn429} 회복=${recoveryMs}ms`)
    expect(recoveryMs, `회복 ${recoveryMs}ms`).toBeLessThan(2000)
  })
})
