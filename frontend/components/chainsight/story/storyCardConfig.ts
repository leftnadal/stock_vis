/**
 * "오늘 시장의 이야기" 피드 카드 화면 설정 (R2-S2) — 라벨·배지색 단일 소스.
 * (mindmapConfig.ts 패턴 재사용: 매직스트링·매핑을 컴포넌트 밖으로 분리.)
 *
 * 목업 준거 ⑷ 배지 색 계열 구분 — 사건 카드(new_sec·daily_spike)=강조색, weekly_active=중립색.
 * new_sec 은 근거색(SEC 8-K)이되 daily_spike(co-mention 사건)와 구분되는 톤을 쓴다.
 * 색만으로 구분하지 않는다 — 문구(배지 텍스트)를 항상 병기.
 */

import type { MarketStoryCard, MarketStoryCardType } from '@/types/chainsight';
import { relationTypeLabel } from '../mindmapConfig';

/** 카드 유형 → 배지 문구. */
export const STORY_CARD_LABEL: Record<MarketStoryCardType, string> = {
  new_sec: '신규 연결 · 8-K',
  daily_spike: '일간 급등',
  weekly_active: '이번 주 활발',
};

/** 카드 유형 → 배지 톤(bg + text, dark 변형 포함). new_sec=근거(블루) · daily_spike=사건(앰버) · weekly_active=중립(그레이). */
export const STORY_CARD_BADGE: Record<MarketStoryCardType, string> = {
  new_sec: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  daily_spike: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  weekly_active: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
};

/** relation_type → 표시어 (mindmapConfig 재사용 — SEC 4종 라벨 단일 소스). */
export function newSecRelationLabel(relationType: string | undefined): string {
  if (!relationType) return '';
  return relationTypeLabel(relationType);
}

/** 카드 클릭 시 딥링크 대상 — 페어의 symbol_a로 마인드맵 카드 포커스. */
export function storyCardDeepLink(card: MarketStoryCard): string {
  return `/chainsight/mindmap?symbol=${encodeURIComponent(card.symbol_a.toUpperCase())}`;
}

/** 규칙 3(신뢰 위계): co_mention 카드에만 "관계 아님" 캡션 — sec_evidence는 표시 안 함. */
export function isCoMention(card: MarketStoryCard): boolean {
  return card.kind === 'co_mention';
}

/** days_since → 사람이 읽는 최신성 (MindmapCardDetail.recencyLabel과 동일 규약). null이면 빈 문자열. */
export function recencyLabel(daysSince: number | null | undefined): string {
  if (daysSince == null) return '';
  if (daysSince <= 0) return '오늘';
  if (daysSince === 1) return '어제';
  return `${daysSince}일 전`;
}
