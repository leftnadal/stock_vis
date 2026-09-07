'use client';

import { Fragment } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { fetchMarketStoryFeed } from '@/services/chainsightService';
import MarketStoryCardItem from './MarketStoryCardItem';

/**
 * "오늘 시장의 이야기" 피드 (R2-S2) — Chain Sight 신규 랜딩.
 *
 * 목업 준거 4항:
 * ⑴ 헤더 2줄(제목 + 부제, has_event=false는 정문 무공허 카피).
 * ⑵ 마인드맵 링크 헤더 우상단 상시 노출.
 * ⑶ 카드 클릭 → 마인드맵 카드 딥링크(?symbol=).
 * ⑷ 배지 색 계열 구분(사건=강조색·steady=중립색) — MarketStoryCardItem에서 처리.
 */
export default function MarketStoryFeed() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['chainsight', 'feed'],
    queryFn: () => fetchMarketStoryFeed(30),
    staleTime: 1000 * 60 * 5,
  });

  // A-5 정직화: 헤더는 창을 말하지 않는다(발견 2). 부제 = 오늘 새로 온 것 n · 전체 N.
  const subtitle = data
    ? data.has_event
      ? `오늘 새로 온 것 ${data.meta.new_today} · 전체 ${data.meta.stories}`
      : '오늘은 큰 사건이 없어요 — 꾸준히 활발한 이야기들'
    : null;

  // 사건(new_sec·daily_spike) → 배경(weekly_active) 전환점(구분선 삽입 위치).
  const firstSteadyIdx = data ? data.cards.findIndex((c) => c.type === 'weekly_active') : -1;

  return (
    <div className="p-6">
      {/* B-4: pr-24 로 전역 가이드 풍선(GuideOverlay fixed 우상단) 자리 확보 → 버튼 겹침 해소(공용 컴포넌트 무접촉). */}
      <div className="mb-6 flex items-start justify-between gap-4 pr-0 sm:pr-24">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">오늘 시장의 이야기</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {subtitle ?? ' '}
          </p>
        </div>
        {/* 목업 준거 ⑵: 마인드맵 링크는 항상 상시 노출(로딩·에러 상태에서도). */}
        <Link
          href="/chainsight/mindmap"
          className="shrink-0 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          업종별 보기 (마인드맵)
        </Link>
      </div>

      {isLoading && <div className="p-8 text-center text-gray-500">로딩 중...</div>}

      {isError && (
        <div className="p-8 text-center">
          <p className="text-red-500 mb-2">데이터를 불러올 수 없습니다</p>
          <button onClick={() => refetch()} className="text-sm text-blue-600 dark:text-blue-400 underline">
            다시 시도
          </button>
        </div>
      )}

      {data && data.cards.length === 0 && (
        <div className="p-8 text-center text-gray-500">아직 관찰된 이야기가 없습니다</div>
      )}

      {data && data.cards.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.cards.map((card, i) => (
            <Fragment key={card.story_id ?? `${card.type}-${card.symbol_a}-${card.symbol_b}`}>
              {/* 사건→배경 전환점 구분선(앞에 사건 카드가 있을 때만). */}
              {i === firstSteadyIdx && firstSteadyIdx > 0 && (
                <div
                  data-testid="steady-divider"
                  className="col-span-full flex items-center gap-3 py-1 text-[11px] text-gray-400 dark:text-gray-500"
                >
                  <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
                  여기부터 잔잔한 흐름
                  <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
                </div>
              )}
              <MarketStoryCardItem card={card} />
            </Fragment>
          ))}
        </div>
      )}
    </div>
  );
}
