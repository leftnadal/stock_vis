/**
 * MSW Node 테스트 서버 (vitest 환경).
 *
 * vitest.setup.ts에서 lifecycle 배선:
 *   beforeAll(server.listen) / afterEach(server.resetHandlers) / afterAll(server.close)
 */

import { setupServer } from 'msw/node'

import { handlers } from './handlers'

export const server = setupServer(...handlers)
