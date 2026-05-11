'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Check, X } from 'lucide-react';
import { useLeaderComparison } from '@/hooks/useValidation';
import type { LeaderMetricComparison } from '@/types/validation';

interface Props {
  symbol: string;
}

export default function LeaderComparisonSection({ symbol }: Props) {
  const { data, isLoading } = useLeaderComparison(symbol);
  const [showDetail, setShowDetail] = useState(false);

  if (isLoading) {
    return <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />;
  }

  if (!data || data.error || data.total_compared === 0) {
    return null; // peer 부족 시 비표시
  }

  const summaryMetrics = data.summary_metrics || [];
  const detailMetrics = data.comparisons.filter(
    (c) => !summaryMetrics.some((s) => s.metric_code === c.metric_code)
  );

  // 카테고리별 그룹핑 (상세)
  const grouped = detailMetrics.reduce<Record<string, LeaderMetricComparison[]>>((acc, m) => {
    if (!acc[m.category]) acc[m.category] = [];
    acc[m.category].push(m);
    return acc;
  }, {});

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700">
      {/* 헤더 */}
      <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
        업종 {data.leader.symbol === symbol ? '2위' : '1위'}: {data.leader.symbol} ({data.leader.name})
      </h3>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
        {data.fiscal_year} FY 기준 · {data.total_compared}개 지표 비교
      </p>

      {/* 요약 6개 지표 테이블 */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left py-2 text-xs font-medium text-gray-500 dark:text-gray-400">지표</th>
              <th className="text-right py-2 text-xs font-medium text-gray-500 dark:text-gray-400">{symbol}</th>
              <th className="text-right py-2 text-xs font-medium text-gray-500 dark:text-gray-400">{data.leader.symbol}</th>
              <th className="text-center py-2 text-xs font-medium text-gray-500 dark:text-gray-400 w-12"></th>
            </tr>
          </thead>
          <tbody>
            {summaryMetrics.map((m) => (
              <ComparisonRow key={m.metric_code} metric={m} />
            ))}
          </tbody>
        </table>
      </div>

      {/* 상세 접기/펼치기 */}
      {detailMetrics.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setShowDetail(!showDetail)}
            className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            상세 {detailMetrics.length}개 {showDetail ? '접기' : '더 보기'}
            {showDetail ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          {showDetail && (
            <div className="mt-3 space-y-4">
              {Object.entries(grouped).map(([cat, metrics]) => (
                <div key={cat}>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 capitalize">
                    {cat.replace('_', ' ')}
                  </p>
                  <table className="w-full text-sm">
                    <tbody>
                      {metrics.map((m) => (
                        <ComparisonRow key={m.metric_code} metric={m} />
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 종합 요약 */}
      <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
        <p className="text-sm text-gray-700 dark:text-gray-300">{data.summary}</p>
      </div>
    </div>
  );
}

function ComparisonRow({ metric }: { metric: LeaderMetricComparison }) {
  function fmt(v: number): string {
    if (Math.abs(v) >= 100) return v.toFixed(1);
    return (v * 100).toFixed(1) + '%';
  }

  return (
    <tr className="border-b border-gray-50 dark:border-gray-700/50">
      <td className="py-1.5 text-gray-700 dark:text-gray-300">{metric.display_name}</td>
      <td className="py-1.5 text-right font-medium text-gray-900 dark:text-white">{fmt(metric.company_value)}</td>
      <td className="py-1.5 text-right text-gray-500 dark:text-gray-400">{fmt(metric.leader_value)}</td>
      <td className="py-1.5 text-center">
        {metric.is_advantage ? (
          <Check className="w-4 h-4 text-green-500 inline" />
        ) : (
          <X className="w-4 h-4 text-red-400 inline" />
        )}
      </td>
    </tr>
  );
}
