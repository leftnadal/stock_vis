'use client';

import { useState } from 'react';
import type { CategorySignal } from '@/types/validation';

const SIGNAL_COLORS = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-400',
  red: 'bg-red-500',
  gray: 'bg-gray-300 dark:bg-gray-600',
} as const;

const SIGNAL_RING_COLORS = {
  green: 'ring-green-200',
  yellow: 'ring-yellow-200',
  red: 'ring-red-200',
  gray: 'ring-gray-200 dark:ring-gray-500',
} as const;

interface Props {
  companyName: string;
  categorySignals: CategorySignal[];
  summaryText: string;
}

export default function SignalSummaryCard({ companyName, categorySignals, summaryText }: Props) {
  const [tooltipIdx, setTooltipIdx] = useState<number | null>(null);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {companyName} 재무 체질 진단
      </h2>

      {/* 7개 카테고리 신호등 */}
      <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-hide">
        {categorySignals.map((sig, idx) => (
          <div
            key={sig.category}
            className="flex flex-col items-center min-w-[72px] relative"
            onMouseEnter={() => sig.signal === 'gray' ? setTooltipIdx(idx) : null}
            onMouseLeave={() => setTooltipIdx(null)}
          >
            {/* 신호등 */}
            <div
              className={`w-10 h-10 rounded-full ${SIGNAL_COLORS[sig.signal]} ring-4 ${SIGNAL_RING_COLORS[sig.signal]} mb-2`}
            />
            {/* 카테고리명 */}
            <span className="text-xs text-gray-600 dark:text-gray-400 text-center whitespace-nowrap">
              {sig.display_name}
            </span>

            {/* Gray 툴팁 */}
            {tooltipIdx === idx && sig.signal === 'gray' && (
              <div className="absolute top-12 left-1/2 -translate-x-1/2 z-10 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg whitespace-nowrap">
                {sig.signal_reason}
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 한줄 요약 */}
      <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
        <p className="text-sm text-gray-700 dark:text-gray-300">
          {summaryText}
        </p>
      </div>
    </div>
  );
}
