// /dashboard → / redirect 검증 (STRIP-REHOME, D-DASH-SURFACE-UNIFY D-2)
import { describe, expect, it, vi } from 'vitest'

const redirect = vi.fn()
vi.mock('next/navigation', () => ({
  redirect: (path: string) => redirect(path),
}))

import DashboardPage from '@/app/dashboard/page'

describe('DashboardPage (레거시 /dashboard)', () => {
  it('루트 / 로 redirect 한다 (표면 통일)', () => {
    DashboardPage()
    expect(redirect).toHaveBeenCalledWith('/')
  })
})
