// Stock insight card component (fact-based, no scores)

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronUp, Newspaper, BarChart3, ArrowRight, Info } from 'lucide-react';
import { StockInsight } from '@/types/news';
import SentimentBar from './SentimentBar';
import KeywordMentionList from './KeywordMentionList';
import MarketDataBadge from './MarketDataBadge';

interface StockInsightCardProps {
  insight: StockInsight;
  periodLabel?: string;
  defaultExpanded?: boolean;
}

export default function StockInsightCard({
  insight,
  periodLabel,
  defaultExpanded = false,
}: StockInsightCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const hasMarketData = insight.market_data && (
    insight.market_data.price_position ||
    insight.market_data.valuation ||
    insight.market_data.analyst_ratings
  );

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden transition-shadow hover:shadow-md">
      {/* Header - Always visible */}
      <div className="p-4">
        {/* Symbol and company name */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <Link
            href={`/stocks/${insight.symbol}`}
            className="flex items-center gap-2 group"
          >
            <span className="text-lg font-bold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
              {insight.symbol}
            </span>
            <ArrowRight className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
          {insight.company_name && (
            <span className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-[150px]">
              {insight.company_name}
            </span>
          )}
        </div>

        {/* News mention summary */}
        <div className="space-y-3">
          {/* Section label */}
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <Newspaper className="w-3.5 h-3.5" />
            <span>뉴스 언급 현황</span>
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {insight.total_news_count}건
            </span>
            {periodLabel && (
              <span
                className="inline-flex items-center gap-0.5 text-gray-400 dark:text-gray-500 cursor-help"
                title={`${periodLabel} 동안 수집된 뉴스에서 해당 종목이 언급된 횟수입니다`}
              >
                <Info className="w-3 h-3" />
                <span>{periodLabel}</span>
              </span>
            )}
          </div>

          {/* Sentiment distribution bar */}
          <SentimentBar
            distribution={insight.sentiment_distribution}
            size="sm"
          />
        </div>

        {/* Keywords preview (collapsed) */}
        {!expanded && insight.keyword_mentions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {insight.keyword_mentions.slice(0, 2).map((mention, index) => (
              <span
                key={`${mention.keyword}-${index}`}
                className={`px-2 py-0.5 text-xs rounded-full ${
                  mention.sentiment === 'positive'
                    ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                    : mention.sentiment === 'negative'
                    ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
                    : 'bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                }`}
              >
                {mention.keyword}
              </span>
            ))}
            {insight.keyword_mentions.length > 2 && (
              <span className="text-xs text-gray-400 dark:text-gray-500">
                +{insight.keyword_mentions.length - 2}
              </span>
            )}
          </div>
        )}

        {/* Market data preview (compact) */}
        {!expanded && hasMarketData && insight.market_data && (
          <div className="mt-3">
            <MarketDataBadge data={insight.market_data} compact />
          </div>
        )}
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-100 dark:border-gray-700 pt-4">
          {/* Keywords section */}
          {insight.keyword_mentions.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
                <span>관련 키워드</span>
              </div>
              <KeywordMentionList
                mentions={insight.keyword_mentions}
                showAll
              />
            </div>
          )}

          {/* Market data section */}
          {hasMarketData && insight.market_data && (
            <div>
              <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
                <BarChart3 className="w-3.5 h-3.5" />
                <span>시장 데이터</span>
              </div>
              <MarketDataBadge data={insight.market_data} />
            </div>
          )}
        </div>
      )}

      {/* Expand/Collapse toggle */}
      {(insight.keyword_mentions.length > 0 || hasMarketData) && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full py-2 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50 border-t border-gray-100 dark:border-gray-700 flex items-center justify-center gap-1 transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              접기
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              상세 보기
            </>
          )}
        </button>
      )}
    </div>
  );
}
