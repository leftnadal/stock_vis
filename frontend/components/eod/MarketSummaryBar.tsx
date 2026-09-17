'use client';

import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';
import { VixChip } from './VixChip';
import {
  CHANGE_CHIP,
  DIRECTION_BAND,
  SIGNED_BAR,
  STRENGTH_TEXT,
} from '@/components/common/colorSemantics';
import type { MarketSummary, SignalCard } from '@/types/eod';

/** 그리드 방향 필터(D3). composite_score 부호 기준. */
export type DirectionFilter = 'all' | 'bull' | 'bear' | 'neutral';

/** 세그먼트에 표기할 종목 수 — 소비처가 **실제 필터 결과와 같은 모집단**에서 센다. */
export interface DirectionCounts {
  all: number;
  bull: number;
  bear: number;
  neutral: number;
}

interface MarketSummaryBarProps {
  summary: MarketSummary;
  activeDirection?: DirectionFilter;
  onDirectionChange?: (direction: DirectionFilter) => void;
  directionCounts?: DirectionCounts;
  /** 세그먼트 모집단의 고유 종목 수 — 행 수(directionCounts.all)와 다르다는 사실을 밝히기 위함. */
  uniqueStockCount?: number;
}

/**
 * 방향 축 단일 소스 — 종목 하나의 방향은 composite_score 부호로만 정한다.
 * 0·부재 = 중립(payload에 0.0이 실제로 존재한다).
 */
export function directionOfScore(score: number | null | undefined): Exclude<DirectionFilter, 'all'> {
  if (score == null || score === 0) return 'neutral';
  return score > 0 ? 'bull' : 'bear';
}

/** 카드들의 preview_stocks를 방향별로 센다(= 그리드에 실제로 보일 줄 수). */
export function countDirections(cards: SignalCard[]): DirectionCounts {
  const counts: DirectionCounts = { all: 0, bull: 0, bear: 0, neutral: 0 };
  for (const card of cards) {
    for (const stock of card.preview_stocks ?? []) {
      counts.all += 1;
      counts[directionOfScore(stock.composite_score)] += 1;
    }
  }
  return counts;
}

/** 카드들의 preview_stocks에 등장하는 **고유 종목 수**(같은 종목이 여러 카드에 걸린다). */
export function countUniqueSymbols(cards: SignalCard[]): number {
  const symbols = new Set<string>();
  for (const card of cards) {
    for (const stock of card.preview_stocks ?? []) {
      if (stock?.symbol) symbols.add(stock.symbol);
    }
  }
  return symbols.size;
}

/**
 * 방향으로 카드의 preview_stocks를 거르고, 남는 종목이 없는 카드는 뺀다.
 * `count`(카드 총 시그널 수)는 모집단 사실이라 건드리지 않고,
 * 숨은 종목의 방향 분포는 알 수 없으므로 `more_count`만 0으로 내린다.
 * ⚠ 새 배열/객체를 만들 뿐 렌더 key는 card.id 그대로다(필터 상태를 key에 넣지 않는다 — remount 금지).
 */
export function filterCardsByDirection(
  cards: SignalCard[],
  direction: DirectionFilter,
): SignalCard[] {
  if (direction === 'all') return cards;
  const out: SignalCard[] = [];
  for (const card of cards) {
    const stocks = (card.preview_stocks ?? []).filter(
      (s) => directionOfScore(s.composite_score) === direction,
    );
    if (stocks.length > 0) out.push({ ...card, preview_stocks: stocks, more_count: 0 });
  }
  return out;
}

const DIRECTION_SEGMENTS: { id: DirectionFilter; label: string }[] = [
  { id: 'all', label: '전체' },
  { id: 'bull', label: '강세' },
  { id: 'bear', label: '약세' },
  { id: 'neutral', label: '중립' },
];

const SEGMENT_ACTIVE: Record<DirectionFilter, string> = {
  all: 'bg-gray-200 text-gray-800 border-gray-300 dark:bg-gray-600 dark:text-gray-100 dark:border-gray-500',
  bull: DIRECTION_BAND.positive,
  bear: DIRECTION_BAND.negative,
  neutral: DIRECTION_BAND.neutral,
};

