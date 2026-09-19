'use client';

import type { Recommendation } from '@/types/eod';
import { RecommendationCard } from './RecommendationCard';
import { getAxisCategories, type ConfluenceMap, type StockIndex } from './confluence';
import { sortRecommendations } from './recommendation';

/**
 * 추천 캐러셀 (A+, D-P1-CAROUSEL · DASH-RECO R3).
 * - 단일 가로 스크롤, N=10.
 * - R3 정렬: 축 수 내림 → 거래대금 내림 → ticker 오름(composite_score 포화로 폐기).
 * - 순서가 합류 지도에 의존 → 지도 로딩 중에는 **캐러셀만** 스켈레톤(도착 시 재정렬로 카드가 튀지 않게).
 *   로딩이 끝났는데 지도가 없으면(요청 실패) 축 0으로 그대로 렌더(정칙 ⑴).
 * - 하위호환: recommendations 부재/빈 배열이면 캐러셀 표면 생략(기존 6키 화면 무영향).
 * - 접근성: 가로 스크롤 컨테이너 keyboard focus 가능(tabIndex), 카드별 aria-label.
 */
export function RecommendationCarousel({
  recommendations,
  tradingDate,
  confluenceMap,
  stockIndex,
  confluenceLoading = false,
  onSelect,
}: {
  recommendations?: Recommendation[];
  tradingDate?: string;
  confluenceMap?: ConfluenceMap;
  /** 카드 JSON symbol→행(거래대금 조인). */
  stockIndex?: StockIndex;
  /** 합류 지도 로딩 중 여부 — true면 캐러셀 스켈레톤. */
  confluenceLoading?: boolean;
  /** 카드 본문 클릭 → 추천 드로어. */
  onSelect?: (rec: Recommendation) => void;
}) {
  if (!recommendations || recommendations.length === 0) {
    return null; // 하위호환 — 표면 생략
  }

  const heading = (
    <h2 className="mb-2 px-1 text-sm font-semibold text-gray-700 dark:text-gray-200">
      오늘의 추천 <span className="text-gray-400">({recommendations.length})</span>
    </h2>
  );

  if (confluenceLoading && !confluenceMap) {
    return (
      <section data-guide="dashboard.recommendations" aria-label="추천 종목 캐러셀" aria-busy="true" className="my-4">
        {heading}
        <div className="flex gap-3 overflow-hidden pb-2" data-testid="recommendation-skeleton">
          {Array.from({ length: Math.min(recommendations.length, 4) }).map((_, i) => (
            <div
              key={i}
              className="h-44 w-64 flex-shrink-0 animate-pulse rounded-xl border border-gray-200 bg-gray-100 dark:border-gray-700 dark:bg-gray-800"
            />
          ))}
        </div>
      </section>
    );
  }

  const sorted = sortRecommendations(recommendations, confluenceMap, stockIndex);

  return (
    <section data-guide="dashboard.recommendations" aria-label="추천 종목 캐러셀" className="my-4">
      {heading}
      <div
        tabIndex={0}
        role="list"
        aria-label="추천 종목 가로 목록"
        className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        {sorted.map((rec) => (
          <div role="listitem" key={`${rec.rank}-${rec.ticker}`}>
            <RecommendationCard
              rec={rec}
              tradingDate={tradingDate}
              axisCategories={getAxisCategories(confluenceMap, rec.ticker)}
              onOpen={onSelect ? () => onSelect(rec) : undefined}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
