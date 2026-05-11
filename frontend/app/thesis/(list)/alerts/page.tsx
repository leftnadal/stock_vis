'use client'

import { useState, useMemo, useCallback } from 'react'
import { useAlerts } from '@/lib/thesis/queries'
import { useMarkAlertRead } from '@/lib/thesis/mutations'
import { USE_MOCK, MOCK_ALERTS } from '@/lib/thesis/mock'
import type { ThesisAlert } from '@/lib/thesis/types'
import { AlertFilterTabs, type AlertFilter } from '@/components/thesis/alerts/AlertFilterTabs'
import { AlertCard } from '@/components/thesis/alerts/AlertCard'
import { EmptyAlerts } from '@/components/thesis/alerts/EmptyAlerts'
import { ThesisAlertsSkeleton } from '@/components/thesis/skeleton/ThesisSkeleton'

export default function ThesisAlertsPage() {
  const [filter, setFilter] = useState<AlertFilter>('all')

  // ── 데이터 조회 ──
  const { data, isLoading } = useAlerts({ enabled: !USE_MOCK })
  const markReadMutation = useMarkAlertRead()

  // ── Mock: 로컬 읽음 상태 관리 ──
  const [mockReadIds, setMockReadIds] = useState<Set<string>>(new Set())

  const alerts: ThesisAlert[] = useMemo(() => {
    if (USE_MOCK) {
      return MOCK_ALERTS.map((a) =>
        mockReadIds.has(a.id) ? { ...a, is_read: true } : a,
      )
    }
    return data ?? []
  }, [data, mockReadIds])

  const filtered = useMemo(() => {
    switch (filter) {
      case 'unread':
        return alerts.filter((a) => !a.is_read)
      case 'read':
        return alerts.filter((a) => a.is_read)
      default:
        return alerts
    }
  }, [alerts, filter])

  const unreadCount = useMemo(
    () => alerts.filter((a) => !a.is_read).length,
    [alerts],
  )

  const handleMarkRead = useCallback(
    (alertId: string) => {
      if (USE_MOCK) {
        setMockReadIds((prev) => new Set(prev).add(alertId))
        return
      }
      markReadMutation.mutate(alertId)
    },
    [markReadMutation],
  )

  if (isLoading && !USE_MOCK) return <ThesisAlertsSkeleton />

  return (
    <div>
      <h2 className="text-gray-300 text-sm font-medium mb-4">알림</h2>

      <AlertFilterTabs
        current={filter}
        onChange={setFilter}
        unreadCount={unreadCount}
      />

      {filtered.length === 0 ? (
        <EmptyAlerts filter={filter} />
      ) : (
        <ul className="space-y-3">
          {filtered.map((alert) => (
            <li key={alert.id}>
              <AlertCard alert={alert} onMarkRead={handleMarkRead} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
