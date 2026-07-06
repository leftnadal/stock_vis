'use client';

import Link from 'next/link';
import { DIRECTION_BADGE, DIRECTION_SPINE } from './colorSemantics';
import type { Recommendation } from '@/types/eod';

const CONFIDENCE_LABEL: Record<Recommendation['confidence'], string> = {
  high: '신뢰 높음',
  medium: '신뢰 보통',
  low: '신뢰 낮음',
};

/**
 * 추천 카드 (A+, D-P1-CAROUSEL).
 * - 방향 이중표기: 색 배지 + 동사 라벨(색 단독 인코딩 금지 = 색맹 안전).
 * - strength spine: 방향색 + |composite_score| 길이.
 * - placeholder ghost: thesis/perspectives/risk가 모두 null이면 자리 예약 스트립(additive-within 대비).
 * - 카드 → 체인사이트 진입(기존 eod 관례 /stocks/{ticker}?tab=chain-sight 재사용).
 */
export function RecommendationCard({ rec }: { rec: Recommendation }) {
  const isBuy = rec.composite_score >= 0;
  const strengthPct = Math.round(Math.min(Math.abs(rec.composite_score), 1) * 100);
  const directionVerb = isBuy ? '매수' : '매도·회피';

  // 색 단독 의존 금지 — 동사 라벨이 주 인코딩, 색은 보조.
  // 한국축(D-COLOR-SYSTEM): 매수 rose / 매도 sky. colorSemantics 단일소스(퍼지 안전).
  const badgeClass = isBuy ? DIRECTION_BADGE.buy : DIRECTION_BADGE.sell;
  const spineClass = isBuy ? DIRECTION_SPINE.buy : DIRECTION_SPINE.sell;

  const perspectivesEmpty =
    !rec.perspectives.technical &&
    !rec.perspectives.fundamental &&
    !rec.perspectives.news_context;
  const hasPlaceholder =
    rec.thesis === null && rec.risk === null && perspectivesEmpty;

  return (
    <div
      role="group"
      aria-label={`추천 ${rec.rank}위 ${rec.ticker} ${directionVerb} · ${CONFIDENCE_LABEL[rec.confidence]}`}
      className="flex w-64 flex-shrink-0 snap-start flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800"
    >
      {/* rank + ticker + company */}
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-semibold text-gray-400 dark:text-gray-500">
          #{rec.rank}
        </span>
        <span className="text-lg font-bold text-gray-900 dark:text-white">
          {rec.ticker}
        </span>
        <span className="truncate text-xs text-gray-500 dark:text-gray-400">
          {rec.company_name}
        </span>
      </div>

      {/* 방향 배지(색 + 동사 이중) + signal_tag + confidence */}
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
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {CONFIDENCE_LABEL[rec.confidence]}
        </span>
      </div>

      {/* strength spine: 방향색 + |score| 길이 */}
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700"
        role="meter"
        aria-valuenow={strengthPct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`신호 강도 ${strengthPct}%`}
      >
        <div className={`h-full ${spineClass}`} style={{ width: `${strengthPct}%` }} />
      </div>

      {/* placeholder ghost (LLM 채움 전) 또는 실내용(additive-within) */}
      {hasPlaceholder ? (
        <div className="rounded-md border border-dashed border-gray-200 px-2 py-1.5 text-xs italic text-gray-400 dark:border-gray-600 dark:text-gray-500">
          곧: 논리 · 3관점 · 리스크
        </div>
      ) : (
        <div className="flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-300">
          {rec.thesis && <p className="line-clamp-2">{rec.thesis}</p>}
          {rec.risk && (
            <p className="text-rose-600 dark:text-rose-400">⚠ {rec.risk}</p>
          )}
        </div>
      )}

      {/* 체인사이트 진입 */}
      <Link
        href={`/stocks/${rec.ticker}?tab=chain-sight`}
        className="mt-auto inline-flex items-center text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
      >
        체인사이트 분석 →
      </Link>
    </div>
  );
}
