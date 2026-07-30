import { redirect } from 'next/navigation'

/**
 * `/dashboard` → `/` redirect (STRIP-REHOME, D-DASH-SURFACE-UNIFY D-2).
 *
 * 실 대시보드는 루트 `/`(app/page.tsx). 이 레거시 경로는 네비 도달 경로가 없어
 * 직접 URL 진입 시 실 대시보드로 안내한다(표면 통일, 가역 조치).
 * ⚠ 중첩 라우트 `/dashboard/coverage`는 자체 page라 이 redirect의 영향을 받지 않는다
 *   (Next.js App Router: redirect는 이 세그먼트의 정확 경로에만 적용).
 * DASH-LEGACY(KEEP/CUT/MOVE) 최종 운명은 미확정 — redirect는 1줄·완전 가역.
 */
export default function DashboardPage() {
  redirect('/')
}
