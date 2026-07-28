import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['__tests__/**/*.{test,spec}.{ts,tsx}'],
    // 테스트용 절대 base (#55 fail-fast 소스가 요구). MSW 핸들러·코드 모두 동일 base 사용.
    // 죽은 포트 미사용 — 테스트 전용 임의 호스트.
    env: { NEXT_PUBLIC_API_URL: 'http://localhost/api/v1' },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
})
