'use client';

import type { Recommendation } from '@/types/eod';
import { RecommendationCard } from './RecommendationCard';

/**
 * 추천 캐러셀 (A+, D-P1-CAROUSEL / D-P1-REC-RANK).
 * - 단일 가로 스크롤, N=10.
 * - |composite_score| 내림차순: payload 순서를 신뢰하되 방어 정렬(불변).
 * - 하위호환: recommendations 부재/빈 배열이면 캐러셀 표면 생략(기존 6키 화면 무영향).
 * - 접근성: 가로 스크롤 컨테이너 keyboard focus 가능(tabIndex), 카드별 aria-label.
 */
export function RecommendationCarousel({
  recommendations,
  tradingDate,
}: {
  recommendations?: Recommendation[];
  tradingDate?: string;
}) {
  if (!recommendations || recommendations.length === 0) {
    return null; // 하위호환 — 표면 생략
  }

  // 방어 정렬: |composite_score| 내림차순(원본 불변 복사).
  const sorted = [...recommendations].sort(
    (a, b) => Math.abs(b.composite_score) - Math.abs(a.composite_score),
  );

  return (
    <section aria-label="추천 종목 캐러셀" className="my-4">
      <h2 className="mb-2 px-1 text-sm font-semibold text-gray-700 dark:text-gray-200">
        오늘의 추천 <span className="text-gray-400">({sorted.length})</span>
      </h2>
      <div
        tabIndex={0}
        role="list"
        aria-label="추천 종목 가로 목록"
        className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        {sorted.map((rec) => (
          <div role="listitem" key={`${rec.rank}-${rec.ticker}`}>
            <RecommendationCard rec={rec} tradingDate={tradingDate} />
          </div>
        ))}
      </div>
    </section>
  );
}
