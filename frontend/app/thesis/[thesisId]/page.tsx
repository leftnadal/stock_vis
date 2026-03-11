import { Suspense } from 'react'
import { ThesisDashboardSkeleton } from '@/components/thesis/skeleton/ThesisSkeleton'

export default function ThesisDashboardPage() {
  return (
    <Suspense fallback={<ThesisDashboardSkeleton />}>
      <div className="text-gray-500 text-center py-20">
        <p className="text-lg">관제실 -- FE-PR-5에서 구현</p>
      </div>
    </Suspense>
  )
}
