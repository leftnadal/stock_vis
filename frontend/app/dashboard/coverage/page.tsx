'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

import { CoverageDetailView } from '@/components/dashboard/CoverageDetailView'
import { useAuth } from '@/contexts/AuthContext'
import { useCoverage } from '@/hooks/useCoverage'

/** /dashboard/coverage — 커버리지 상세(C-1 범위). C-2 퍼널 영역 미포함. */
export default function CoverageDetailPage() {
  const { loading, isAuthenticated } = useAuth()
  const router = useRouter()
  const { data, isLoading, isError } = useCoverage()

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login')
    }
  }, [loading, isAuthenticated, router])

  if (loading || !isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">추천 커버리지</h1>
          <button
            onClick={() => router.push('/dashboard')}
            className="text-sm font-medium text-blue-600 hover:text-blue-500"
          >
            ← 대시보드
          </button>
        </div>

        {isLoading && (
          <div
            data-testid="coverage-detail-skeleton"
            className="h-40 animate-pulse rounded-lg bg-gray-200"
          />
        )}

        {isError && (
          <p className="text-sm text-gray-500">
            커버리지 데이터를 불러오지 못했습니다.
          </p>
        )}

        {!isLoading && !isError && data && <CoverageDetailView data={data} />}
      </main>
    </div>
  )
}
