'use client';

import { Lightbulb, MessageCircle } from 'lucide-react';

interface AIInsightPanelProps {
  insights: string | null | undefined;
  followUpQuestions?: string[];
  isLoading?: boolean;
  onQuestionClick?: (question: string) => void;
}

/**
 * AI 인사이트 패널 컴포넌트
 *
 * AI가 생성한 인사이트와 후속 질문을 표시합니다.
 */
export default function AIInsightPanel({
  insights,
  followUpQuestions = [],
  isLoading = false,
  onQuestionClick,
}: AIInsightPanelProps) {
  if (isLoading) {
    return (
      <div className="mx-4 mb-4 rounded-lg border border-blue-100 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-900/30">
        <div className="flex items-start gap-3">
          <div className="h-5 w-5 animate-pulse rounded bg-blue-200 dark:bg-blue-700" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-3/4 animate-pulse rounded bg-blue-200 dark:bg-blue-700" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-blue-200 dark:bg-blue-700" />
          </div>
        </div>
      </div>
    );
  }

  if (!insights) {
    return null;
  }

  return (
    <div className="mx-4 mb-4 space-y-3">
      {/* 인사이트 */}
      <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-900/30">
        <div className="flex items-start gap-3">
          <Lightbulb className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-500" />
          <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
            {insights}
          </p>
        </div>
      </div>

      {/* 후속 질문 */}
      {followUpQuestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <MessageCircle className="h-4 w-4 text-gray-400" />
          {followUpQuestions.map((question, index) => (
            <button
              key={index}
              onClick={() => onQuestionClick?.(question)}
              className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-blue-500 dark:hover:bg-blue-900/30 dark:hover:text-blue-400"
            >
              {question}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
