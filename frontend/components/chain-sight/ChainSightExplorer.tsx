'use client';

import { useState } from 'react';
import { Compass, RefreshCw, AlertCircle } from 'lucide-react';
import { useChainSightCategories, useChainSightSync } from '@/hooks/useChainSightCategories';
import { useChainSightStocks } from '@/hooks/useChainSightStocks';
import CategorySelector from './CategorySelector';
import RelatedStockGrid from './RelatedStockGrid';
import AIInsightPanel from './AIInsightPanel';

interface ChainSightExplorerProps {
  symbol: string;
}

/**
 * Chain Sight Explorer 메인 컴포넌트
 *
 * 개별 주식 페이지에서 AI 가이드와 함께하는 주식 탐험 기능.
 * 카테고리 선택 → 관련 종목 표시 → 종목 클릭으로 "파도타기" 가능.
 */
export default function ChainSightExplorer({ symbol }: ChainSightExplorerProps) {
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);

  // 카테고리 조회
  const {
    categories,
    companyName,
    isColdStart,
    isLoading: isCategoriesLoading,
    error: categoriesError,
  } = useChainSightCategories(symbol);

  // 동기화 뮤테이션
  const { mutate: sync, isPending: isSyncing } = useChainSightSync(symbol);

  // 선택된 카테고리의 종목 조회
  const {
    stocks,
    category: selectedCategory,
    aiInsights,
    followUpQuestions,
    isLoading: isStocksLoading,
  } = useChainSightStocks(symbol, selectedCategoryId);

  // Cold Start 처리
  if (isColdStart && !isSyncing) {
    return (
      <div className="rounded-lg bg-white shadow-sm dark:bg-gray-800">
        {/* 헤더 */}
        <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Compass className="h-5 w-5 text-blue-500" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Chain Sight
              </h2>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                AI 가이드와 함께하는 주식 탐험
              </span>
            </div>
          </div>
        </div>

        {/* Cold Start 안내 */}
        <div className="p-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
            <Compass className="h-8 w-8 text-blue-500" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {symbol} 탐험 준비 중
          </h3>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {symbol}의 관계 데이터를 수집하고 있습니다.
            <br />
            잠시만 기다리거나 아래 버튼을 눌러 시작하세요.
          </p>
          <button
            onClick={() => sync()}
            disabled={isSyncing}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? '데이터 수집 중...' : '탐험 시작하기'}
          </button>
        </div>
      </div>
    );
  }

  // 에러 처리
  if (categoriesError) {
    return (
      <div className="rounded-lg bg-white shadow-sm dark:bg-gray-800">
        <div className="p-8 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-red-500" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            데이터를 불러올 수 없습니다
          </h3>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            잠시 후 다시 시도해 주세요.
          </p>
          <button
            onClick={() => sync()}
            disabled={isSyncing}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          >
            <RefreshCw className={`h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} />
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-white shadow-sm dark:bg-gray-800">
      {/* 헤더 */}
      <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Compass className="h-5 w-5 text-blue-500" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Chain Sight
              </h2>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {companyName || symbol}와 연결된 종목 탐험
              </span>
            </div>
          </div>

          {/* 새로고침 버튼 */}
          <button
            onClick={() => sync()}
            disabled={isSyncing}
            className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
            title="관계 데이터 새로고침"
          >
            <RefreshCw className={`h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 카테고리 선택 */}
      <CategorySelector
        categories={categories}
        selectedId={selectedCategoryId}
        onSelect={setSelectedCategoryId}
        isLoading={isCategoriesLoading || isSyncing}
      />

      {/* 선택된 카테고리 콘텐츠 */}
      {selectedCategoryId && (
        <>
          {/* AI 인사이트 */}
          <AIInsightPanel
            insights={aiInsights}
            followUpQuestions={followUpQuestions}
            isLoading={isStocksLoading}
          />

          {/* 관련 종목 그리드 */}
          <RelatedStockGrid
            stocks={stocks}
            isLoading={isStocksLoading}
          />
        </>
      )}

      {/* 카테고리 미선택 안내 */}
      {!selectedCategoryId && !isCategoriesLoading && categories.length > 0 && (
        <div className="p-8 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            위 카테고리를 선택하여 관련 종목을 탐험해 보세요.
          </p>
        </div>
      )}
    </div>
  );
}
