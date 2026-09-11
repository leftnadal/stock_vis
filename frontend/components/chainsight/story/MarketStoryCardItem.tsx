'use client';

import Link from 'next/link';
import type { MarketStoryCard } from '@/types/chainsight';
import {
  STORY_CARD_BADGE,
  STORY_CARD_LABEL,
  isCoMention,
  membersDisplay,
  newSecRelationLabel,
  recencyLabel,
  storyCardDeepLink,
} from './storyCardConfig';

/**
 * 피드 카드 1장 (R2-S2 + S3-1). 정직성 규칙:
 * - 제목 = 근거 기사 원문 인용(co_mention) 또는 8-K 공시 사실 템플릿(new_sec). LLM 0.
 *   근거 기사가 없으면 제목을 만들지 않고 "근거 기사 없음 · 언급 수만 집계"로 정직 표기.
 * - daily_spike: 묶음(members) + N쌍 · 최대 M회 + 발생일. "평소 대비/배수" 문구 금지.
 * - weekly_active: 이번 주 절대량 + 최신성.
 * - new_sec: SEC 8-K item + filing일 — "관계 아님" 캡션 없음(유일하게 관계 시사).
 * data-story-id = S3-4 리포트 라우트/추적 앵커.
 *
 * 주: 8-K "SEC 원문 보기" 링크(url 있을 때)는 카드 전체가 <Link>라 중첩 anchor(무효 DOM)를
 * 피하기 위해 S3-4 리포트 페이지(카드 비-링크)로 이관. 현행 데이터 primary_doc_url=빈값이라
 * 가시 손실 0(종료 보고 명시).
 */
export default function MarketStoryCardItem({ card }: { card: MarketStoryCard }) {
  const href = storyCardDeepLink(card);
  const coMention = isCoMention(card);
  const companions = card.companions_outside ?? card.companions;
  const evidenceCount = card.evidence?.length ?? 0;

  return (
    <Link
      href={href}
      data-testid="market-story-card"
      data-card-type={card.type}
      data-story-id={card.story_id}
      className="flex flex-col gap-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 hover:shadow-md hover:border-blue-400 transition-shadow"
    >
      <span
        className={`self-start px-2 py-0.5 rounded text-[11px] font-semibold ${STORY_CARD_BADGE[card.type]}`}
      >
        {STORY_CARD_LABEL[card.type]}
      </span>

      {/* 제목(인용/템플릿) 또는 정직 표기 */}
      {card.title ? (
        <div className="font-semibold text-sm text-gray-900 dark:text-gray-50">{card.title}</div>
      ) : (
        coMention && (
          <div className="text-xs italic text-gray-400 dark:text-gray-500">
            근거 기사 없음 · 언급 수만 집계
          </div>
        )
      )}

      {/* 멤버 라인 */}
      <div className="text-sm font-medium text-gray-700 dark:text-gray-200">
        {membersDisplay(card)}
      </div>

      {card.type === 'daily_spike' && (
        <>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {(card.pairs?.length ?? 1)}쌍 · 최대 {card.max_mentions ?? card.count}회 · {card.occurred_on}
            {card.days_since != null && ` (${recencyLabel(card.days_since)})`}
          </p>
          {companions.length > 0 && (
            <div className="flex flex-wrap gap-1">
              <span className="text-[11px] text-gray-400">함께:</span>
              {companions.map((c) => (
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

      {/* B안: 카드가 자기 관측 창을 말함(헤더는 창을 말하지 않음). */}
      {card.window_label && (
        <p className="text-[11px] text-gray-400 dark:text-gray-500">{card.window_label}</p>
      )}

      {evidenceCount > 0 && (
        <p className="text-[11px] text-gray-400 dark:text-gray-500">근거 {evidenceCount}</p>
      )}

      {/* D-S3-8 관계 종류 한 줄(serving_layer 축). 등급 단어 금지. 기록 없음이 가장 조용.
          색은 사건성 배지(amber/blue)와 충돌하지 않게 중립 그레이 2단. */}
      {card.relation_line && (
        <p
          data-testid="relation-line"
          data-recorded={card.relation_recorded ? 'true' : 'false'}
          className={
            card.relation_recorded
              ? 'text-[11px] font-medium text-gray-600 dark:text-gray-300'
              : 'text-[11px] text-gray-400 dark:text-gray-500'
          }
        >
          {card.relation_line}
        </p>
      )}

      {coMention && (
        <p className="text-[11px] text-gray-400 dark:text-gray-500">관계 아님 · 동시 언급</p>
      )}
    </Link>
  );
}
