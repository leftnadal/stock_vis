import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll } from 'vitest'

import { server } from './__tests__/mocks/server'

// MSW lifecycle — 모든 테스트 공통. msw 미사용 테스트는 영향 없음 (handlers
// 미매칭 요청은 onUnhandledRequest: 'error'로 명시적 실패시켜 mock 누락 탐지).
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
