/**
 * HUB-V02-S2 — 전역 서브탭 왕복 + 정적 문장 회귀 안전망.
 *
 * 데스크탑 + Pixel5. 홈(개요) → 거시 근거 → 로테이션을 헤더 서브탭으로 왕복.
 * 각 화면: 서브탭 노출·active 정확·콘솔 에러 0·가로 스크롤 부재. 스크린샷 아티팩트(DoD 겸용).
 * route interception(실캡처 macroPulseFixture)로 백엔드/인증 무의존. overview translations=null
 * → breadth 정적 fallback이 실제로 렌더됨을 함께 확증.
 */
import { test, expect } from '@playwright/test'

import { mockMarketPulse } from './fixtures/marketPulse'

const CONSOLE_ALLOW = [/favicon/i, /manifest/i, /Download the React DevTools/i]

async function noHOverflow(page: import('@playwright/test').Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow, `가로 오버플로 ${overflow}px`).toBeLessThanOrEqual(1)
}

test.describe('Market Pulse v2 서브탭 왕복', () => {
  test('홈 → 거시 근거 → 로테이션 (서브탭·정적 문장·콘솔0)', async ({ page }, testInfo) => {
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() !== 'error') return
      const t = msg.text()
      if (CONSOLE_ALLOW.some((re) => re.test(t))) return
      consoleErrors.push(t)
    })
    page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`))

    await mockMarketPulse(page)

    // ── ① 홈(개요) ──
    await page.goto('/market-pulse-v2', { waitUntil: 'networkidle' })
    await expect(page.getByTestId('mp-tab-overview')).toHaveAttribute('aria-current', 'page')
    await expect(page.getByTestId('mp-tab-macro')).toBeVisible()
    await expect(page.getByTestId('mp-tab-movers')).toHaveAttribute('aria-disabled', 'true')
    // breadth 정적 fallback(translations=null) — 실수치 서술이 화면에 존재
    await expect(page.getByText('상승 320 대 하락 160', { exact: false })).toBeVisible()
    await noHOverflow(page)
    await page.screenshot({ path: testInfo.outputPath(`home-subnav-${testInfo.project.name}.png`), fullPage: true })

    // ── ② 거시 근거(서브탭 클릭) ──
    await page.getByTestId('mp-tab-macro').click()
    await expect(page).toHaveURL(/\/market-pulse-v2\/macro$/)
    await expect(page.getByRole('heading', { name: '거시 근거' })).toBeVisible()
    await expect(page.getByTestId('mp-tab-macro')).toHaveAttribute('aria-current', 'page')
    // 위젯 아래 국면 연결 한 줄(SenseNote) 존재 — 최소 1개
    await expect(page.getByTestId('sense-note').first()).toBeVisible()
    await noHOverflow(page)
    await page.screenshot({ path: testInfo.outputPath(`macro-hub-${testInfo.project.name}.png`), fullPage: true })

    // ── ③ 로테이션(서브탭 클릭) ──
    await page.getByTestId('mp-tab-rotation').click()
    await expect(page).toHaveURL(/\/market-pulse-v2\/rotation$/)
    await expect(page.getByRole('heading', { name: '섹터 회전 맵' })).toBeVisible()
    await expect(page.getByTestId('mp-tab-rotation')).toHaveAttribute('aria-current', 'page')
    await noHOverflow(page)
    await page.screenshot({ path: testInfo.outputPath(`rotation-${testInfo.project.name}.png`), fullPage: true })

    // ── ④ 개요로 복귀 ──
    await page.getByTestId('mp-tab-overview').click()
    await expect(page).toHaveURL(/\/market-pulse-v2$/)
    await expect(page.getByTestId('mp-tab-overview')).toHaveAttribute('aria-current', 'page')

    expect(consoleErrors, `콘솔 에러:\n${consoleErrors.join('\n')}`).toEqual([])
  })
})
