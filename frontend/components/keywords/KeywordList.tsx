'use client';

import { memo, useMemo } from 'react';
import { KeywordTag } from './KeywordTag';
import type { Keyword } from '@/types/keyword';
import { KeywordCategory } from '@/types/keyword';
import { Loader2, AlertCircle, Sparkles } from 'lucide-react';

interface KeywordListProps {
  keywords: Keyword[] | string[];  // 문자열 배열도 지원
  isLoading?: boolean;
  error?: Error | null;
  onKeywordClick?: (keyword: Keyword) => void;
  maxVisible?: number;
  showConfidence?: boolean;
  emptyMessage?: string;
  layout?: 'horizontal' | 'vertical';
  size?: 'sm' | 'md';
}

/**
 * 문자열 배열을 Keyword 객체 배열로 변환
 */
function normalizeKeywords(keywords: Keyword[] | string[]): Keyword[] {
  if (!keywords || keywords.length === 0) return [];

  // 이미 Keyword 객체 배열인 경우
  if (typeof keywords[0] === 'object' && 'text' in keywords[0]) {
    return keywords as Keyword[];
  }

  // 문자열 배열인 경우 Keyword 객체로 변환
  return (keywords as string[]).map((text, index) => ({
    id: `keyword-${index}-${text.slice(0, 10)}`,
    text: text,
    category: KeywordCategory.CATALYST,  // 기본 카테고리
    confidence: 0.8,  // 기본 신뢰도
  }));
}

export const KeywordList = memo(function KeywordList({
  keywords,
  isLoading = false,
  error = null,
  onKeywordClick,
  maxVisible,
  showConfidence = false,
  emptyMessage = '키워드가 없습니다',
  layout = 'horizontal',
  size = 'sm',
}: KeywordListProps) {
  // 로딩 상태
  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 py-1">
        <Loader2 className="w-3 h-3 animate-spin text-gray-300 dark:text-gray-600" />
        <span className="text-[10px] text-gray-400 dark:text-gray-500">
          AI 분석 중...
        </span>
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <div className="flex items-center gap-1.5 py-1">
        <AlertCircle className="w-3 h-3 text-red-400" />
        <span className="text-[10px] text-red-500 dark:text-red-400">
          키워드 로딩 실패
        </span>
      </div>
    );
  }

  // 키워드 정규화 (문자열 배열 → Keyword 객체 배열)
  const normalizedKeywords = useMemo(() => normalizeKeywords(keywords), [keywords]);

  // 빈 상태
  if (!normalizedKeywords || normalizedKeywords.length === 0) {
    return (
      <div className="flex items-center gap-1.5 py-1">
        <Sparkles className="w-3 h-3 text-gray-300 dark:text-gray-600" />
        <span className="text-[10px] text-gray-400 dark:text-gray-500">
          {emptyMessage}
        </span>
      </div>
    );
  }

  // 표시할 키워드 필터링
  const visibleKeywords = maxVisible ? normalizedKeywords.slice(0, maxVisible) : normalizedKeywords;
  const hiddenCount = normalizedKeywords.length - visibleKeywords.length;

  // 레이아웃 스타일
  const layoutClasses = {
    horizontal: 'flex flex-wrap items-center gap-1',
    vertical: 'flex flex-col gap-1',
  };

  return (
    <div className={layoutClasses[layout]}>
      {visibleKeywords.map((keyword) => (
        <KeywordTag
          key={keyword.id}
          keyword={keyword}
          onClick={onKeywordClick}
          showConfidence={showConfidence}
          size={size}
        />
      ))}

      {/* 더보기 표시 */}
      {hiddenCount > 0 && (
        <span
          className={`
            inline-flex items-center justify-center px-2 py-0.5 rounded-md
            bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400
            text-[10px] font-medium
          `}
        >
          +{hiddenCount}
        </span>
      )}
    </div>
  );
});