function ChangeChip({ label, value }: { label: string; value: number }) {
  const isPositive = value > 0;
  const isNeutral = value === 0;

  // 한국축(D-COLOR-SYSTEM): 상승 rose / 하락 sky / 보합 gray. 아이콘·부호 병기(색 보조).
  const colorClass = isNeutral
    ? CHANGE_CHIP.neutral
    : isPositive
    ? CHANGE_CHIP.up
    : CHANGE_CHIP.down;

  const Icon = isNeutral ? Minus : isPositive ? TrendingUp : TrendingDown;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${colorClass}`}>
      <Icon className="w-3 h-3" />
      {label}
      <span>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>
    </span>
  );
}

/**
 * 3색 바 — 강세(rose) · 중립(트랙 gray 노출) · 약세(sky).
 * 색은 colorSemantics 토큰만 소비하고, 중립은 별도 색을 만들지 않고 트랙을 드러내 표현한다.
 */
function BullBearBar({
  bullish,
  bearish,
  neutral,
}: {
  bullish: number;
  bearish: number;
  neutral: number;
}) {
  const total = bullish + bearish + neutral;
  if (total === 0) return null;
  const pct = (n: number) => (n / total) * 100;
  const bullPct = Math.round(pct(bullish));

  return (
    <div className="flex items-center gap-1.5">
      <span className={`text-xs ${STRENGTH_TEXT.positive} font-medium`}>{bullish}</span>
      <div className="w-24 h-2 rounded-full bg-gray-200 dark:bg-gray-600 overflow-hidden flex">
        <div className={`h-full ${SIGNED_BAR.positive}`} style={{ width: `${pct(bullish)}%` }} />
        {/* 중립 = 트랙 gray 노출 */}
        <div className="h-full" style={{ width: `${pct(neutral)}%` }} />
        <div className={`h-full ${SIGNED_BAR.negative}`} style={{ width: `${pct(bearish)}%` }} />
      </div>
      <span className={`text-xs ${STRENGTH_TEXT.negative} font-medium`}>{bearish}</span>
      <span className="text-[10px] text-gray-400 dark:text-gray-500 ml-0.5">({bullPct}%)</span>
    </div>
  );
}

export function MarketSummaryBar({
  summary,
  activeDirection = 'all',
  onDirectionChange,
  directionCounts,
  uniqueStockCount,
}: MarketSummaryBarProps) {
  const regimeLabel = summary.vix_regime === 'high_vol'
    ? '고변동성 구간'
    : summary.vix_regime === 'elevated'
    ? '변동성 주의'
    : null;

  const regimeBadgeClass = summary.vix_regime === 'high_vol'
    ? 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-700'
    : 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700';

  // 중립 = 전체 시그널에서 강세·약세를 뺀 나머지(payload 파생 — 하드코딩 없음).
  const neutralSignals = Math.max(
    0,
    summary.total_signals - summary.bullish_count - summary.bearish_count,
  );

  const showSegments = onDirectionChange != null && directionCounts != null;

  return (
    <div data-guide="dashboard.market-summary" className="mb-4 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
      {/* 헤드라인 */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          {summary.stock_universe.toLocaleString()}종목에서{' '}
          <span className="text-blue-600 dark:text-blue-400 text-2xl font-extrabold">
            {summary.total_signals}개
          </span>{' '}
          시그널 감지
        </h2>
        {regimeLabel && (
          <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${regimeBadgeClass}`}>
            <AlertTriangle className="w-3 h-3" />
            {regimeLabel}
          </span>
        )}
      </div>

      {/* 지표 배지 */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <ChangeChip label="S&P500" value={summary.sp500_change} />
        <ChangeChip label="QQQ" value={summary.qqq_change} />
        <VixChip vix={summary.vix} regime={summary.vix_regime} />
      </div>

      {/* 강세/중립/약세 비율 */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 dark:text-gray-400">강세/약세</span>
          <BullBearBar
            bullish={summary.bullish_count}
            bearish={summary.bearish_count}
            neutral={neutralSignals}
          />
        </div>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {summary.stocks_with_signals}개 종목
        </span>
      </div>
      <p className="mt-1 text-[10px] text-gray-400 dark:text-gray-500">
        시그널 수 기준(종목 수 아님) · 강세 {summary.bullish_count} · 중립 {neutralSignals} · 약세{' '}
        {summary.bearish_count}
      </p>

      {/* D3 방향 토글 — 아래 시그널 그리드를 composite_score 부호로 거른다 */}
      {showSegments && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          <div
            className="flex flex-wrap items-center gap-1.5"
            role="group"
            aria-label="방향 필터"
          >
            {DIRECTION_SEGMENTS.map((segment) => {
              const isActive = activeDirection === segment.id;
              return (
                <button
                  key={segment.id}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() => onDirectionChange(segment.id)}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-xs font-medium transition-colors ${
                    isActive
                      ? SEGMENT_ACTIVE[segment.id]
                      : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                  }`}
                >
                  {segment.label}
                  <span className="opacity-70">{directionCounts[segment.id]}</span>
                </button>
              );
            })}
          </div>
          <p className="mt-1.5 text-[10px] text-gray-400 dark:text-gray-500">
            composite_score 부호 기준 · 화면에 보이는 {directionCounts.all}줄
            {uniqueStockCount != null && `(고유 ${uniqueStockCount}종목 — 한 종목이 여러 카드에 걸립니다)`}
            {' · '}
            전체 {summary.stock_universe.toLocaleString()}종목 {summary.total_signals}신호
          </p>
        </div>
      )}
    </div>
  );
}
