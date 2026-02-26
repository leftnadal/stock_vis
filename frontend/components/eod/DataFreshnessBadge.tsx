'use client';

import { AlertTriangle, CheckCircle } from 'lucide-react';

interface DataFreshnessBadgeProps {
  tradingDate: string;
  generatedAt: string;
  isStale: boolean; // Baker 판단값 (참고용)
}

/**
 * 프론트에서 is_stale을 동적으로 재판단합니다.
 * Baker는 bake 시점에 false로 굽지만, 다음 날 사용자가 접속하면
 * generated_at이 24시간 이상 경과했으므로 stale로 표시합니다.
 */
function computeIsStale(generatedAt: string, bakerIsStale: boolean): boolean {
  if (bakerIsStale) return true;
  try {
    const generated = new Date(generatedAt).getTime();
    const now = Date.now();
    const hours24 = 24 * 60 * 60 * 1000;
    return now - generated > hours24;
  } catch {
    return bakerIsStale;
  }
}

function formatKoreanDateTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

function formatTradingDate(dateStr: string): string {
  try {
    const [year, month, day] = dateStr.split('-');
    return `${year}년 ${month}월 ${day}일`;
  } catch {
    return dateStr;
  }
}

export function DataFreshnessBadge({
  tradingDate,
  generatedAt,
  isStale: bakerIsStale,
}: DataFreshnessBadgeProps) {
  const isStale = computeIsStale(generatedAt, bakerIsStale);

  if (isStale) {
    return (
      <div className="mb-3 flex items-center gap-2 px-4 py-2.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
        <AlertTriangle className="w-4 h-4 text-amber-500 dark:text-amber-400 flex-shrink-0" />
        <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2 min-w-0">
          <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
            어제 데이터입니다
          </span>
          <span className="text-xs text-amber-600 dark:text-amber-400">
            거래일: {formatTradingDate(tradingDate)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-3 flex items-center justify-end">
      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700">
        <CheckCircle className="w-3.5 h-3.5 text-green-500 dark:text-green-400" />
        <span className="text-xs text-green-700 dark:text-green-300 font-medium">
          {formatTradingDate(tradingDate)}
        </span>
        <span className="text-xs text-green-600 dark:text-green-400 opacity-70">
          · {formatKoreanDateTime(generatedAt)} 생성
        </span>
      </div>
    </div>
  );
}
