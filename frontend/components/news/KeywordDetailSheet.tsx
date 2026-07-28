'use client';

import React, { useState, useEffect, useRef } from 'react';
import { ExternalLink, Loader2, Newspaper, AlertCircle, TrendingUp, TrendingDown, Minus, ChevronLeft, ChevronRight } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import { BottomSheet } from '@/components/common/BottomSheet';
import { useKeywordDetail } from '@/hooks/useNews';
import { DailyKeyword } from '@/types/news';

interface KeywordDetailSheetProps {
  isOpen: boolean;
  onClose: () => void;
  date: string;
  initialIndex: number;
  keywords: DailyKeyword[];
}

const SENTIMENT_LABEL: Record<string, string> = {
  positive: '긍정',
  negative: '부정',
  neutral: '중립',
};

const SENTIMENT_COLOR: Record<string, string> = {
  positive: 'text-green-400',
  negative: 'text-red-400',
  neutral: 'text-gray-400',
};

const STRIP_STYLES: Record<string, { base: string; active: string }> = {
  positive: {
    base: 'bg-green-900/30 border-green-700/50 text-green-300',
    active: 'ring-2 ring-green-400 bg-green-900/50',
  },
  negative: {
    base: 'bg-red-900/30 border-red-700/50 text-red-300',
    active: 'ring-2 ring-red-400 bg-red-900/50',
  },
  neutral: {
    base: 'bg-gray-800 border-gray-600 text-gray-300',
    active: 'ring-2 ring-gray-400 bg-gray-700',
  },
};

const SENTIMENT_ICON: Record<string, React.ElementType> = {
  positive: TrendingUp,
  negative: TrendingDown,
  neutral: Minus,
};

export default function KeywordDetailSheet({
  isOpen,
  onClose,
  date,
  initialIndex,
  keywords,
}: KeywordDetailSheetProps) {
  const [activeIndex, setActiveIndex] = useState(initialIndex);
  const pillRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const updateScrollState = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 0);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  };

  useEffect(() => {
    setActiveIndex(initialIndex);
  }, [initialIndex]);

  useEffect(() => {
    pillRefs.current[activeIndex]?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
      inline: 'center',
    });
    // 스크롤 후 상태 업데이트
    setTimeout(updateScrollState, 300);
  }, [activeIndex]);

  useEffect(() => {
    updateScrollState();
  }, [keywords]);

  const scrollStrip = (dir: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: dir === 'left' ? -150 : 150, behavior: 'smooth' });
    setTimeout(updateScrollState, 300);
  };

  const { data, isLoading, isPlaceholderData, error } = useKeywordDetail(
    isOpen ? date : null,
    isOpen ? activeIndex : null,
  );

  const activeKeyword = keywords[activeIndex];

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose}>
      {/* Keyword Strip */}
      {keywords.length > 0 && (
        <div className="sticky top-0 z-10 bg-gray-900 pt-1 pb-3 mb-3
                        border-b border-gray-800 -mx-5 px-5">
          <div className="relative">
            {/* Left fade + arrow */}
            {canScrollLeft && (
              <button
                onClick={() => scrollStrip('left')}
                className="absolute left-0 top-0 bottom-0 z-10 flex items-center
                           bg-gradient-to-r from-gray-900 via-gray-900/80 to-transparent pl-0.5 pr-3"
              >
                <ChevronLeft className="w-4 h-4 text-gray-400" />
              </button>
            )}

            <div
              ref={scrollRef}
              onScroll={updateScrollState}
              className="flex gap-2 overflow-x-auto scrollbar-hide"
            >
              {keywords.map((kw, idx) => {
                const style = STRIP_STYLES[kw.sentiment] || STRIP_STYLES.neutral;
                const Icon = SENTIMENT_ICON[kw.sentiment] || Minus;
                const isActive = idx === activeIndex;

                return (
                  <button
                    key={idx}
                    ref={(el) => { pillRefs.current[idx] = el; }}
                    onClick={() => setActiveIndex(idx)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium
                               whitespace-nowrap flex-shrink-0 transition-all
                               ${style.base} ${isActive ? style.active : 'opacity-70 hover:opacity-100'}`}
                  >
                    <Icon className="w-3 h-3" />
                    {kw.text}
                  </button>
                );
              })}
            </div>

            {/* Right fade + arrow */}
            {canScrollRight && (
              <button
                onClick={() => scrollStrip('right')}
                className="absolute right-0 top-0 bottom-0 z-10 flex items-center
                           bg-gradient-to-l from-gray-900 via-gray-900/80 to-transparent pr-0.5 pl-3"
              >
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Active keyword title */}
      {activeKeyword && (
        <h3 className="text-white text-base font-medium mb-3">{activeKeyword.text}</h3>
      )}

      {/* Loading overlay for placeholder data */}
      {isPlaceholderData && (
        <div className="flex items-center gap-2 mb-3 text-xs text-gray-400">
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>전환 중...</span>
        </div>
      )}

      {/* Loading */}
      {isLoading && !isPlaceholderData && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
          <span className="ml-2 text-sm text-gray-400">분석 중...</span>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="flex items-center gap-2 py-4 text-sm text-red-400">
          <AlertCircle className="w-4 h-4" />
          <span>데이터를 불러올 수 없습니다</span>
        </div>
      )}

      {/* Content */}
      {data && !isLoading && (
        <div className="space-y-4">
          {/* Sentiment badge */}
          <div className="flex items-center gap-2">
            <span className={`text-xs font-medium ${SENTIMENT_COLOR[data.sentiment] || SENTIMENT_COLOR.neutral}`}>
              {SENTIMENT_LABEL[data.sentiment] || '중립'}
            </span>
            {data.related_symbols.length > 0 && (
              <span className="text-xs text-gray-500">
                관련: {data.related_symbols.join(', ')}
              </span>
            )}
          </div>

          {/* Analysis (null이면 숨김) */}
          {data.analysis && (
            <div className="p-3 bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-line">
                {data.analysis}
              </p>
            </div>
          )}

          {/* Articles */}
          {data.articles.length > 0 ? (
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                관련 기사 ({data.articles.length})
              </h4>
              <div className="space-y-1.5">
                {data.articles.map((article) => (
                  <a
                    key={article.id}
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-2 p-2.5 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors group"
                  >
                    <Newspaper className="w-4 h-4 text-gray-500 mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-200 line-clamp-2 group-hover:text-white transition-colors">
                        {article.title}
                      </p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                        <span>{article.source}</span>
                        {article.published_at && (
                          <>
                            <span>·</span>
                            <span>
                              {formatDistanceToNow(new Date(article.published_at), {
                                addSuffix: true,
                                locale: ko,
                              })}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <ExternalLink className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-400 shrink-0 mt-0.5" />
                  </a>
                ))}
              </div>
            </div>
          ) : (
            <div className="py-4 text-center text-sm text-gray-500">
              관련 기사를 찾을 수 없습니다
            </div>
          )}
        </div>
      )}
    </BottomSheet>
  );
}
