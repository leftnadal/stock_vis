// News list component with auto-fetch and loading UX

'use client';

import React, { useState, useEffect } from 'react';
import { RefreshCw, Newspaper, AlertCircle, Loader2 } from 'lucide-react';
import NewsCard from './NewsCard';
import { newsService } from '@/services/newsService';
import { StockNewsResponse } from '@/types/news';

export interface NewsListProps {
  symbol: string;
  onArticleClick: (articleId: string) => void;
}

type PeriodType = 1 | 7 | 30;

export default function NewsList({ symbol, onArticleClick }: NewsListProps) {
  const [period, setPeriod] = useState<PeriodType>(7);
  const [data, setData] = useState<StockNewsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('');

  // 초기 로드 및 기간 변경 시 데이터 가져오기
  useEffect(() => {
    fetchNews(false);
  }, [symbol, period]);

  const fetchNews = async (forceRefresh: boolean) => {
    try {
      if (forceRefresh) {
        setIsRefreshing(true);
        setStatusMessage('Finnhub API에서 최신 뉴스를 가져오는 중...');
      } else {
        setIsLoading(true);
        setStatusMessage('뉴스 데이터를 확인하는 중...');
      }
      setError(null);

      // 먼저 캐시된 데이터 확인
      const cachedData = await newsService.getStockNews(symbol, period, false);

      // 캐시된 데이터가 있으면 먼저 표시
      if (cachedData && cachedData.articles && cachedData.articles.length > 0) {
        setData(cachedData);
        setIsLoading(false);

        // 강제 새로고침이 아니면 여기서 종료
        if (!forceRefresh) {
          setStatusMessage('');
          return;
        }
      }

      // 데이터가 없거나 강제 새로고침인 경우 API에서 새로 가져오기
      if (!cachedData || cachedData.articles.length === 0 || forceRefresh) {
        setStatusMessage('Finnhub API에서 뉴스를 수집하는 중...');

        const freshData = await newsService.getStockNews(symbol, period, true);
        setData(freshData);

        if (freshData.articles.length === 0) {
          setStatusMessage('해당 기간에 뉴스가 없습니다');
        } else {
          setStatusMessage(`${freshData.count}개의 뉴스를 가져왔습니다`);
        }

        // 3초 후 상태 메시지 제거
        setTimeout(() => setStatusMessage(''), 3000);
      }
    } catch (err) {
      console.error('Failed to fetch news:', err);
      setError(err instanceof Error ? err : new Error('뉴스를 불러오는데 실패했습니다'));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleRefresh = () => {
    fetchNews(true);
  };

  const handlePeriodChange = (newPeriod: PeriodType) => {
    setPeriod(newPeriod);
  };

  // Period selector buttons
  const periods: { value: PeriodType; label: string }[] = [
    { value: 1, label: '오늘' },
    { value: 7, label: '1주일' },
    { value: 30, label: '1개월' },
  ];

  return (
    <div className="space-y-4">
      {/* Header: Period Selector + Refresh Button */}
      <div className="flex justify-between items-center">
        {/* Period Selector */}
        <div className="flex space-x-2">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => handlePeriodChange(p.value)}
              disabled={isLoading || isRefreshing}
              className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                period === p.value
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Refresh Button */}
        <button
          onClick={handleRefresh}
          disabled={isLoading || isRefreshing}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          새로고침
        </button>
      </div>

      {/* Status Message (업데이트 중 표시) */}
      {(isLoading || isRefreshing || statusMessage) && (
        <div className={`flex items-center gap-3 p-4 rounded-lg ${
          isLoading || isRefreshing
            ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
            : 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
        }`}>
          {(isLoading || isRefreshing) && (
            <Loader2 className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-spin" />
          )}
          <div>
            <p className={`text-sm font-medium ${
              isLoading || isRefreshing
                ? 'text-blue-700 dark:text-blue-300'
                : 'text-green-700 dark:text-green-300'
            }`}>
              {isLoading ? '뉴스 데이터 로딩 중...' : isRefreshing ? 'API에서 새 뉴스 수집 중...' : statusMessage}
            </p>
            {isRefreshing && (
              <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                Finnhub API Rate Limit: 60회/분
              </p>
            )}
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-700 dark:text-red-400 font-medium mb-2">
            뉴스를 불러오는 중 오류가 발생했습니다
          </p>
          <p className="text-sm text-red-600 dark:text-red-500 mb-4">
            {error.message}
          </p>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            다시 시도
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && !data && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <div className="flex gap-4">
                  <div className="w-32 h-24 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                  <div className="flex-1 space-y-3">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                    <div className="flex gap-2">
                      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && data && data.articles.length === 0 && (
        <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center">
          <Newspaper className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400 font-medium mb-2">
            선택한 기간에 뉴스가 없습니다
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mb-4">
            새로고침 버튼을 눌러 최신 뉴스를 가져와보세요
          </p>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {isRefreshing ? (
              <>
                <Loader2 className="w-4 h-4 inline mr-2 animate-spin" />
                수집 중...
              </>
            ) : (
              '뉴스 가져오기'
            )}
          </button>
        </div>
      )}

      {/* News Articles List */}
      {!isLoading && !error && data && data.articles.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            총 <span className="font-semibold text-gray-900 dark:text-white">{data.count}</span>개의
            뉴스
          </p>

          {data.articles.map((article) => (
            <NewsCard
              key={article.id}
              article={article}
              onClick={() => onArticleClick(article.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
