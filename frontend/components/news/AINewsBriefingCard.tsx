'use client';

import React, { useState } from 'react';
import {
  Sparkles,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Minus,
  Newspaper,
  BarChart3,
} from 'lucide-react';
import Link from 'next/link';
import { useMarketFeed } from '@/hooks/useNews';
import { BriefingKeyword } from '@/types/news';

const SENTIMENT_CONFIG = {
  positive: {
    color: 'text-green-600 dark:text-green-400',
    bg: 'bg-green-500',
    barBg: 'bg-green-200 dark:bg-green-900',
    icon: TrendingUp,
    label: '긍정',
  },
  negative: {
    color: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-500',
    barBg: 'bg-red-200 dark:bg-red-900',
    icon: TrendingDown,
    label: '부정',
  },
  neutral: {
    color: 'text-yellow-600 dark:text-yellow-400',
    bg: 'bg-yellow-500',
    barBg: 'bg-yellow-200 dark:bg-yellow-900',
    icon: Minus,
    label: '중립',
  },
};

function KeywordItem({ keyword, rank }: { keyword: BriefingKeyword; rank: number }) {
  const [expanded, setExpanded] = useState(rank <= 2);
  const sentiment = keyword.sentiment || 'neutral';
  const config = SENTIMENT_CONFIG[sentiment];
  const Icon = config.icon;
  const importance = keyword.importance || 0.5;

  return (
    <div className="py-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
      {/* 키워드 헤더 */}
      <div className="flex items-start gap-3">
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-500 dark:text-gray-400">
          {rank}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-sm text-gray-900 dark:text-white">
              {keyword.text}
            </span>
            <div className={`flex items-center gap-1 text-xs ${config.color}`}>
              <Icon className="w-3 h-3" />
              <span>{config.label}</span>
            </div>
          </div>

          {/* Importance bar */}
          <div className={`h-1.5 rounded-full ${config.barBg} mb-2 w-full max-w-[200px]`}>
            <div
              className={`h-1.5 rounded-full ${config.bg} transition-all`}
              style={{ width: `${Math.round(importance * 100)}%` }}
            />
          </div>

          {/* Reason */}
          {keyword.reason && (
            <p className="text-xs text-gray-600 dark:text-gray-300 mb-2 leading-relaxed">
              {keyword.reason}
            </p>
          )}

          {/* Related symbols + news count */}
          <div className="flex items-center gap-2 flex-wrap mb-1">
            {keyword.related_symbols?.map((symbol) => (
              <Link
                key={symbol}
                href={`/stocks/${symbol}`}
                className="text-xs px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
              >
                {symbol}
              </Link>
            ))}
            {keyword.news_count > 0 && (
              <span className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1">
                <Newspaper className="w-3 h-3" />
                {keyword.news_count}건
              </span>
            )}
          </div>

          {/* Headlines (expandable) */}
          {keyword.headlines && keyword.headlines.length > 0 && (
            <>
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex items-center gap-1 mt-1"
              >
                {expanded ? (
                  <ChevronUp className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
                헤드라인 {expanded ? '접기' : '보기'}
              </button>
              {expanded && (
                <div className="mt-1.5 pl-2 border-l-2 border-gray-200 dark:border-gray-600 space-y-1">
                  {keyword.headlines.map((h, i) => (
                    <a
                      key={i}
                      href={h.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start gap-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3 mt-0.5 flex-shrink-0" />
                      <span className="line-clamp-1">{h.title}</span>
                    </a>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function BriefingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex gap-3 py-3">
          <div className="w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-700" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32" />
            <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded w-48" />
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-64" />
            <div className="flex gap-2">
              <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-12" />
              <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-12" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AINewsBriefingCard() {
  const { data, isLoading, error } = useMarketFeed();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden lg:col-span-2">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/10 dark:to-blue-900/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                AI가 분석한 오늘의 뉴스 키워드
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {data?.date || ''} | 분석 뉴스 {data?.briefing?.total_news_count || 0}건
              </p>
            </div>
          </div>
        </div>

        {/* Fallback notice */}
        {data?.is_fallback && data.fallback_message && (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
            <AlertCircle className="w-3 h-3" />
            <span>{data.fallback_message}</span>
          </div>
        )}
      </div>

      {/* Keywords Content */}
      <div className="px-4 py-2">
        {isLoading && <BriefingSkeleton />}

        {error && !isLoading && (
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 py-4">
            <AlertCircle className="w-4 h-4" />
            <span>뉴스 브리핑을 불러올 수 없습니다</span>
          </div>
        )}

        {data && !isLoading && data.briefing.keywords.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-full mb-3">
              <Newspaper className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              시장 데이터가 다음 거래일 이후 제공됩니다
            </p>
          </div>
        )}

        {data && !isLoading && data.briefing.keywords.length > 0 && (
          <div>
            {data.briefing.keywords.map((kw, index) => (
              <KeywordItem key={index} keyword={kw} rank={index + 1} />
            ))}
          </div>
        )}
      </div>

      {/* Market Context */}
      {data &&
        !isLoading &&
        (data.market_context.top_sectors.length > 0 ||
          data.market_context.hot_movers.length > 0) && (
          <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <div className="flex items-center gap-1.5 mb-2">
              <BarChart3 className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                시장 컨텍스트
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {data.market_context.top_sectors.slice(0, 4).map((sector) => (
                <span
                  key={sector.name}
                  className={`text-xs px-2 py-1 rounded-full ${
                    sector.return_pct >= 0
                      ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                      : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                  }`}
                >
                  {sector.name} {sector.return_pct >= 0 ? '+' : ''}
                  {sector.return_pct.toFixed(1)}%
                </span>
              ))}
              {data.market_context.hot_movers.slice(0, 3).map((mover) => (
                <Link
                  key={mover.symbol}
                  href={`/stocks/${mover.symbol}`}
                  className={`text-xs px-2 py-1 rounded-full ${
                    mover.change_percent >= 0
                      ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                      : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                  } hover:opacity-80 transition-opacity`}
                >
                  {mover.symbol} {mover.change_percent >= 0 ? '+' : ''}
                  {mover.change_percent.toFixed(1)}%
                </Link>
              ))}
            </div>
          </div>
        )}

      {/* Footer */}
      {data?.briefing?.llm_model && (
        <div className="px-4 py-2 border-t border-gray-100 dark:border-gray-700 text-right">
          <span className="text-[10px] text-gray-400">{data.briefing.llm_model}</span>
        </div>
      )}
    </div>
  );
}
