'use client';

import { Database, Wifi, Clock, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

export type DataSource = 'db' | 'fmp' | 'fmp_realtime' | 'alpha_vantage' | 'yfinance' | 'unknown';
export type DataFreshness = 'fresh' | 'stale' | 'expired';

interface DataSourceBadgeProps {
  source: DataSource;
  syncedAt?: string | Date | null;
  freshness?: DataFreshness;
  showTime?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

// Source display names
const SOURCE_NAMES: Record<DataSource, string> = {
  db: 'DB',
  fmp: 'FMP',
  fmp_realtime: 'FMP',
  alpha_vantage: 'AV',
  yfinance: 'YF',
  unknown: '?',
};

// Source colors
const SOURCE_COLORS: Record<DataSource, string> = {
  db: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  fmp: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  fmp_realtime: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  alpha_vantage: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  yfinance: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  unknown: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
};

// Freshness colors
const FRESHNESS_COLORS: Record<DataFreshness, string> = {
  fresh: 'text-green-600 dark:text-green-400',
  stale: 'text-yellow-600 dark:text-yellow-400',
  expired: 'text-red-600 dark:text-red-400',
};

// Freshness icons
const FRESHNESS_ICONS: Record<DataFreshness, typeof CheckCircle> = {
  fresh: CheckCircle,
  stale: AlertTriangle,
  expired: XCircle,
};

// Format relative time
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return '방금 전';
  } else if (diffMinutes < 60) {
    return `${diffMinutes}분 전`;
  } else if (diffHours < 24) {
    return `${diffHours}시간 전`;
  } else if (diffDays < 7) {
    return `${diffDays}일 전`;
  } else {
    return date.toLocaleDateString('ko-KR', {
      month: 'short',
      day: 'numeric',
    });
  }
}

export default function DataSourceBadge({
  source,
  syncedAt,
  freshness = 'fresh',
  showTime = true,
  size = 'sm',
  className = '',
}: DataSourceBadgeProps) {
  const parsedDate = syncedAt ? (typeof syncedAt === 'string' ? new Date(syncedAt) : syncedAt) : null;
  const relativeTime = parsedDate ? formatRelativeTime(parsedDate) : null;

  const sourceName = SOURCE_NAMES[source] || SOURCE_NAMES.unknown;
  const sourceColor = SOURCE_COLORS[source] || SOURCE_COLORS.unknown;
  const freshnessColor = FRESHNESS_COLORS[freshness];
  const FreshnessIcon = FRESHNESS_ICONS[freshness];

  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1';
  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-4 w-4';

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      {/* Source badge */}
      <span className={`inline-flex items-center gap-1 rounded-full font-medium ${sizeClasses} ${sourceColor}`}>
        {source === 'db' ? <Database className={iconSize} /> : <Wifi className={iconSize} />}
        {sourceName}
      </span>

      {/* Time and freshness indicator */}
      {showTime && relativeTime && (
        <span className={`inline-flex items-center gap-1 ${freshnessColor} ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>
          <FreshnessIcon className={iconSize} />
          <span>{relativeTime}</span>
        </span>
      )}
    </div>
  );
}

// Compact version for tight spaces
export function DataSourceBadgeCompact({
  source,
  freshness = 'fresh',
  className = '',
}: Pick<DataSourceBadgeProps, 'source' | 'freshness' | 'className'>) {
  const freshnessColors: Record<DataFreshness, string> = {
    fresh: 'bg-green-500',
    stale: 'bg-yellow-500',
    expired: 'bg-red-500',
  };

  return (
    <div className={`inline-flex items-center gap-1 ${className}`}>
      <span className="text-xs text-gray-500 dark:text-gray-400">{SOURCE_NAMES[source]}</span>
      <span className={`w-2 h-2 rounded-full ${freshnessColors[freshness]}`} title={`Freshness: ${freshness}`}></span>
    </div>
  );
}

// Tooltip version with more details
interface DataSourceTooltipProps extends DataSourceBadgeProps {
  canSync?: boolean;
  onSync?: () => void;
}

export function DataSourceWithTooltip({
  source,
  syncedAt,
  freshness = 'fresh',
  canSync = true,
  onSync,
  className = '',
}: DataSourceTooltipProps) {
  const parsedDate = syncedAt ? (typeof syncedAt === 'string' ? new Date(syncedAt) : syncedAt) : null;

  const sourceFullNames: Record<DataSource, string> = {
    db: 'Database (Local)',
    fmp: 'Financial Modeling Prep',
    fmp_realtime: 'FMP Realtime',
    alpha_vantage: 'Alpha Vantage',
    yfinance: 'Yahoo Finance',
    unknown: 'Unknown',
  };

  const freshnessDescriptions: Record<DataFreshness, string> = {
    fresh: '최신 데이터입니다.',
    stale: '데이터가 오래되었습니다. 동기화를 권장합니다.',
    expired: '데이터가 만료되었습니다. 동기화가 필요합니다.',
  };

  return (
    <div className={`relative group ${className}`}>
      <DataSourceBadge source={source} syncedAt={syncedAt} freshness={freshness} />

      {/* Tooltip */}
      <div className="absolute left-0 top-full mt-1 z-50 invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-all duration-200">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3 min-w-[200px]">
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-gray-500 dark:text-gray-400">소스:</span>
              <span className="ml-2 text-gray-900 dark:text-white">{sourceFullNames[source]}</span>
            </div>
            {parsedDate && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">마지막 동기화:</span>
                <span className="ml-2 text-gray-900 dark:text-white">
                  {parsedDate.toLocaleString('ko-KR')}
                </span>
              </div>
            )}
            <div>
              <span className={FRESHNESS_COLORS[freshness]}>{freshnessDescriptions[freshness]}</span>
            </div>
            {canSync && onSync && freshness !== 'fresh' && (
              <button
                onClick={onSync}
                className="w-full mt-2 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700 transition-colors"
              >
                지금 동기화
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
