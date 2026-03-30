'use client';

import { AlertTriangle } from 'lucide-react';
import type { MetricData } from '@/types/validation';
import MetricBarChart from './MetricBarChart';

const SIGNAL_DOT: Record<string, string> = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-400',
  red: 'bg-red-500',
  gray: 'bg-gray-300 dark:bg-gray-600',
};

function getSignalFromPercentile(pct: number | null, higherIsBetter: boolean): string {
  if (pct === null) return 'gray';
  const effective = higherIsBetter ? pct : 100 - pct;
  if (effective >= 65) return 'green';
  if (effective >= 35) return 'yellow';
  return 'red';
}

function formatMetricValue(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined) return '-';
  switch (unit) {
    case 'ratio':
    case 'pct':
      return `${(value * 100).toFixed(1)}%`;
    case 'multiple':
      return `${value.toFixed(2)}x`;
    case 'days':
      return `${value.toFixed(0)}일`;
    case 'years':
      return `${value.toFixed(1)}년`;
    case 'percent_point':
      return `${(value * 100).toFixed(1)}%p`;
    default:
      return value.toFixed(2);
  }
}

interface Props {
  metric: MetricData;
}

export default function MetricCard({ metric }: Props) {
  const { current, benchmark, history, trend, interpretation } = metric;
  const valueStatus = current?.value_status || 'missing';

  // not_applicable
  if (valueStatus === 'not_applicable') {
    return (
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-5 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-2">
          <div className={`w-3 h-3 rounded-full ${SIGNAL_DOT.gray}`} />
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{metric.display_name}</h4>
          <span className="text-xs text-gray-400">{metric.display_name_en}</span>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">해당 없음 — {interpretation}</p>
      </div>
    );
  }

  // missing
  if (valueStatus === 'missing') {
    return (
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-5 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-2">
          <div className={`w-3 h-3 rounded-full ${SIGNAL_DOT.gray}`} />
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{metric.display_name}</h4>
          <span className="text-xs text-gray-400">{metric.display_name_en}</span>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">데이터 누락</p>
      </div>
    );
  }

  // normal / unstable / low_confidence
  const signal = getSignalFromPercentile(benchmark?.percentile_rank ?? null, metric.higher_is_better);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-5 border border-gray-200 dark:border-gray-700">
      {/* 상단: 신호등 + 지표명 */}
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-3 h-3 rounded-full ${SIGNAL_DOT[signal]}`} />
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{metric.display_name}</h4>
        <span className="text-xs text-gray-400">{metric.display_name_en}</span>
      </div>

      {/* 경고 배너 */}
      {valueStatus === 'unstable' && (
        <div className="flex items-center gap-1.5 mb-3 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 rounded text-xs text-amber-700 dark:text-amber-400">
          <AlertTriangle className="w-3.5 h-3.5" />
          값 변동이 크므로 해석 주의
        </div>
      )}
      {valueStatus === 'low_confidence' && (
        <div className="flex items-center gap-1.5 mb-3 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 rounded text-xs text-amber-700 dark:text-amber-400">
          <AlertTriangle className="w-3.5 h-3.5" />
          비교 표본 부족
        </div>
      )}

      {/* 중단: 현재값 + benchmark */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 text-sm">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">현재값</p>
          <p className="font-semibold text-gray-900 dark:text-white">
            {formatMetricValue(current?.value, metric.unit)}
          </p>
        </div>
        {benchmark && (
          <>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">업종 중앙값</p>
              <p className="font-medium text-gray-700 dark:text-gray-300">
                {formatMetricValue(benchmark.median, metric.unit)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">순위</p>
              <p className="font-medium text-gray-700 dark:text-gray-300">
                {benchmark.rank && benchmark.total ? `${benchmark.rank}/${benchmark.total}` : '-'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">백분위</p>
              <p className="font-medium text-gray-700 dark:text-gray-300">
                {benchmark.percentile_rank !== null ? `${benchmark.percentile_rank.toFixed(0)}%` : '-'}
              </p>
            </div>
          </>
        )}
      </div>

      {/* 하단: 차트 */}
      {history.length > 0 && (
        <MetricBarChart
          history={history}
          unit={metric.unit}
          higherIsBetter={metric.higher_is_better}
        />
      )}

      {/* 해석 텍스트 */}
      <p className="mt-3 text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
        {interpretation}
      </p>
    </div>
  );
}
