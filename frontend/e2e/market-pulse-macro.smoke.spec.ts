/**
 * MP2-SUBPAGES S1 — 거시 근거 허브 화면 회귀 안전망.
 *
 * 데스크탑 + Pixel5. 4위젯 존재·콘솔 에러 0·가로 스크롤 부재 + 홈 CTA 클릭→허브 도달.
 * route interception(macro/pulse 실응답 캡처 픽스처)로 백엔드/인증 무의존.
 */
import { test, expect } from '@playwright/test'

import { mockMarketPulse } from './fixtures/marketPulse'

const CONSOLE_ALLOW = [/favicon/i, /manifest/i, /Download the React DevTools/i]

test.describe('거시 근거 허브 안전망', () => {
  test('허브 로드 — 4위젯 존재 + 콘솔 에러 0 + 가로 스크롤 부재', async ({ page }, testInfo) => {
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() !== 'error') return
      const t = msg.text()
      if (CONSOLE_ALLOW.some((re) => re.test(t))) return
      consoleErrors.push(t)
    })
    page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`))

    await mockMarketPulse(page)
    await page.goto('/market-pulse-v2/macro', { waitUntil: 'networkidle' })

    // 헤더 + 탭
    await expect(page.getByRole('heading', { name: '거시 근거' })).toBeVisible()
    await expect(page.getByRole('navigation', { name: '거시 탭' })).toBeVisible()

    // 4위젯 존재(data-guide anchor로 결합 회피)
    for (const anchor of [
      'marketPulse.macro.sentiment',
      'marketPulse.macro.rates',
      'marketPulse.macro.economy',
      'marketPulse.macro.global',
    ]) {
      await expect(page.locator(`[data-guide="${anchor}"]`)).toBeVisible()
    }

    // 무버스 탭 = 준비 중(비활성)
    await expect(page.getByText('준비 중')).toBeVisible()

    // 전면 에러(준비 중 안내) 부재 — 실데이터 렌더 시엔 안 나와야 함
    await expect(
      page.getByText('거시 데이터를 준비 중입니다 — 잠시 후 자동으로 다시 시도합니다.'),
    ).toHaveCount(0)

    // 가로 스크롤 부재
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(overflow, `가로 오버플로 ${overflow}px`).toBeLessThanOrEqual(1)

    await page.screenshot({
      path: testInfo.outputPath(`macro-hub-${testInfo.project.name}.png`),
      fullPage: true,
    })
    expect(consoleErrors, `콘솔 에러:\n${consoleErrors.join('\n')}`).toEqual([])
  })

  test('?tab=rates 딥링크 — 금리·지표만 표시(심리·글로벌 숨김)', async ({ page }) => {
    await mockMarketPulse(page)
    await page.goto('/market-pulse-v2/macro?tab=rates', { waitUntil: 'networkidle' })
    await expect(page.locator('[data-guide="marketPulse.macro.rates"]')).toBeVisible()
    await expect(page.locator('[data-guide="marketPulse.macro.economy"]')).toBeVisible()
    await expect(page.locator('[data-guide="marketPulse.macro.sentiment"]')).toHaveCount(0)
    await expect(page.locator('[data-guide="marketPulse.macro.global"]')).toHaveCount(0)
  })

  test('홈 CTA 클릭 → 허브 도달', async ({ page }) => {
    await mockMarketPulse(page)
    await page.goto('/market-pulse-v2', { waitUntil: 'networkidle' })
    await page.getByRole('link', { name: /거시 근거 보기/ }).click()
    await expect(page).toHaveURL(/\/market-pulse-v2\/macro$/)
    await expect(page.getByRole('heading', { name: '거시 근거' })).toBeVisible()
  })
})
