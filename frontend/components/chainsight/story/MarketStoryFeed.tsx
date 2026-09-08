'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { fetchMarketStoryFeed } from '@/services/chainsightService';
import MarketStoryCardItem from './MarketStoryCardItem';
import SteadyFold from './SteadyFold';
import { FOLD_STEADY_BY_DEFAULT, QUIET_DAY_PEEK } from './storyCardConfig';

/**
 * "오늘 시장의 이야기" 피드 (R2-S2 + S3-1 + S3-1B) — Chain Sight 랜딩.
 *
 * D-S3-7 배경 접기: 사건 카드(new_sec·daily_spike)는 항상 펴짐, weekly_active(배경)는
 * 기본 접힘(FOLD_STEADY_BY_DEFAULT). 아침 첫 화면의 조용함이 목적 → 펼침 상태 비저장.
 * 조용한 날(사건 0): 배경 상위 QUIET_DAY_PEEK장 카드 + "오늘은 조용합니다" + 나머지 접힘.
 * 헤더 부제 = D-S3-6 그대로(배경 수는 접힘 줄이 말함, 부제엔 안 씀).
 */
export default function MarketStoryFeed() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['chainsight', 'feed'],
    queryFn: () => fetchMarketStoryFeed(30),
    staleTime: 1000 * 60 * 5,
  });

  // 펼침 상태는 저장하지 않는다(localStorage·쿠키 금지) — 매일 접힌 채로 연다.
  const [steadyExpanded, setSteadyExpanded] = useState(!FOLD_STEADY_BY_DEFAULT);

  // A-5 정직화(D-S3-6 잠금): 헤더는 창을 말하지 않는다. 부제 = 오늘 새로 온 것 n · 전체 N.
  const subtitle = data
    ? data.has_event
      ? `오늘 새로 온 것 ${data.meta.new_today} · 전체 ${data.meta.stories}`
      : '오늘은 큰 사건이 없어요 — 꾸준히 활발한 이야기들'
    : null;

  const eventCards = data ? data.cards.filter((c) => c.type !== 'weekly_active') : [];
  const steadyCards = data ? data.cards.filter((c) => c.type === 'weekly_active') : [];
  const hasEvent = eventCards.length > 0;
  // 조용한 날엔 배경 상위 QUIET_DAY_PEEK장을 카드로 펴고 나머지를 접는다.
  const peekCards = hasEvent ? [] : steadyCards.slice(0, QUIET_DAY_PEEK);
  const foldedCards = hasEvent ? steadyCards : steadyCards.slice(QUIET_DAY_PEEK);
  const toggle = () => setSteadyExpanded((v) => !v);

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
          {/* 조용한 날: 빈 화면 금지 — 조용함을 말한다. */}
          {!hasEvent && (
            <p
              data-testid="quiet-note"
              className="col-span-full text-sm text-gray-500 dark:text-gray-400"
            >
              오늘은 조용합니다 — 이번 주 흐름만 보여드립니다
            </p>
          )}

          {/* 사건 카드(항상 펴짐) + 조용한 날 peek 카드. */}
          {[...eventCards, ...peekCards].map((card) => (
            <MarketStoryCardItem
              key={card.story_id ?? `${card.type}-${card.symbol_a}-${card.symbol_b}`}
              card={card}
            />
          ))}

          {/* 배경 접힘 줄(구분선 대체) — 접힐 배경이 있을 때만. */}
          {foldedCards.length > 0 && (
            <SteadyFold cards={foldedCards} expanded={steadyExpanded} onToggle={toggle} />
          )}
        </div>
      )}
    </div>
  );
}
