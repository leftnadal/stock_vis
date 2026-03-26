// Stock insight card component (fact-based, no scores)

'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronUp, Newspaper, BarChart3, ArrowRight, Info, MessageSquareText, X } from 'lucide-react';
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
  const [showKeywords, setShowKeywords] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  const hasMarketData = insight.market_data && (
    insight.market_data.price_position ||
    insight.market_data.valuation ||
    insight.market_data.analyst_ratings
  );

  const { positive, negative, neutral } = insight.sentiment_distribution;
  const dominantSentiment = positive >= negative && positive >= neutral
    ? 'positive'
    : negative >= positive && negative >= neutral
    ? 'negative'
    : 'neutral';

  const sentimentColor = dominantSentiment === 'positive'
    ? 'text-green-600 dark:text-green-400'
    : dominantSentiment === 'negative'
    ? 'text-red-600 dark:text-red-400'
    : 'text-gray-500 dark:text-gray-400';

  const hasKeywords = insight.keyword_mentions.length > 0;

  // Close overlay on outside click
  useEffect(() => {
    if (!showKeywords) return;
    function handleClick(e: MouseEvent) {
      if (overlayRef.current && !overlayRef.current.contains(e.target as Node)) {
        setShowKeywords(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showKeywords]);

  return (
    <div className="relative bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-visible transition-shadow hover:shadow-md">
      {/* Header - Always visible: symbol + company + news count */}
      <button
        onClick={() => {
          setExpanded(!expanded);
          if (expanded) setShowKeywords(false);
        }}
        className="w-full px-4 py-3 flex items-center justify-between gap-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors rounded-lg"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-base font-bold text-gray-900 dark:text-white flex-shrink-0">
            {insight.symbol}
          </span>
          {insight.company_name && (
            <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {insight.company_name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`text-xs font-medium ${sentimentColor}`}>
            {insight.total_news_count}건
          </span>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-3 space-y-3 border-t border-gray-100 dark:border-gray-700 pt-3">
          {/* News mention summary + link */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <Newspaper className="w-3.5 h-3.5" />
              <span>뉴스 언급</span>
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
            <Link
              href={`/stocks/${insight.symbol}`}
              className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              종목 보기
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {/* Sentiment distribution bar */}
          <SentimentBar
            distribution={insight.sentiment_distribution}
            size="sm"
          />

          {/* Market data badges (compact) */}
          {hasMarketData && insight.market_data && (
            <MarketDataBadge data={insight.market_data} compact />
          )}

          {/* Keywords toggle button */}
          {hasKeywords && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowKeywords(!showKeywords);
              }}
              className="w-full flex items-center justify-center gap-1.5 py-2 text-xs font-medium rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <MessageSquareText className="w-3.5 h-3.5" />
              {showKeywords ? '키워드 · 헤드라인 접기' : `키워드 · 헤드라인 보기 (${insight.keyword_mentions.length})`}
              {showKeywords ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
            </button>
          )}
        </div>
      )}

      {/* Keywords overlay */}
      {showKeywords && hasKeywords && (
        <div
          ref={overlayRef}
          className="absolute left-0 right-0 top-full mt-1 z-30 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-lg max-h-[360px] overflow-y-auto"
        >
          <div className="sticky top-0 z-10 flex items-center justify-between px-4 py-2.5 bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              {insight.symbol} 관련 키워드 · 헤드라인
            </span>
            <button
              onClick={() => setShowKeywords(false)}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="p-4">
            <KeywordMentionList
              mentions={insight.keyword_mentions}
              showAll
            />
          </div>
        </div>
      )}
    </div>
  );
}
