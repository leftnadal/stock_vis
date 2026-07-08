'use client'

interface Props {
  step: number
  totalSteps: number
}

export function ProgressBar({ step, totalSteps }: Props) {
  const percent = Math.round((step / totalSteps) * 100)

  return (
    <div className="h-0.5 bg-gray-800 w-full">
      <div
        className="h-full bg-blue-500 transition-all duration-500 ease-out"
        style={{ width: `${percent}%` }}
      />
    </div>
  )
}
