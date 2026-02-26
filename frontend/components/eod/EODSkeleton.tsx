'use client';

function SkeletonBox({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-gray-200 dark:bg-gray-700 rounded animate-pulse ${className}`} />
  );
}

function MarketSummaryBarSkeleton() {
  return (
    <div className="mb-4 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
      <SkeletonBox className="h-6 w-56 mb-3" />
      <div className="flex gap-2 mb-3">
        <SkeletonBox className="h-6 w-20 rounded-md" />
        <SkeletonBox className="h-6 w-16 rounded-md" />
        <SkeletonBox className="h-6 w-16 rounded-md" />
      </div>
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <SkeletonBox className="h-4 w-16" />
          <SkeletonBox className="h-2 w-20 rounded-full mt-1" />
        </div>
        <SkeletonBox className="h-4 w-12" />
      </div>
    </div>
  );
}

function SignalFilterTabsSkeleton() {
  return (
    <div className="mb-4 flex gap-2 overflow-hidden">
      {[68, 76, 84, 92, 100, 108, 116].map((w, i) => (
        <div
          key={i}
          className="h-8 rounded-full flex-shrink-0 bg-gray-200 dark:bg-gray-700 animate-pulse"
          style={{ width: `${w}px` }}
        />
      ))}
    </div>
  );
}

function SignalCardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
      style={{ borderLeft: '4px solid #374151' }}
    >
      <div className="px-4 pt-4 pb-3">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <SkeletonBox className="w-2 h-2 rounded-full" />
            <SkeletonBox className="h-3 w-12 rounded" />
          </div>
          <SkeletonBox className="h-5 w-8 rounded-full" />
        </div>
        {/* 제목 */}
        <SkeletonBox className="h-4 w-40 mb-1.5" />
        {/* 설명 */}
        <SkeletonBox className="h-3 w-full mb-1" />
        <SkeletonBox className="h-3 w-3/4" />
      </div>

      {/* 종목 3개 */}
      <div className="px-4 space-y-3 pb-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-start gap-2">
            <div className="flex-1 space-y-1">
              <SkeletonBox className="h-3.5 w-20" />
              <SkeletonBox className="h-5 w-full rounded" />
            </div>
            <div className="flex-shrink-0 flex flex-col items-end gap-1">
              <SkeletonBox className="h-5 w-14 rounded" />
              <SkeletonBox className="h-3 w-10" />
            </div>
          </div>
        ))}
      </div>

      {/* CTA 버튼 */}
      <div className="px-4 pb-4">
        <SkeletonBox className="h-8 w-full rounded-lg" />
      </div>
    </div>
  );
}

export function EODSkeleton() {
  return (
    <div className="min-h-screen pb-20 md:pb-0">
      <div className="max-w-6xl mx-auto px-4 py-4">
        {/* DataFreshnessBadge 스켈레톤 */}
        <div className="mb-3 flex justify-end">
          <SkeletonBox className="h-6 w-52 rounded-full" />
        </div>

        {/* MarketSummaryBar 스켈레톤 */}
        <MarketSummaryBarSkeleton />

        {/* SignalFilterTabs 스켈레톤 */}
        <SignalFilterTabsSkeleton />

        {/* SignalCardGrid 스켈레톤 - 6개 카드 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SignalCardSkeleton key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}
