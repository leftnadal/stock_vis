// Sentiment badge component for displaying sentiment scores

import React from 'react';

export interface SentimentBadgeProps {
  score: number | null;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export default function SentimentBadge({
  score,
  size = 'md',
  showLabel = true,
}: SentimentBadgeProps) {
  // Handle null or undefined scores
  if (score === null || score === undefined) {
    return (
      <span
        className={`inline-flex items-center rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 ${getSizeClasses(size)}`}
      >
        중립
      </span>
    );
  }

  // Determine sentiment level and styling
  const sentiment = getSentimentLevel(score);

  return (
    <span
      className={`inline-flex items-center rounded-full ${sentiment.bgColor} ${sentiment.textColor} ${getSizeClasses(size)}`}
    >
      {showLabel && sentiment.label}
    </span>
  );
}

// Helper function to get size-specific classes
function getSizeClasses(size: 'sm' | 'md' | 'lg'): string {
  switch (size) {
    case 'sm':
      return 'px-2 py-0.5 text-xs font-medium';
    case 'md':
      return 'px-2.5 py-1 text-sm font-medium';
    case 'lg':
      return 'px-3 py-1.5 text-base font-semibold';
    default:
      return 'px-2.5 py-1 text-sm font-medium';
  }
}

// Helper function to determine sentiment level
function getSentimentLevel(score: number) {
  if (score >= 0.3) {
    return {
      label: '매우 긍정',
      bgColor: 'bg-green-600',
      textColor: 'text-white',
    };
  } else if (score >= 0.1) {
    return {
      label: '긍정',
      bgColor: 'bg-green-100 dark:bg-green-900/30',
      textColor: 'text-green-700 dark:text-green-400',
    };
  } else if (score >= -0.1) {
    return {
      label: '중립',
      bgColor: 'bg-gray-100 dark:bg-gray-700',
      textColor: 'text-gray-600 dark:text-gray-400',
    };
  } else if (score >= -0.3) {
    return {
      label: '부정',
      bgColor: 'bg-red-100 dark:bg-red-900/30',
      textColor: 'text-red-700 dark:text-red-400',
    };
  } else {
    return {
      label: '매우 부정',
      bgColor: 'bg-red-600',
      textColor: 'text-white',
    };
  }
}

// Export utility function for external use
export { getSentimentLevel };
