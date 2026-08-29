/**
 * P2-DLITE Part 1 — /market-pulse-v2 화면 회귀 안전망 (MP2-E2E-SAFETYNET).
 *
 * 존재·비오류 중심(과도한 셀렉터 결합 금지). 데스크탑 + 모바일(Pixel 5) 두 프로젝트에서
 * 동일 실행. 콘솔 에러 0(허용목록) · 전면 에러 화면 부재 · 가로 스크롤 부재.
 */
import { test, expect } from '@playwright/test'

import { mockMarketPulse } from './fixtures/marketPulse'

// prod 빌드에서 무해한 콘솔 노이즈 허용목록(존재 시 무시). 그 외 error는 실패.
const CONSOLE_ALLOW = [/favicon/i, /manifest/i, /Download the React DevTools/i]

test.describe('market-pulse-v2 화면 안전망', () => {
  test('핵심 표면 렌더 + 콘솔 에러 0 + 전면 에러 부재 + 가로 스크롤 부재', async ({ page }, testInfo) => {
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() !== 'error') return
      const text = msg.text()
      if (CONSOLE_ALLOW.some((re) => re.test(text))) return
      consoleErrors.push(text)
    })
    page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`))

    await mockMarketPulse(page)
    await page.goto('/market-pulse-v2', { waitUntil: 'networkidle' })

    // ① 페이지 셸 존재
    await expect(page.getByRole('heading', { name: 'Market Pulse v2' })).toBeVisible()

    // ② 레짐 히어로(overview 렌더 프록시)
    await expect(page.getByText('확장 국면 지속')).toBeVisible()

    // ③ 전면 에러 화면 부재
    await expect(page.getByText('데이터를 불러오지 못했습니다.')).toHaveCount(0)

    // ④ Macro Playbook 카드 존재(shell 타이틀)
    await expect(page.getByText('거시 플레이북')).toBeVisible()

    // ⑤ 스트레스 표면 존재(hero 배지 + StressCard — available=true 픽스처가 크래시 없이 렌더).
    //    /스트레스/는 배지·카드 다중 매칭 → 존재 단언은 first()(과도한 결합 회피).
    await expect(page.getByText(/스트레스/).first()).toBeVisible()

    // ⑥ 티커바(부수 표면)
    await expect(page.getByText('SPY')).toBeVisible()

    // ⑦ 가로 스크롤 부재(특히 모바일) — 본문 폭이 뷰포트 초과하지 않음
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(overflow, `가로 오버플로 ${overflow}px`).toBeLessThanOrEqual(1)

    // ⑧ 스크린샷 아티팩트(프로젝트별)
    await page.screenshot({
      path: testInfo.outputPath(`mp-v2-${testInfo.project.name}.png`),
      fullPage: true,
    })

    // ⑨ 콘솔 에러 0
    expect(consoleErrors, `콘솔 에러:\n${consoleErrors.join('\n')}`).toEqual([])
  })
})
