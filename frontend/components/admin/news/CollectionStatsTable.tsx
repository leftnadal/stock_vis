'use client';

import { useCollectionLogs } from '@/hooks/useNewsPipeline';

interface CollectionStatsTableProps {
  enabled?: boolean;
}

export function CollectionStatsTable({ enabled = true }: CollectionStatsTableProps) {
  const { data, isLoading, error } = useCollectionLogs(1, enabled);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-4">수집 현황 (오늘)</h3>
        <div className="h-32 bg-gray-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="font-semibold text-gray-200 mb-2">수집 현황 (오늘)</h3>
        <p className="text-sm text-red-400">데이터 로드 실패</p>
      </div>
    );
  }

  const byProvider = data.aggregated.by_provider;
  const providers = Object.keys(byProvider);

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <h3 className="font-semibold text-gray-200 mb-4">수집 현황 (오늘 · KST 자정 기준)</h3>

      {providers.length === 0 ? (
        <p className="text-sm text-gray-500">오늘 수집 데이터가 없습니다.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-2 px-3 text-gray-400 font-medium">Provider</th>
                <th className="text-right py-2 px-3 text-gray-400 font-medium">신규</th>
                <th className="text-right py-2 px-3 text-gray-400 font-medium">중복</th>
                <th className="text-right py-2 px-3 text-gray-400 font-medium">에러</th>
                <th className="text-right py-2 px-3 text-gray-400 font-medium">실행</th>
                <th className="text-right py-2 px-3 text-gray-400 font-medium">평균 소요</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((provider) => {
                const stats = byProvider[provider];
                const hasErrors = stats.total_errors > 0;
                return (
                  <tr
                    key={provider}
                    className={`border-b border-gray-700/50 ${
                      hasErrors ? 'bg-red-900/10' : ''
                    }`}
                  >
                    <td className="py-2 px-3 font-mono text-xs text-gray-300">{provider}</td>
                    <td className="py-2 px-3 text-right text-gray-300">
                      {stats.total_new.toLocaleString()}
                    </td>
                    <td className="py-2 px-3 text-right text-gray-400">
                      {stats.total_dup.toLocaleString()}
                    </td>
                    <td className={`py-2 px-3 text-right font-medium ${hasErrors ? 'text-red-400' : 'text-gray-400'}`}>
                      {stats.total_errors}
                    </td>
                    <td className="py-2 px-3 text-right text-gray-400">{stats.total_runs}</td>
                    <td className="py-2 px-3 text-right text-gray-400">
                      {stats.avg_duration_sec.toFixed(1)}s
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
