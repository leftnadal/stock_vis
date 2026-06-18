'use client';

import { AlertTriangle } from 'lucide-react';
import type { EventRankingItem } from '@/types/chainsight';

interface Props {
  item: EventRankingItem;
}

/**
 * 신뢰 경고 영역 — 토글 없이 상시 표시.
 * 저유동성 경고(is_low_liquidity) + 데이터 부족 경고(is_fallback) 묶음.
 * 점수분해는 EventRanking chevron 펼침("관심도 근거")으로 이전됨(Slice 1).
 */
export default function LowLiquidityPanel({ item }: Props) {
  return (
    <div className="mt-2 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-3 space-y-2">
      {item.is_low_liquidity && (
        <div className="flex items-start gap-2">
          <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-800 dark:text-amber-200">
            거래량이 얕아 체결·청산이 불리할 수 있습니다. 진입 전 호가 확인.
          </p>
        </div>
      )}
      {item.is_fallback && (
        <div className="flex items-start gap-2">
          <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-800 dark:text-amber-200">
            데이터가 부족해 보정된 값이에요.
          </p>
        </div>
      )}
    </div>
  );
}
