'use client';

import Link from 'next/link';
import type { MarketStoryCard } from '@/types/chainsight';
import {
  STORY_CARD_BADGE,
  STORY_CARD_LABEL,
  isCoMention,
  newSecRelationLabel,
  recencyLabel,
  storyCardDeepLink,
} from './storyCardConfig';

/**
 * 피드 카드 1장 (R2-S2). 유형별 정직성 규칙 준수:
 * - daily_spike: 절대량(N회)+발생일만. "평소 대비/배수" 문구 절대 금지.
 * - weekly_active: 이번 주 절대량 + 최신성.
 * - new_sec: SEC 8-K item code + filing일 — co_mention과 달리 "관계 아님" 캡션 없음(유일하게 관계 시사 가능).
 */
export default function MarketStoryCardItem({ card }: { card: MarketStoryCard }) {
  const href = storyCardDeepLink(card);
  const coMention = isCoMention(card);

  return (
    <Link
      href={href}
      data-testid="market-story-card"
      data-card-type={card.type}
      className="flex flex-col gap-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 hover:shadow-md hover:border-blue-400 transition-shadow"
    >
      <span
        className={`self-start px-2 py-0.5 rounded text-[11px] font-semibold ${STORY_CARD_BADGE[card.type]}`}
      >
        {STORY_CARD_LABEL[card.type]}
      </span>

      <div className="font-semibold text-sm text-gray-900 dark:text-gray-50">
        {card.symbol_a} ↔ {card.symbol_b}
      </div>

      {card.type === 'daily_spike' && (
        <>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {card.count}회 함께 언급 · {card.occurred_on}
          </p>
          {card.companions.length > 0 && (
            <div className="flex flex-wrap gap-1">
              <span className="text-[11px] text-gray-400">함께:</span>
              {card.companions.map((c) => (
                <span
                  key={c}
                  className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-[11px] text-gray-600 dark:text-gray-300"
                >
                  {c}
                </span>
              ))}
            </div>
          )}
        </>
      )}

      {card.type === 'weekly_active' && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          이번 주 {card.count}회 함께 언급 · 최근 {recencyLabel(card.days_since)}
        </p>
      )}

      {card.type === 'new_sec' && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {newSecRelationLabel(card.relation_type) && (
            <span className="mr-1 font-medium text-gray-700 dark:text-gray-300">
              {newSecRelationLabel(card.relation_type)}
            </span>
          )}
          SEC 8-K item {card.item_code} · {card.occurred_on}
        </p>
      )}

      {coMention && (
        <p className="text-[11px] text-gray-400 dark:text-gray-500">관계 아님 · 동시 언급</p>
      )}
    </Link>
  );
}
