'use client'

// 알림 패널의 개별 전이 행 (MON-P3-ALERT §4).
import { StateBandSparkline } from '@/components/monitor/StateBandSparkline'
import { useSparkline } from '@/hooks/useMonitor'
import type { AlertEvent } from '@/types/monitor'

interface AlertRowProps {
  alert: AlertEvent
  onRead: (id: string) => void
}

export function AlertRow({ alert, onRead }: AlertRowProps) {
  const { data: spark } = useSparkline(alert.monitor, 30)

  return (
    <button
      type="button"
      onClick={() => !alert.read && onRead(alert.id)}
      data-testid="alert-row"
      aria-label={`${alert.monitor_name}: ${alert.from_label} → ${alert.to_label}`}
      className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition ${
        alert.read
          ? 'border-gray-100 bg-white opacity-60 dark:border-gray-800 dark:bg-gray-900'
          : 'border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800'
      }`}
    >
      <span
        className={`h-2 w-2 shrink-0 rounded-full ${
          alert.is_deterioration ? 'bg-red-500' : 'bg-green-500'
        }`}
        aria-hidden
      />

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
          {alert.monitor_name}
        </p>
        <p
          className={`text-xs ${
            alert.is_deterioration
              ? 'text-red-600 dark:text-red-400'
              : 'text-green-600 dark:text-green-400'
          }`}
        >
          {alert.from_label} → {alert.to_label}
        </p>
        <p className="mt-0.5 text-[11px] text-gray-400">
          score {alert.score.toFixed(2)} · {alert.asof}
        </p>
      </div>

      {spark && (
        <StateBandSparkline
          series={spark.series}
          bands={spark.bands}
          transitions={spark.transitions}
          width={56}
          height={20}
          className="shrink-0"
        />
      )}
    </button>
  )
}
