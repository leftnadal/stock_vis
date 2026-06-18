'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import type { EventRankingItem } from '@/types/chainsight';

interface Props {
  item: EventRankingItem;
}

export default function LowLiquidityPanel({ item }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-2">
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300"
        aria-expanded={isOpen}
        aria-label="저유동성 상세 정보 토글"
      >
        {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        저유동성 상세
      </button>

      {isOpen && (
        <div className="mt-2 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-3">
          {/* 점수 분해 */}
          <div className="mb-2 text-xs font-semibold text-amber-800 dark:text-amber-200">
            점수 분해
          </div>
          <div className="grid grid-cols-3 gap-2 mb-3">
            <div className="text-center">
              <div className="text-xs text-gray-500 dark:text-gray-400">거래량 Z</div>
              <div className="text-sm font-semibold text-gray-800 dark:text-gray-100">
                {item.volume_z.toFixed(2)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-gray-500 dark:text-gray-400">변동성</div>
              <div className="text-sm font-semibold text-gray-800 dark:text-gray-100">
                {(item.volatility_pct * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-gray-500 dark:text-gray-400">수익률</div>
              <div className={`text-sm font-semibold ${item.raw_return >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                {item.raw_return >= 0 ? '+' : ''}{(item.raw_return * 100).toFixed(2)}%
              </div>
            </div>
          </div>

          {/* 경고 박스 */}
          <div className="flex items-start gap-2 rounded-md bg-amber-100 dark:bg-amber-900/40 p-2">
            <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-800 dark:text-amber-200">
              거래량이 얕아 체결·청산이 불리할 수 있습니다. 진입 전 호가 확인.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
