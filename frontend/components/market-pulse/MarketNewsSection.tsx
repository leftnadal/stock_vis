'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useMarketNews } from '@/hooks/useNews';
import {
  Loader2,
  Clock,
  Newspaper,
  ExternalLink,
  AlertCircle,
  RefreshCw,
  Globe,
  DollarSign,
  Bitcoin,
  GitMerge
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import type { MarketNewsCategory } from '@/types/news';

// 카테고리 설정
const NEWS_CATEGORIES: { id: MarketNewsCategory; label: string; icon: typeof Globe }[] = [
  { id: 'general', label: '일반', icon: Globe },
  { id: 'forex', label: '외환', icon: DollarSign },
  { id: 'crypto', label: '암호화폐', icon: Bitcoin },
  { id: 'merger', label: 'M&A', icon: GitMerge },
];

export function MarketNewsSection() {
  const [activeCategory, setActiveCategory] = useState<MarketNewsCategory>('general');
  const [refreshKey, setRefreshKey] = useState(0);

  const { data, isLoading, error, refetch, isFetching } = useMarketNews(
    activeCategory,
    15, // limit
    refreshKey > 0 // refresh on first manual trigger
  );

  const articles = data?.articles ?? [];

  const handleRefresh = async () => {
    setRefreshKey(prev => prev + 1);
    refetch();
  };

  // 시간 포맷팅
  const formatTime = (dateStr: string) => {
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: ko });
    } catch {
      return '';
    }
  };

  return (
    <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700">
      {/* 헤더 */}
      <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
              <Newspaper className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Market News
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                실시간 시장 뉴스
              </p>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isFetching}
            className={`
              flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200
              ${isFetching
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                : 'bg-purple-500 hover:bg-purple-600 text-white'
              }
            `}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            <span>{isFetching ? '로딩 중...' : '새로고침'}</span>
          </button>
        </div>
      </div>

      {/* 카테고리 탭 */}
      <div className="px-6 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center gap-1">
        {NEWS_CATEGORIES.map((cat) => {
          const isActive = activeCategory === cat.id;
          const Icon = cat.icon;

          return (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200
                ${isActive
                  ? 'bg-purple-500 text-white'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }
              `}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>

      {/* 뉴스 리스트 */}
      <div className="p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <Loader2 className="w-6 h-6 animate-spin text-gray-300 dark:text-gray-600 mx-auto mb-2" />
              <p className="text-xs text-gray-400 dark:text-gray-500">뉴스 로딩 중</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
              <p className="text-sm text-gray-900 dark:text-white mb-1">뉴스를 불러올 수 없습니다</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                새로고침 버튼을 눌러 다시 시도해주세요
              </p>
            </div>
          </div>
        ) : articles.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <Newspaper className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                뉴스가 없습니다
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                새로고침 버튼을 눌러 최신 뉴스를 가져오세요
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {articles.map((article) => (
              <a
                key={article.id}
                href={article.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex gap-4 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-600"
              >
                {/* 썸네일 */}
                {article.image_url ? (
                  <div className="flex-shrink-0 w-24 h-16 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
                    <img
                      src={article.image_url}
                      alt=""
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  </div>
                ) : (
                  <div className="flex-shrink-0 w-24 h-16 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                    <Newspaper className="w-6 h-6 text-gray-300 dark:text-gray-500" />
                  </div>
                )}

                {/* 콘텐츠 */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                    {article.title}
                    <ExternalLink className="inline-block w-3 h-3 ml-1 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </h3>

                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-1">
                    {article.summary}
                  </p>

                  <div className="flex items-center gap-2 mt-2 text-[10px] text-gray-400 dark:text-gray-500">
                    <span className="font-medium">{article.source}</span>
                    <span>•</span>
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>{formatTime(article.published_at)}</span>
                    </div>
                    {article.sentiment_score !== null && (
                      <>
                        <span>•</span>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${
                          article.sentiment_score > 0.1
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                            : article.sentiment_score < -0.1
                            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                            : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                        }`}>
                          {article.sentiment_score > 0.1 ? '긍정' : article.sentiment_score < -0.1 ? '부정' : '중립'}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
