'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { CategoryMetrics, MetricData } from '@/types/validation';
import MetricCard from './MetricCard';

const SIGNAL_DOT: Record<string, string> = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-400',
  red: 'bg-red-500',
  gray: 'bg-gray-300 dark:bg-gray-600',
};

interface Props {
  category: CategoryMetrics;
  /** 모바일 Accordion: 펼쳐진 metric_code */
  expandedMetric?: string | null;
  onToggleMetric?: (code: string) => void;
  isMobile?: boolean;
}

export default function CategorySection({ category, expandedMetric, onToggleMetric, isMobile }: Props) {
  const isValuation = category.category === 'valuation';
  const [collapsed, setCollapsed] = useState(isValuation);

  return (
    <section id={`cat-${category.category}`} className="scroll-mt-20">
      {/* 카테고리 헤더 */}
      <div
        className={`flex items-center gap-3 mb-3 ${isValuation ? 'cursor-pointer' : ''}`}
        onClick={isValuation ? () => setCollapsed(!collapsed) : undefined}
      >
        <div className={`w-3 h-3 rounded-full flex-shrink-0 ${SIGNAL_DOT[category.signal]}`} />
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className={`text-base font-semibold ${isValuation ? 'text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white'}`}>
              {category.display_name}
            </h3>
            {isValuation && (
              <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded-full">
                보조 지표
              </span>
            )}
            {isValuation && (collapsed ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronUp className="w-4 h-4 text-gray-400" />)}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{category.description}</p>
        </div>
      </div>

      {/* 지표 카드 목록 */}
      {!collapsed && (
        <div className="space-y-3">
          {category.metrics.map((metric) => (
            isMobile ? (
              <MobileMetricAccordion
                key={metric.metric_code}
                metric={metric}
                isExpanded={expandedMetric === metric.metric_code}
                onToggle={() => onToggleMetric?.(metric.metric_code)}
              />
            ) : (
              <MetricCard key={metric.metric_code} metric={metric} />
            )
          ))}
        </div>
      )}
    </section>
  );
}

/** 모바일 Accordion: 접힌 상태 → 펼친 상태 */
function MobileMetricAccordion({
  metric,
  isExpanded,
  onToggle,
}: {
  metric: MetricData;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const pct = metric.benchmark?.percentile_rank;
  const val = metric.current?.value;
  const status = metric.current?.value_status || 'missing';

  const signal = status === 'normal' && pct !== null && pct !== undefined
    ? (metric.higher_is_better
        ? (pct >= 65 ? 'green' : pct >= 35 ? 'yellow' : 'red')
        : (100 - pct >= 65 ? 'green' : 100 - pct >= 35 ? 'yellow' : 'red'))
    : 'gray';

  function formatShort(v: number | null | undefined, unit: string): string {
    if (v === null || v === undefined) return '-';
    if (unit === 'ratio' || unit === 'pct') return `${(v * 100).toFixed(1)}%`;
    if (unit === 'multiple') return `${v.toFixed(1)}x`;
    if (unit === 'days') return `${v.toFixed(0)}일`;
    return v.toFixed(2);
  }

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* 접힌 상태 (항상 보임) */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50"
      >
        <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${SIGNAL_DOT[signal]}`} />
        <span className="text-sm font-medium text-gray-900 dark:text-white flex-1 truncate">
          {metric.display_name}
        </span>
        <span className="text-sm text-gray-600 dark:text-gray-300">
          {status === 'not_applicable' ? '해당없음' : status === 'missing' ? '-' : formatShort(val, metric.unit)}
        </span>
        {pct !== null && pct !== undefined && status === 'normal' && (
          <span className="text-xs text-gray-400 w-12 text-right">
            {pct.toFixed(0)}%
          </span>
        )}
        {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>

      {/* 펼친 상태 */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700">
          <MetricCard metric={metric} />
        </div>
      )}
    </div>
  );
}
