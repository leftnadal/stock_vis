'use client';

import { useState } from 'react';
import { Search, Loader2, AlertCircle } from 'lucide-react';
import { useStockScreener } from '@/hooks/useStockScreener';
import { ScreenerFilters } from './ScreenerFilters';
import { ScreenerTable } from './ScreenerTable';
import type { ScreenerFilters as Filters } from '@/services/strategyService';

interface StockScreenerPanelProps {
  onAddToBasket?: (symbol: string) => void;
}

export function StockScreenerPanel({ onAddToBasket }: StockScreenerPanelProps) {
  const [filters, setFilters] = useState<Filters>({});
  const { data: stocks, isLoading, error } = useStockScreener(filters);

  const handleFilterChange = (newFilters: Filters) => {
    setFilters(newFilters);
  };

  return (
    <div className="rounded-lg border border-[#30363D] bg-[#161B22] p-6">
      {/* 헤더 */}
      <div className="mb-4 flex items-center gap-2">
        <Search className="h-5 w-5 text-[#58A6FF]" />
        <h2 className="text-lg font-semibold text-[#E6EDF3]">종목 스크리너</h2>
        {stocks && (
          <span className="ml-auto text-xs text-[#8B949E]">
            {stocks.length}개 종목 발견
          </span>
        )}
      </div>

      {/* 필터 */}
      <div className="mb-4">
        <ScreenerFilters onFilterChange={handleFilterChange} />
      </div>

      {/* 로딩 상태 */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-[#58A6FF]" />
        </div>
      )}

      {/* 에러 상태 */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-[#F85149]/20 bg-[#F85149]/10 p-4">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-[#F85149]" />
          <p className="text-sm text-[#E6EDF3]">데이터를 불러올 수 없습니다.</p>
        </div>
      )}

      {/* 테이블 */}
      {!isLoading && !error && stocks && (
        <ScreenerTable stocks={stocks} onAddToBasket={onAddToBasket} />
      )}
    </div>
  );
}
