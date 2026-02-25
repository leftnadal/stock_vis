// News event timeline component with chain_logic tooltip support

'use client';

import React from 'react';
import { format, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowRight,
  GitBranch,
  Zap,
  Activity,
  AlertCircle,
} from 'lucide-react';
import { useNewsEvents } from '@/hooks/useNews';
import { NewsEventData, NewsEventImpact, NewsEventSummary } from '@/types/news';

// ===== Props =====

interface NewsEventTimelineProps {
  symbol: string;
  days?: number;
}

// ===== Direction helpers =====

type DirectionType = 'bullish' | 'bearish' | 'neutral';

function normalizeDirection(direction: string): DirectionType {
  const d = direction.toLowerCase();
  if (d === 'bullish' || d === 'positive') return 'bullish';
  if (d === 'bearish' || d === 'negative') return 'bearish';
  return 'neutral';
}

const DIRECTION_STYLES: Record<DirectionType, { bg: string; border: string; text: string; icon: React.ElementType; iconColor: string; label: string }> = {
  bullish: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    border: 'border-green-200 dark:border-green-700',
    text: 'text-green-700 dark:text-green-300',
    icon: TrendingUp,
    iconColor: 'text-green-500',
    label: '상승',
  },
  bearish: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-200 dark:border-red-700',
    text: 'text-red-700 dark:text-red-300',
    icon: TrendingDown,
    iconColor: 'text-red-500',
    label: '하락',
  },
  neutral: {
    bg: 'bg-gray-50 dark:bg-gray-800',
    border: 'border-gray-200 dark:border-gray-600',
    text: 'text-gray-700 dark:text-gray-300',
    icon: Minus,
    iconColor: 'text-gray-400',
    label: '중립',
  },
};

// Tier badge styles
const TIER_STYLES: Record<string, { bg: string; text: string }> = {
  A: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-300' },
  B: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300' },
  C: { bg: 'bg-gray-100 dark:bg-gray-700', text: 'text-gray-600 dark:text-gray-400' },
};

function getTierStyle(tier: string) {
  return TIER_STYLES[tier.toUpperCase()] ?? TIER_STYLES['C'];
}

// ===== Confidence bar =====

interface ConfidenceBarProps {
  value: number; // 0~1
  direction: DirectionType;
}

