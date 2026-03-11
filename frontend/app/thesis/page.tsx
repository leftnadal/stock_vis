import { Suspense } from 'react'
import { ThesisListSkeleton } from '@/components/thesis/skeleton/ThesisSkeleton'

export default function ThesisPage() {
  return (
    <Suspense fallback={<ThesisListSkeleton />}>
      <div className="text-gray-500 text-center py-20">
        <p className="text-lg">가설 목록 -- FE-PR-2에서 구현</p>
      </div>
    </Suspense>
  )
}
