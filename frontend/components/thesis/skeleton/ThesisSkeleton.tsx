'use client'

function S({ className = '' }: { className?: string }) {
  return <div className={`bg-gray-700 rounded animate-pulse ${className}`} />
}

// ═══ 가설 목록 페이지 ═══
export function ThesisListSkeleton() {
  return (
    <div className="space-y-6">
      {/* 관제 중 */}
      <div>
        <S className="h-4 w-20 mb-3" />
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <S className="h-5 w-32" />
                <S className="h-6 w-20 rounded-full" />
              </div>
              <S className="h-3 w-48 mb-2" />
              <div className="flex items-center gap-2">
                <S className="h-8 w-8 rounded-full" />
                <S className="h-3 w-36" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 오늘의 변화 */}
      <div>
        <S className="h-4 w-24 mb-3" />
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <S className="h-4 w-full mb-2" />
          <S className="h-3 w-3/4 mb-3" />
          <S className="h-8 w-24 rounded-lg" />
        </div>
      </div>

      {/* 새로운 가설 버튼 */}
      <div>
        <S className="h-4 w-24 mb-3" />
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <S key={i} className="h-14 rounded-xl" />
          ))}
        </div>
      </div>
    </div>
  )
}

// ═══ 관제실 대시보드 ═══
export function ThesisDashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <S className="h-6 w-40 mx-auto" />
        <S className="h-4 w-28 mx-auto" />
      </div>

      <div className="flex flex-col items-center gap-2">
        <S className="h-12 w-12 rounded-full" />
        <S className="h-4 w-48" />
      </div>

      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex flex-col items-center gap-2">
              <S className="h-9 w-9 rounded-full" />
              <S className="h-3 w-16" />
              <S className="h-3 w-12" />
            </div>
          </div>
        ))}
      </div>

      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <S className="h-4 w-20 mb-2" />
        <S className="h-3 w-full mb-1" />
        <S className="h-3 w-2/3" />
      </div>
    </div>
  )
}

// ═══ 알림 목록 ═══
export function ThesisAlertsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-start gap-3">
            <S className="h-5 w-5 rounded-full flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <S className="h-4 w-3/4 mb-2" />
              <S className="h-3 w-full mb-1" />
              <S className="h-3 w-1/2" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
