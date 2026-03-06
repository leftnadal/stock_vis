'use client';

import React, { useState } from 'react';
import {
  Globe,
  Bitcoin,
  DollarSign,
  Handshake,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import NewsCard from './NewsCard';
import NewsDetailModal from './NewsDetailModal';
import { NewsListItem } from '@/types/news';

export type NewsCategoryType = 'general' | 'crypto' | 'forex' | 'merger';

interface NewsCategorySectionProps {
  category: NewsCategoryType;
  articles: NewsListItem[];
  initialCount?: number;
}

const CATEGORY_CONFIG: Record<
  NewsCategoryType,
  { label: string; icon: React.ElementType; color: string; bgColor: string; description: string }
> = {
  general: {
    label: 'General',
    icon: Globe,
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    description: '시장 전반 뉴스',
  },
  crypto: {
    label: 'Crypto',
    icon: Bitcoin,
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-100 dark:bg-orange-900/30',
    description: '암호화폐 뉴스',
  },
  forex: {
    label: 'Forex',
    icon: DollarSign,
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
    description: '외환 시장 뉴스',
  },
  merger: {
    label: 'M&A',
    icon: Handshake,
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
    description: '인수합병 뉴스',
  },
};

export default function NewsCategorySection({
  category,
  articles,
  initialCount = 4,
}: NewsCategorySectionProps) {
  const [expanded, setExpanded] = useState(false);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);

  const config = CATEGORY_CONFIG[category];
  const Icon = config.icon;
  const displayArticles = expanded ? articles : articles.slice(0, initialCount);
  const hasMore = articles.length > initialCount;

  return (
    <section>
      {/* Category Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className={`p-1.5 rounded-lg ${config.bgColor}`}>
            <Icon className={`w-4 h-4 ${config.color}`} />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-900 dark:text-white">
              {config.label}
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {config.description}
            </p>
          </div>
          <span className={`ml-1 px-2 py-0.5 text-xs font-medium rounded-full ${config.bgColor} ${config.color}`}>
            {articles.length}
          </span>
        </div>
      </div>

      {/* Articles Grid */}
      {articles.length > 0 ? (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {displayArticles.map((article) => (
              <NewsCard
                key={article.id}
                article={article}
                onClick={() => setSelectedArticleId(article.id)}
              />
            ))}
          </div>

          {/* Expand/Collapse */}
          {hasMore && (
            <div className="flex justify-center mt-3">
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1.5 px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                {expanded ? (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    접기
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    {articles.length - initialCount}개 더 보기
                  </>
                )}
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="py-8 text-center bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-200 dark:border-gray-700">
          <Icon className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {config.label} 카테고리 뉴스가 아직 수집되지 않았습니다
          </p>
        </div>
      )}

      {/* Detail Modal */}
      <NewsDetailModal
        newsId={selectedArticleId}
        onClose={() => setSelectedArticleId(null)}
      />
    </section>
  );
}
