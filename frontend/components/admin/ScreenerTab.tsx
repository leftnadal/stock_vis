'use client';

import { useAdminScreener } from '@/hooks/useAdminDashboard';
import StatusBadge from './shared/StatusBadge';
import ActionButton from './shared/ActionButton';

export default function ScreenerTab() {
  const { data, isLoading, error } = useAdminScreener();

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-32 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return <div className="text-center py-12 text-red-500">데이터 로드 실패</div>;
  }

  const { breadth, sector_performance, alerts } = data;

  return (
    <div className="space-y-6">
      {/* Market Breadth */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-gray-800 dark:text-gray-200">Market Breadth</h3>
            {!breadth.today.exists && <ActionButton action="sync_breadth" label="Breadth 계산" />}
          </div>
          <StatusBadge status={breadth.today.exists ? 'ok' : 'error'} label={breadth.today.exists ? 'OK' : 'Missing'} />
        </div>
        {breadth.today.exists && (
          <div className="flex gap-6 mb-4 text-sm">
            <div>
              <span className="text-gray-500 dark:text-gray-400">Signal: </span>
              <span className="font-medium">{breadth.today.signal}</span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">A/D Ratio: </span>
              <span className="font-medium">{breadth.today.advance_decline_ratio}</span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Date: </span>
              <span className="font-medium">{breadth.today.date}</span>
            </div>
          </div>
        )}

        {/* 7일 이력 */}
        {breadth.history.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Date</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Signal</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">A/D Ratio</th>
                  <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Advancing</th>
                  <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">Declining</th>
                </tr>
              </thead>
              <tbody>
                {breadth.history.map((h) => (
                  <tr key={h.date} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300">{h.date}</td>
                    <td className="py-1.5 px-2">
                      <span className={`text-xs font-medium ${
                        h.breadth_signal.includes('bullish') ? 'text-green-600' :
                        h.breadth_signal.includes('bearish') ? 'text-red-600' : 'text-gray-600'
                      }`}>
                        {h.breadth_signal}
                      </span>
                    </td>
                    <td className="py-1.5 px-2 text-gray-600 dark:text-gray-400">{h.advance_decline_ratio}</td>
                    <td className="py-1.5 px-2 text-right text-green-600">{h.advancing_count}</td>
                    <td className="py-1.5 px-2 text-right text-red-600">{h.declining_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Sector Performance */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-gray-800 dark:text-gray-200">Sector Heatmap</h3>
            {!sector_performance.complete && <ActionButton action="sync_heatmap" label="히트맵 계산" />}
          </div>
          <StatusBadge
            status={sector_performance.complete ? 'ok' : 'warning'}
            label={`${sector_performance.count}/${sector_performance.expected} 섹터`}
          />
        </div>
      </div>

      {/* Alerts */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800 dark:text-gray-200">스크리너 알림</h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">{alerts.active_count}개 활성</span>
        </div>
        {alerts.recent_history.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">알림명</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">상태</th>
                  <th className="text-right py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">매칭 수</th>
                  <th className="text-left py-2 px-2 text-gray-500 dark:text-gray-400 font-medium">시간</th>
                </tr>
              </thead>
              <tbody>
                {alerts.recent_history.map((h) => (
                  <tr key={h.id} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300">{h.alert__name}</td>
                    <td className="py-1.5 px-2">
                      <StatusBadge
                        status={h.status === 'sent' ? 'ok' : h.status === 'failed' ? 'error' : 'warning'}
                        label={h.status}
                      />
                    </td>
                    <td className="py-1.5 px-2 text-right text-gray-600 dark:text-gray-400">{h.matched_count}</td>
                    <td className="py-1.5 px-2 text-xs text-gray-500 dark:text-gray-400">
                      {new Date(h.triggered_at).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">최근 알림 이력 없음</p>
        )}
      </div>
    </div>
  );
}
