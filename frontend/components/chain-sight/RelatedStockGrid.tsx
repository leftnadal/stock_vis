'use client';

import { ChainSightStock } from '@/types/chainSight';
import RelatedStockCard from './RelatedStockCard';

interface RelatedStockGridProps {
  stocks: ChainSightStock[];
  isLoading?: boolean;
  onStockClick?: (symbol: string) => void;
}

/**
 * 관련 종목 그리드 컴포넌트
 *
 * 관련 종목들을 그리드 형태로 표시합니다.
 */
export default function RelatedStockGrid({
  stocks,
  isLoading = false,
  onStockClick,
}: RelatedStockGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"
          />
        ))}
      </div>
    );
  }

  if (stocks.length === 0) {
    return (
      <div className="p-8 text-center">
        <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
          <span className="text-2xl">🔍</span>
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          관련 종목이 없습니다
        </h3>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          이 카테고리에서 관련 종목을 찾을 수 없습니다.
          <br />
          다른 카테고리를 선택해 보세요.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3">
      {stocks.map((stock) => (
        <RelatedStockCard
          key={stock.symbol}
          stock={stock}
          onClick={() => onStockClick?.(stock.symbol)}
        />
      ))}
    </div>
  );
}
