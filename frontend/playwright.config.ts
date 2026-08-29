import { defineConfig, devices } from '@playwright/test'

/**
 * P2-DLITE — E2E 화면 회귀 안전망 (MP2-E2E-SAFETYNET).
 *
 * 격리 원칙: 라이브 :3000(web-frontend 런타임)과 충돌 없이 **:3100**의 자체 prod
 * 빌드(next start)를 구동한다. 모든 백엔드 호출은 Playwright route interception으로
 * 모킹 → 인증/공유DB/런타임 3트리 무의존·결정론.
 *
 * 프로젝트 2종: 데스크탑(Chrome) + 모바일(Pixel 5·chromium 엔진 = MP2-MOBILE-EYECHECK
 * 뷰포트 에뮬레이션 흡수). webkit 미설치(chromium 단일).
 */
const PORT = Number(process.env.E2E_PORT ?? 3100)
const BASE_URL = `http://127.0.0.1:${PORT}`

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  outputDir: 'test-results',
  timeout: 30_000,
  expect: { timeout: 7_000 },
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-pixel5', use: { ...devices['Pixel 5'] } },
  ],
  // reuseExistingServer: 이미 :3100에 서버가 떠 있으면 재사용(수동 기동 + 2회 연속 실행).
  webServer: {
    command: `npm run start -- -p ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
