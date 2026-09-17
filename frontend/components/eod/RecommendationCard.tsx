'use client';

import { useRef } from 'react';
import Link from 'next/link';
import { Layers } from 'lucide-react';
import { DIRECTION_BADGE } from '@/components/common/colorSemantics';
import { useImpressionTracker } from '@/hooks/useImpressionTracker';
import { recoObjectRef, SURFACE_RECO_CARD } from '@/hooks/impressionTelemetry';
import { AXIS_CATEGORIES } from './confluence';
import { PERSPECTIVE_LABEL, pickPerspectiveLine } from './recommendation';
import { SIGNAL_CATEGORY_COLORS, SIGNAL_CATEGORY_LABELS } from '@/types/eod';
import type { Recommendation, SignalCategory } from '@/types/eod';

/** 6칸 축 pips — 칸 위치가 곧 카테고리(AXIS_CATEGORIES 순서), 걸린 축만 채운다. */
function AxisPips({ categories }: { categories: SignalCategory[] }) {
  const hit = new Set(categories);
  const labels = AXIS_CATEGORIES.filter((c) => hit.has(c)).map((c) => SIGNAL_CATEGORY_LABELS[c]);
  return (
    <div
      role="img"
      aria-label={`신호 축 6개 중 ${labels.length}축: ${labels.join(' · ')}`}
      className="flex gap-1"
    >
      {AXIS_CATEGORIES.map((cat) => (
        <span
          key={cat}
          data-axis={cat}
          data-filled={hit.has(cat) ? 'true' : 'false'}
          title={SIGNAL_CATEGORY_LABELS[cat]}
          className={`h-1.5 flex-1 rounded-full ${hit.has(cat) ? '' : 'bg-gray-100 dark:bg-gray-700'}`}
          style={hit.has(cat) ? { backgroundColor: SIGNAL_CATEGORY_COLORS[cat] } : undefined}
        />
      ))}
    </div>
  );
}

/**
 * 추천 카드 (A+, D-P1-CAROUSEL · DASH-RECO R3/P3).
 * - 방향 이중표기: 색 배지 + 동사 라벨(색 단독 인코딩 금지 = 색맹 안전).
 * - 축: 헤더 `N축` 배지(1축부터) + 6칸 pips. 0축이면 둘 다 생략(정칙 ⑴ — "약함"이 아니라 "없음").
 * - 관점 한 줄(P3): fundamental ?? technical, 둘 다 없으면 줄 생략.
 * - placeholder ghost: thesis/perspectives/risk가 모두 null이면 자리 예약 스트립(additive-within 대비).
 * - 본문 클릭 = 추천 드로어(주 동선). `체인사이트 →`는 명시 클릭만(부 동선 — 본문 클릭으로 전파 안 함).
 */
