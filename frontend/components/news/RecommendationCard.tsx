// Stock recommendation card component

'use client';

import React from 'react';
import Link from 'next/link';
import { TrendingUp, TrendingDown, MessageSquare, Star, ArrowRight } from 'lucide-react';
import { StockRecommendation } from '@/types/news';

interface RecommendationCardProps {
  recommendation: StockRecommendation;
  rank: number;
}

// Score color based on value
function getScoreColor(score: number): string {
  if (score >= 0.8) return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30';
  if (score >= 0.6) return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30';
  if (score >= 0.4) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/30';
  return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800';
}

// Sentiment icon
function SentimentIndicator({ sentiment }: { sentiment: number | null }) {
  if (sentiment === null) return null;

  const isPositive = sentiment > 0.1;
  const isNegative = sentiment < -0.1;

  if (isPositive) {
    return (
      <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
        <TrendingUp className="w-3 h-3" />
        <span className="text-xs">+{(sentiment * 100).toFixed(0)}%</span>
      </div>
    );
  }

  if (isNegative) {
    return (
      <div className="flex items-center gap-1 text-red-600 dark:text-red-400">
        <TrendingDown className="w-3 h-3" />
        <span className="text-xs">{(sentiment * 100).toFixed(0)}%</span>
      </div>
    );
  }

  return (
    <span className="text-xs text-gray-500 dark:text-gray-400">중립</span>
  );
}

export default function RecommendationCard({ recommendation, rank }: RecommendationCardProps) {
  const scoreColor = getScoreColor(recommendation.score);

  return (
    <Link
      href={`/stocks/${recommendation.symbol}`}
      className="block bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all p-4"
    >
      <div className="flex items-start justify-between gap-3">
        {/* Rank & Symbol */}
        <div className="flex items-center gap-3">
          {/* Rank badge */}
          <div className={`
            w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
            ${rank <= 3
              ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
            }
          `}>
            {rank}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-gray-900 dark:text-white">
                {recommendation.symbol}
              </span>
              {rank <= 3 && (
                <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
              )}
            </div>
            {recommendation.company_name && (
              <p className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-[150px]">
                {recommendation.company_name}
              </p>
            )}
          </div>
        </div>

        {/* Score */}
        <div className={`px-3 py-1.5 rounded-lg ${scoreColor}`}>
          <span className="text-lg font-bold">
            {(recommendation.score * 100).toFixed(0)}
          </span>
          <span className="text-xs ml-0.5">점</span>
        </div>
      </div>

      {/* Reasons */}
      {recommendation.reasons && recommendation.reasons.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {recommendation.reasons.slice(0, 3).map((reason, index) => (
            <span
              key={index}
              className="px-2 py-0.5 text-xs bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded-full"
            >
              {reason}
            </span>
          ))}
          {recommendation.reasons.length > 3 && (
            <span className="text-xs text-gray-400">
              +{recommendation.reasons.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Stats */}
      <div className="mt-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-4">
          {/* Mention count */}
          <div className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
            <MessageSquare className="w-3 h-3" />
            <span>{recommendation.mention_count}회 언급</span>
          </div>

          {/* Sentiment */}
          <SentimentIndicator sentiment={recommendation.avg_sentiment} />
        </div>

        {/* View arrow */}
        <ArrowRight className="w-4 h-4 text-gray-400" />
      </div>
    </Link>
  );
}
