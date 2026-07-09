'use client'

// 모니터 알림 패널 (MON-P3-ALERT §4). 헤더 벨이 여기로 화면 전환한다.
import { useMemo, useState } from 'react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import { AlertRow } from '@/components/monitor/AlertRow'
import { useAlerts, useMarkAllAlertsRead, useMarkAlertRead } from '@/hooks/useMonitor'

function AlertPanelContent() {
  const { data: alerts, isLoading, isError } = useAlerts()
  const markRead = useMarkAlertRead()
  const markAllRead = useMarkAllAlertsRead()
  const [showImprovements, setShowImprovements] = useState(false)

  const { deteriorations, improvements } = useMemo(() => {
    const list = alerts ?? []
    return {
      deteriorations: list.filter((a) => a.is_deterioration),
      improvements: list.filter((a) => !a.is_deterioration),
    }
  }, [alerts])

  const hasUnread = (alerts ?? []).some((a) => !a.read)
  const isEmpty = deteriorations.length === 0 && improvements.length === 0

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">알림</h1>
          <p className="text-sm text-gray-500">모니터 상태 전이 기록</p>
        </div>
        <button
          type="button"
          onClick={() => markAllRead.mutate()}
          disabled={!hasUnread || markAllRead.isPending}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          모두 읽음
        </button>
      </div>

      {isLoading && <p className="py-12 text-center text-gray-400">불러오는 중…</p>}
      {isError && (
        <p className="py-12 text-center text-red-500">알림을 불러오지 못했어요.</p>
      )}

      {!isLoading && !isError && (
        <div className="flex flex-col gap-3">
          {isEmpty && (
            <p className="py-12 text-center text-sm text-gray-400">아직 알림이 없어요.</p>
          )}

          {deteriorations.map((a) => (
            <AlertRow key={a.id} alert={a} onRead={(id) => markRead.mutate(id)} />
          ))}

          {improvements.length > 0 && (
            <div className="rounded-xl border border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-900/40">
              <button
                type="button"
                onClick={() => setShowImprovements((v) => !v)}
                className="flex w-full items-center justify-between px-3 py-2.5 text-sm text-gray-600 dark:text-gray-300"
                data-testid="improvements-toggle"
              >
                <span>개선 전이 {improvements.length}건</span>
                <span className="text-xs text-gray-400">
                  {showImprovements ? '접기' : '펼치기'}
                </span>
              </button>
              {showImprovements && (
                <div className="flex flex-col gap-2 px-3 pb-3">
                  {improvements.map((a) => (
                    <AlertRow key={a.id} alert={a} onRead={(id) => markRead.mutate(id)} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function MonitorAlertsPage() {
  return (
    <AuthGuard>
      <AlertPanelContent />
    </AuthGuard>
  )
}