function ConfidenceBar({ value, direction }: ConfidenceBarProps) {
  const pct = Math.round(value * 100);
  const colorMap: Record<DirectionType, string> = {
    bullish: 'bg-green-400 dark:bg-green-500',
    bearish: 'bg-red-400 dark:bg-red-500',
    neutral: 'bg-gray-300 dark:bg-gray-500',
  };

  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${colorMap[direction]}`}
          style={{ width: `${pct}%`, opacity: 0.4 + value * 0.6 }}
        />
      </div>
      <span className="text-xs text-gray-400 dark:text-gray-500 tabular-nums">{pct}%</span>
    </div>
  );
}

// ===== Chain logic tooltip (Tailwind group/relative/absolute pattern) =====

interface ChainLogicTooltipProps {
  chainLogic: string;
}

function ChainLogicTooltip({ chainLogic }: ChainLogicTooltipProps) {
  return (
    <span className="relative group/tooltip inline-flex items-center">
      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded text-xs text-amber-600 dark:text-amber-400 cursor-help select-none">
        <GitBranch className="w-3 h-3" />
        연쇄
      </span>
      {/* Tooltip popup */}
      <span
        className="
          absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50
          w-64 max-w-xs
          px-3 py-2
          bg-gray-900 dark:bg-gray-700
          text-white text-xs leading-relaxed
          rounded-lg shadow-lg
          pointer-events-none
          opacity-0 group-hover/tooltip:opacity-100
          transition-opacity duration-150
          whitespace-normal
        "
      >
        {chainLogic}
        {/* Arrow */}
        <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700" />
      </span>
    </span>
  );
}

// ===== Single impact row =====

interface ImpactRowProps {
  impact: NewsEventImpact;
  impactType: 'direct' | 'indirect';
  isLast: boolean;
}

function ImpactRow({ impact, impactType, isLast }: ImpactRowProps) {
  const direction = normalizeDirection(impact.direction);
  const styles = DIRECTION_STYLES[direction];
  const Icon = styles.icon;

  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-start gap-2 py-2 ${
        !isLast ? 'border-b border-gray-100 dark:border-gray-700/50' : ''
      }`}
    >
      {/* Impact type badge */}
      <div className="flex-shrink-0 pt-0.5">
        {impactType === 'direct' ? (
          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-700 rounded">
            <Zap className="w-2.5 h-2.5" />
            직접
          </span>
        ) : (
          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-700 rounded">
            <Activity className="w-2.5 h-2.5" />
            간접
          </span>
        )}
      </div>

      {/* Symbol + direction */}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <ArrowRight className="w-3 h-3 text-gray-400" />
        <span className="text-sm font-bold text-gray-900 dark:text-white">{impact.symbol}</span>
        <span
          className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs rounded-full border ${styles.bg} ${styles.border} ${styles.text}`}
        >
          <Icon className={`w-3 h-3 ${styles.iconColor}`} />
          {styles.label}
        </span>
      </div>

      {/* Right side: confidence + reason + chain_logic */}
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        <ConfidenceBar value={impact.confidence} direction={direction} />
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-gray-500 dark:text-gray-400 leading-snug">
            {impact.reason}
          </span>
          {impact.chain_logic && (
            <ChainLogicTooltip chainLogic={impact.chain_logic} />
          )}
        </div>
      </div>
    </div>
  );
}

// ===== Single event card =====

interface EventCardProps {
  event: NewsEventData;
}

function EventCard({ event }: EventCardProps) {
  const tierStyle = getTierStyle(event.tier);
  const allImpacts = [
    ...event.direct_impacts.map((i) => ({ impact: i, type: 'direct' as const })),
    ...event.indirect_impacts.map((i) => ({ impact: i, type: 'indirect' as const })),
  ];

  let publishedLabel = '';
  try {
    publishedLabel = format(parseISO(event.published_at), 'MM/dd HH:mm', { locale: ko });
  } catch {
    publishedLabel = event.published_at;
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Event header */}
      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap items-start gap-2">
          {/* Tier badge */}
          <span
            className={`flex-shrink-0 mt-0.5 inline-block px-2 py-0.5 text-xs font-bold rounded ${tierStyle.bg} ${tierStyle.text}`}
          >
            Tier {event.tier}
          </span>

          {/* Title */}
          <h4 className="flex-1 text-sm font-semibold text-gray-900 dark:text-white leading-snug min-w-0">
            {event.title}
          </h4>
        </div>

        {/* Meta: source + time + importance */}
        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
          <span>{event.source}</span>
          <span>·</span>
          <span>{publishedLabel}</span>
          <span>·</span>
          <span>중요도 {Math.round(event.importance_score * 100)}%</span>
        </div>
      </div>

      {/* Impact rows */}
      {allImpacts.length > 0 ? (
        <div className="px-4 divide-y-0">
          {allImpacts.map(({ impact, type }, idx) => (
            <ImpactRow
              key={`${impact.symbol}-${type}-${idx}`}
              impact={impact}
              impactType={type}
              isLast={idx === allImpacts.length - 1}
            />
          ))}
        </div>
      ) : (
        <p className="px-4 py-3 text-xs text-gray-400 dark:text-gray-500">
          이 이벤트에 연관된 종목이 없습니다.
        </p>
      )}
    </div>
  );
}

// ===== Summary bar =====

interface SummaryBarProps {
  summary: NewsEventSummary;
}

function SummaryBar({ summary }: SummaryBarProps) {
  const stats = [
    { label: '이벤트', value: summary.total_events, color: 'text-gray-700 dark:text-gray-200' },
    { label: '상승', value: summary.bullish_count, color: 'text-green-600 dark:text-green-400' },
    { label: '하락', value: summary.bearish_count, color: 'text-red-600 dark:text-red-400' },
    { label: '직접', value: summary.direct_count, color: 'text-blue-600 dark:text-blue-400' },
    { label: '간접', value: summary.indirect_count, color: 'text-indigo-600 dark:text-indigo-400' },
    {
      label: '평균 신뢰도',
      value: `${Math.round(summary.avg_confidence * 100)}%`,
      color: 'text-gray-600 dark:text-gray-300',
    },
  ];

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-xs">
      {stats.map(({ label, value, color }) => (
        <span key={label} className="flex items-center gap-1">
          <span className="text-gray-400 dark:text-gray-500">{label}</span>
          <span className={`font-semibold tabular-nums ${color}`}>{value}</span>
        </span>
      ))}
    </div>
  );
}

// ===== Skeleton placeholder =====

function TimelineSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {[1, 2, 3].map((n) => (
        <div
          key={n}
          className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
        >
          <div className="px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-start gap-2">
              <div className="w-14 h-5 bg-gray-200 dark:bg-gray-600 rounded" />
              <div className="flex-1 h-5 bg-gray-200 dark:bg-gray-600 rounded" />
            </div>
            <div className="mt-1.5 w-32 h-3 bg-gray-100 dark:bg-gray-700 rounded" />
          </div>
          <div className="px-4 py-2 space-y-2">
            {[1, 2].map((m) => (
              <div key={m} className="flex items-center gap-2 py-2">
                <div className="w-10 h-5 bg-gray-100 dark:bg-gray-700 rounded" />
                <div className="w-16 h-5 bg-gray-100 dark:bg-gray-700 rounded" />
                <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-700 rounded" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ===== Main component =====

export default function NewsEventTimeline({ symbol, days = 7 }: NewsEventTimelineProps) {
  const { data, isLoading, isError, error } = useNewsEvents(symbol, days);

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <Activity className="w-4 h-4 animate-pulse" />
          <span>뉴스 이벤트 불러오는 중...</span>
        </div>
        <TimelineSkeleton />
      </div>
    );
  }

  // Error state
  if (isError) {
    const message = error instanceof Error ? error.message : '알 수 없는 오류';
    return (
      <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
        <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-medium">데이터를 불러오지 못했습니다.</p>
          <p className="text-xs mt-0.5 text-red-500 dark:text-red-400">{message}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!data || data.events.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-10 text-center text-gray-400 dark:text-gray-500">
        <Activity className="w-8 h-8" />
        <p className="text-sm font-medium">No news events for {symbol}</p>
        <p className="text-xs">최근 {days}일 내 연관 이벤트가 없습니다.</p>
      </div>
    );
  }

  // Sort events by published_at descending (newest first)
  const sortedEvents = [...data.events].sort(
    (a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime()
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-500" />
          뉴스 이벤트 타임라인
          <span className="text-xs font-normal text-gray-400 dark:text-gray-500">
            ({symbol} · 최근 {days}일)
          </span>
        </h3>
      </div>

      {/* Summary bar */}
      <SummaryBar summary={data.summary} />

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-0 top-0 bottom-0 w-px bg-gray-200 dark:bg-gray-700 ml-3 hidden sm:block" />

        <div className="space-y-4 sm:pl-8">
          {sortedEvents.map((event, idx) => (
            <div key={event.article_id} className="relative">
              {/* Timeline dot */}
              <div className="absolute -left-5 top-4 hidden sm:flex items-center justify-center w-3 h-3 rounded-full bg-blue-400 dark:bg-blue-500 border-2 border-white dark:border-gray-900 shadow-sm" />

              {/* Date label */}
              {(idx === 0 ||
                !isSameDay(event.published_at, sortedEvents[idx - 1].published_at)) && (
                <div className="mb-2 -ml-8 hidden sm:block">
                  <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">
                    {formatDateLabel(event.published_at)}
                  </span>
                </div>
              )}

              <EventCard event={event} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ===== Date helpers =====

function isSameDay(a: string, b: string): boolean {
  try {
    const da = parseISO(a);
    const db = parseISO(b);
    return (
      da.getFullYear() === db.getFullYear() &&
      da.getMonth() === db.getMonth() &&
      da.getDate() === db.getDate()
    );
  } catch {
    return false;
  }
}

function formatDateLabel(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'yyyy년 MM월 dd일 (EEE)', { locale: ko });
  } catch {
    return dateStr;
  }
}
