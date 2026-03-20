'use client';

import { formatDistanceToNow, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import { useAlerts, useResolveAlert } from '@/hooks/useNewsPipeline';
import type { AlertSeverity } from '@/types/newsPipeline';

const SEVERITY_STYLES: Record<
  AlertSeverity,
  { bg: string; text: string; border: string; label: string }
> = {
  critical: {
    bg: 'bg-red-900/30',
    text: 'text-red-400',
    border: 'border-red-800',
    label: '긴급',
  },
  high: {
    bg: 'bg-orange-900/30',
    text: 'text-orange-400',
    border: 'border-orange-800',
    label: '높음',
  },
  medium: {
    bg: 'bg-yellow-900/30',
    text: 'text-yellow-400',
    border: 'border-yellow-800',
    label: '주의',
  },
  low: {
    bg: 'bg-gray-800',
    text: 'text-gray-400',
    border: 'border-gray-700',
    label: '낮음',
  },
};

function formatRelativeTime(isoString: string): string {
  try {
    return formatDistanceToNow(parseISO(isoString), {
      addSuffix: true,
      locale: ko,
    });
  } catch {
    return isoString;
  }
}

export function AlertList() {
  const { data, isLoading, error } = useAlerts({ resolved: false });
  const resolveAlert = useResolveAlert();

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-4">파이프라인 알림</h3>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-700 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">파이프라인 알림</h3>
        <p className="text-sm text-red-400">알림 데이터 로드 실패</p>
      </div>
    );
  }

  const alerts = data?.alerts ?? [];

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-200">
          파이프라인 알림
          {data && data.unresolved_count > 0 && (
            <span className="ml-2 inline-flex items-center justify-center px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 text-xs font-medium">
              {data.unresolved_count}
            </span>
          )}
        </h3>
        {data && (
          <span className="text-xs text-gray-500">전체 {data.total}건</span>
        )}
      </div>

      {alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <CheckCircle2 className="h-8 w-8 text-green-500" />
          <p className="text-sm text-gray-400">미해결 알림이 없습니다</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const styles = SEVERITY_STYLES[alert.severity];
            const isPending =
              resolveAlert.isPending &&
              resolveAlert.variables?.alertId === alert.id;

            return (
              <div
                key={alert.id}
                className={`rounded-lg border p-4 ${styles.bg} ${styles.border}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <AlertTriangle
                      className={`h-4 w-4 mt-0.5 shrink-0 ${styles.text}`}
                    />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span
                          className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-semibold ${styles.text} ${styles.bg} border ${styles.border}`}
                        >
                          {styles.label}
                        </span>
                        <span className="text-xs font-medium text-gray-300 truncate">
                          {alert.trigger_type_display}
                        </span>
                      </div>
                      <p className="text-sm text-gray-200 leading-snug">
                        {alert.message}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatRelativeTime(alert.created_at)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() =>
                      resolveAlert.mutate({ alertId: alert.id })
                    }
                    disabled={isPending}
                    className="shrink-0 px-3 py-1.5 rounded-md text-xs font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isPending ? '처리 중...' : '해결'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
