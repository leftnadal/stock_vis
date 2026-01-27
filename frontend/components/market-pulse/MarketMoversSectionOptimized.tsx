'use client';

import { useState, useMemo } from 'react';
import { useMarketMovers, useSyncMarketMovers } from '@/hooks/useMarketMovers';
import { useBatchKeywords } from '@/hooks/useKeywords';
import { MoverCardWithBatchKeywords } from './MoverCardWithBatchKeywords';
import { MOVER_TABS, type MoverType } from '@/types/market';
import { Loader2, Clock, TrendingUp, TrendingDown, BarChart3, AlertCircle, RefreshCw, CheckCircle, Sparkles } from 'lucide-react';

// 탭 아이콘 매핑
const TAB_ICONS: Record<MoverType, typeof TrendingUp> = {
  gainers: TrendingUp,
  losers: TrendingDown,
  actives: BarChart3,
};

/**
 * MarketMoversSection 배치 최적화 버전
 * - useBatchKeywords()로 모든 종목의 키워드를 한 번에 조회 (N+1 쿼리 방지)
 * - MoverCardWithBatchKeywords에 배치 데이터 전달
 */
export function MarketMoversSectionOptimized() {
  const [activeTab, setActiveTab] = useState<MoverType>('gainers');
  const { data, isLoading, error, dataUpdatedAt } = useMarketMovers(activeTab);
  const syncMutation = useSyncMarketMovers();

  const activeConfig = MOVER_TABS.find(tab => tab.id === activeTab)!;
  const movers = data?.data?.movers ?? [];
  const date = data?.data?.date;

  // 배치 키워드 조회 (모든 종목 심볼)
  const symbols = useMemo(() => movers.map(m => m.symbol), [movers]);
  const {
    data: batchKeywordsData,
    isLoading: keywordsLoading,
    error: keywordsError,
  } = useBatchKeywords(symbols, date);

  const keywordsMap = batchKeywordsData?.data ?? {};

  const handleSync = () => {
    syncMutation.mutate(undefined);
  };

  // 날짜 포맷팅
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  };

  return (
    <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700">
      {/* 헤더 */}
      <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Market Movers
              </h2>
              {keywordsLoading && (
                <span className="flex items-center gap-1 text-[10px] text-blue-500 dark:text-blue-400">
                  <Sparkles className="w-3 h-3 animate-pulse" />
                  AI 분석 중
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Clock className="w-3 h-3 text-gray-400" />
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {formatDate(date) || '로딩 중...'} 기준
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {dataUpdatedAt && (
              <span className="text-[10px] text-gray-400 dark:text-gray-500">
                {new Date(dataUpdatedAt).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })} 갱신
              </span>
            )}
            {syncMutation.isSuccess && (
              <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                <CheckCircle className="w-3.5 h-3.5" />
                완료
              </span>
            )}
            {syncMutation.isError && (
              <span className="flex items-center gap-1 text-xs text-red-500">
                <AlertCircle className="w-3.5 h-3.5" />
                실패
              </span>
            )}
            <button
              onClick={handleSync}
              disabled={syncMutation.isPending}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200
                ${syncMutation.isPending
                  ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
                }
              `}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
              <span>{syncMutation.isPending ? '업데이트 중...' : '업데이트'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 탭 네비게이션 */}
      <div className="px-6 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center gap-1">
        {MOVER_TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = TAB_ICONS[tab.id];

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200
                ${isActive
                  ? tab.id === 'gainers'
                    ? 'bg-emerald-500 text-white'
                    : tab.id === 'losers'
                    ? 'bg-red-500 text-white'
                    : 'bg-amber-500 text-white'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }
              `}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.labelKo}</span>
            </button>
          );
        })}
      </div>

      {/* 종목 리스트 */}
      <div className="p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <Loader2 className="w-6 h-6 animate-spin text-gray-300 dark:text-gray-600 mx-auto mb-2" />
              <p className="text-xs text-gray-400 dark:text-gray-500">데이터 로딩 중</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
              <p className="text-sm text-gray-900 dark:text-white mb-1">데이터를 불러올 수 없습니다</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                잠시 후 다시 시도해주세요
              </p>
            </div>
          </div>
        ) : movers.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <BarChart3 className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                데이터가 없습니다
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {movers.map((mover) => (
              <MoverCardWithBatchKeywords
                key={mover.symbol}
                mover={mover}
                keywords={keywordsMap[mover.symbol]}
                keywordsLoading={keywordsLoading}
                keywordsError={keywordsError}
                showKeywords={true}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
