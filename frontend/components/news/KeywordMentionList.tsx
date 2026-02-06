// Keyword mention list component

'use client';

import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import { ExternalLink, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { KeywordMention } from '@/types/news';

interface KeywordMentionListProps {
  mentions: KeywordMention[];
  maxItems?: number;
  showAll?: boolean;
}

// Sentiment icon for keyword
function SentimentIcon({ sentiment }: { sentiment: 'positive' | 'negative' | 'neutral' }) {
  switch (sentiment) {
    case 'positive':
      return <TrendingUp className="w-3 h-3 text-green-500" />;
    case 'negative':
      return <TrendingDown className="w-3 h-3 text-red-500" />;
    default:
      return <Minus className="w-3 h-3 text-gray-400" />;
  }
}

// Sentiment background color for keyword badge
function getSentimentBgColor(sentiment: 'positive' | 'negative' | 'neutral'): string {
  switch (sentiment) {
    case 'positive':
      return 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300';
    case 'negative':
      return 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300';
    default:
      return 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300';
  }
}

// Format relative time
function formatTime(isoDate: string): string {
  try {
    return formatDistanceToNow(new Date(isoDate), { addSuffix: true, locale: ko });
  } catch {
    return '';
  }
}

export default function KeywordMentionList({
  mentions,
  maxItems = 3,
  showAll = false,
}: KeywordMentionListProps) {
  const displayMentions = showAll ? mentions : mentions.slice(0, maxItems);

  if (mentions.length === 0) {
    return (
      <div className="text-sm text-gray-400 dark:text-gray-500 py-2">
        관련 키워드 없음
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {displayMentions.map((mention, index) => (
        <div key={`${mention.keyword}-${index}`} className="space-y-1">
          {/* Keyword badge */}
          <div className="flex items-center gap-2">
            <SentimentIcon sentiment={mention.sentiment} />
            <span
              className={`px-2 py-0.5 text-xs font-medium rounded-full ${getSentimentBgColor(mention.sentiment)}`}
            >
              {mention.keyword}
            </span>
          </div>

          {/* News headline */}
          <div className="ml-5 pl-2 border-l-2 border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
              &ldquo;{mention.news_headline}&rdquo;
            </p>
            <div className="flex items-center gap-2 mt-1 text-xs text-gray-400 dark:text-gray-500">
              <span>{mention.news_source}</span>
              <span>&middot;</span>
              <span>{formatTime(mention.published_at)}</span>
            </div>
          </div>
        </div>
      ))}

      {/* Show more indicator */}
      {!showAll && mentions.length > maxItems && (
        <div className="text-xs text-gray-400 dark:text-gray-500 ml-5">
          +{mentions.length - maxItems}개 더 보기
        </div>
      )}
    </div>
  );
}