export function RecommendationCard({
  rec,
  tradingDate,
  axisCategories = [],
  onOpen,
}: {
  rec: Recommendation;
  tradingDate?: string;
  /** 스캐너 합류 지도에서 이 종목이 걸린 카테고리 축. 미로딩·교집합 밖 = [] → 축 표시 생략. */
  axisCategories?: SignalCategory[];
  /** 본문 클릭 시 드로어 열기. 없으면 본문은 클릭 대상이 아니다. */
  onOpen?: () => void;
}) {
  const isBuy = rec.composite_score >= 0;
  const axisCount = axisCategories.length;
  const directionVerb = isBuy ? '매수' : '매도·회피';
  const perspectiveLine = pickPerspectiveLine(rec);

  // impression/click 추적: object_ref = ticker:trading_date:signal_tag (IssuanceLog grain 정합).
  const objectRef = recoObjectRef(rec.ticker, tradingDate ?? '', rec.signal_tag);
  const { ref, onClick } = useImpressionTracker<HTMLDivElement>(SURFACE_RECO_CARD, objectRef);

  // 가로 캐러셀 스와이프 뒤의 click은 드로어를 열지 않는다(SignalCard와 같은 가드).
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const swipedRef = useRef(false);

  // 색 단독 의존 금지 — 동사 라벨이 주 인코딩, 색은 보조.
  // 한국축(D-COLOR-SYSTEM): 매수 rose / 매도 sky. colorSemantics 단일소스(퍼지 안전).
  const badgeClass = isBuy ? DIRECTION_BADGE.buy : DIRECTION_BADGE.sell;

  const perspectivesEmpty =
    !rec.perspectives.technical &&
    !rec.perspectives.fundamental &&
    !rec.perspectives.news_context;
  const hasPlaceholder =
    rec.thesis === null && rec.risk === null && perspectivesEmpty;

  const handleClick = () => {
    if (swipedRef.current) {
      swipedRef.current = false;
      return;
    }
    onOpen?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.target !== e.currentTarget) return; // 내부 링크의 Enter는 링크 몫
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onOpen?.();
    }
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    touchStartRef.current = { x: t.clientX, y: t.clientY };
    swipedRef.current = false;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const start = touchStartRef.current;
    if (!start) return;
    const t = e.touches[0];
    if (Math.abs(t.clientX - start.x) > 10 || Math.abs(t.clientY - start.y) > 10) {
      swipedRef.current = true;
    }
  };

  const interactive = !!onOpen;

  return (
    <div
      ref={ref}
      role={interactive ? 'button' : 'group'}
      tabIndex={interactive ? 0 : undefined}
      aria-label={`추천 ${rec.ticker} ${directionVerb}${axisCount > 0 ? ` · ${axisCount}축` : ''}`}
      onClick={interactive ? handleClick : undefined}
      onKeyDown={interactive ? handleKeyDown : undefined}
      onTouchStart={interactive ? handleTouchStart : undefined}
      onTouchMove={interactive ? handleTouchMove : undefined}
      className={`flex w-64 flex-shrink-0 snap-start flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800${
        interactive
          ? ' cursor-pointer transition-colors hover:border-gray-300 dark:hover:border-gray-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500'
          : ''
      }`}
    >
      {/* ticker + company + N축(1축부터) */}
      <div className="flex items-baseline gap-2">
        <span className="text-lg font-bold text-gray-900 dark:text-white">
          {rec.ticker}
        </span>
        <span className="min-w-0 flex-1 truncate text-xs text-gray-500 dark:text-gray-400">
          {rec.company_name}
        </span>
        {axisCount > 0 && (
          <span
            className="inline-flex flex-shrink-0 items-center gap-0.5 self-center rounded-full border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 dark:border-indigo-800 dark:bg-indigo-900/20 dark:text-indigo-300"
            title="스캐너 신호 축 6개 중 이 종목이 걸린 축 수"
          >
            <Layers className="w-2.5 h-2.5" />
            {axisCount}축
          </span>
        )}
      </div>

      {/* 방향 배지(색 + 동사 이중) + signal_tag */}
      <div className="flex flex-wrap items-center gap-2">
        <span
          aria-label={`방향: ${directionVerb}`}
          className={`rounded-full px-2 py-0.5 text-xs font-bold ${badgeClass}`}
        >
          {directionVerb}
        </span>
        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-mono text-gray-600 dark:bg-gray-700 dark:text-gray-300">
          {rec.signal_tag}
        </span>
      </div>

      {/* 6칸 축 pips — 0축이면 생략 */}
      {axisCount > 0 && <AxisPips categories={axisCategories} />}

      {/* placeholder ghost (LLM 채움 전) 또는 실내용(additive-within) */}
      {hasPlaceholder ? (
        <div className="rounded-md border border-dashed border-gray-200 px-2 py-1.5 text-xs italic text-gray-400 dark:border-gray-600 dark:text-gray-500">
          곧: 논리 · 3관점 · 리스크
        </div>
      ) : (
        <div className="flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-300">
          {rec.thesis && <p className="line-clamp-2">{rec.thesis}</p>}
          {/* P3 관점 한 줄 — thesis와 별도 줄(자리 경쟁 없음) */}
          {perspectiveLine && (
            <p className="line-clamp-1 text-gray-500 dark:text-gray-400" title={perspectiveLine.text}>
              <span className="font-medium text-gray-600 dark:text-gray-300">
                {PERSPECTIVE_LABEL[perspectiveLine.kind]}
              </span>
              {' · '}
              {perspectiveLine.text}
            </p>
          )}
          {rec.risk && (
            <p className="text-rose-600 dark:text-rose-400">⚠ {rec.risk}</p>
          )}
        </div>
      )}

      {/* 체인사이트 진입(부 동선) — 본문 클릭(드로어)으로 전파하지 않는다 */}
      <Link
        href={`/stocks/${rec.ticker}?tab=chain-sight`}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        className="mt-auto inline-flex items-center self-start text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
      >
        체인사이트 분석 →
      </Link>
    </div>
  );
}
