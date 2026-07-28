'use client'

// _reuse/builder에서 이식 (MON-P3-S2, 무의존 프리미티브)
interface Props {
  step: number
  totalSteps: number
}

export function ProgressBar({ step, totalSteps }: Props) {
  const percent = Math.round((step / totalSteps) * 100)

  return (
    <div className="h-1 w-full rounded bg-gray-200 dark:bg-gray-800">
      <div
        className="h-full rounded bg-blue-500 transition-all duration-500 ease-out"
        style={{ width: `${percent}%` }}
      />
    </div>
  )
}
