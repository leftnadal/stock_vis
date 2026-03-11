import { Suspense } from 'react'
import { ThesisAlertsSkeleton } from '@/components/thesis/skeleton/ThesisSkeleton'

export default function ThesisAlertsPage() {
  return (
    <Suspense fallback={<ThesisAlertsSkeleton />}>
      <div className="text-gray-500 text-center py-20">
        <p className="text-lg">알림 -- FE-PR-6에서 구현</p>
      </div>
    </Suspense>
  )
}
