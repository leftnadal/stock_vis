'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { assignZone, heatMedian } from '@/components/charts/SectorQuadrant';
import { useSectorQuadrant } from '@/hooks/useSectorQuadrant';
import type { Recommendation, SignalCard } from '@/types/eod';

interface SectorChipLineProps {
  /** 추천 캐러셀 payload — J2 조인(ticker→sector)의 좌변. */
  recommendations?: Recommendation[];
  /** signal_cards — preview_stocks가 J2 조인의 우변(ticker→sector 사전). */
  cards?: SignalCard[];
  /** 주어지면 버튼으로 탭 전환(기존 쿼리 파라미터 보존). 없으면 ?tab=market 링크. */
  onViewMarket?: () => void;
}

const MAX_NAMED_SECTORS = 3;

/** preview_stocks 전량을 symbol→sector 사전으로 (J2 조인 재료). */
export function buildSectorIndex(cards: SignalCard[] | undefined): Map<string, string> {
  const index = new Map<string, string>();
  for (const card of cards ?? []) {
    for (const stock of card.preview_stocks ?? []) {
      if (stock?.symbol && stock?.sector && !index.has(stock.symbol)) {
        index.set(stock.symbol, stock.sector);
      }
    }
  }
  return index;
}

/**
 * 추천 종목 중 조인에 성공한 수 / 그중 수요 개선 섹터(구역 II)에 속한 수.
 * resolved === 0 = 조인 실패 → 소비처가 그 절만 생략한다(D-SCAN-REC-JOIN-J2 정칙 ⑴).
 */
export function joinRecommendationSectors(
  recommendations: Recommendation[] | undefined,
  index: Map<string, string>,
  risingSectors: Set<string>,
): { resolved: number; rising: number } {
  let resolved = 0;
  let rising = 0;
  for (const rec of recommendations ?? []) {
    const sector = index.get(rec.ticker);
    if (!sector) continue;
    resolved += 1;
    if (risingSectors.has(sector)) rising += 1;
  }
  return { resolved, rising };
}

function sectorNames(names: string[]): string {
  const head = names.slice(0, MAX_NAMED_SECTORS).join(' · ');
  const rest = names.length - MAX_NAMED_SECTORS;
  return rest > 0 ? `${head} 외 ${rest}곳` : head;
}

/**
 * Q3 섹터 칩 — 사분면 데이터를 한 줄 사실 서술로 요약하고 [시장] 탭으로 보낸다.
 *
 * 정칙 ⑴: 데이터가 없거나(비로그인·401·API 미도달) 분류된 섹터가 없으면 **조용히 생략**한다.
 * 구역 정의는 차트와 같은 소스를 쓴다(assignZone·heatMedian 재사용 — 중복 정의 금지).
 */
export function SectorChipLine({ recommendations, cards, onViewMarket }: SectorChipLineProps) {
  const { data } = useSectorQuadrant();

  if (!data?.sectors?.length) return null;

  const median = heatMedian(data.sectors);
  const rising = data.sectors.filter((s) => assignZone(s, median) === 'II');
  const cooling = data.sectors.filter((s) => assignZone(s, median) === 'IV');

  if (rising.length === 0 && cooling.length === 0) return null;

  const risingNames = rising.map((s) => s.sector);
  const risingSet = new Set(risingNames);
  const join = joinRecommendationSectors(recommendations, buildSectorIndex(cards), risingSet);

  const label = '시장 탭에서 보기';

  return (
    <div
      className="mb-4 flex flex-wrap items-center gap-x-2 gap-y-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700"
    >
      <span className="text-xs text-gray-600 dark:text-gray-300">
        {rising.length > 0 && (
          <>
            수요가 붙는 섹터 {rising.length}곳
            <span className="text-gray-400 dark:text-gray-500"> ({sectorNames(risingNames)})</span>
          </>
        )}
        {rising.length > 0 && cooling.length > 0 && <span className="mx-1">·</span>}
        {cooling.length > 0 && (
          <>
            관심 대비 수요가 빠지는 섹터 {cooling.length}곳
            <span className="text-gray-400 dark:text-gray-500">
              {' '}
              ({sectorNames(cooling.map((s) => s.sector))})
            </span>
          </>
        )}
      </span>

      {join.resolved > 0 && (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          · 추천 {join.resolved}종목 중 {join.rising}곳이 수요가 붙는 섹터
        </span>
      )}

      {onViewMarket ? (
        <button
          type="button"
          onClick={onViewMarket}
          className="ml-auto inline-flex items-center gap-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
        >
          {label}
          <ArrowRight className="w-3 h-3" />
        </button>
      ) : (
        <Link
          href="?tab=market"
          className="ml-auto inline-flex items-center gap-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
        >
          {label}
          <ArrowRight className="w-3 h-3" />
        </Link>
      )}
    </div>
  );
}
