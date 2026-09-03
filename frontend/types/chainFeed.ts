// 관계망 이벤트 피드 타입 (EVT-CHAIN-1). BE build_chain_feed 응답 ⇄ FE 타입 그대로.
// 부호 중립: relation = {type, truth_score}만 — 방향/센티먼트 필드 없음(BE DTO 계약).
import type { EventItem, EventKind } from '@/types/eventCalendar';

// CHAIN-1a: 방향성 유형의 시드 기준 역할(부호 중립 = 판단 아님, 관계 역할 라벨).
export type ChainRole = 'supplier' | 'customer' | 'dependency' | 'dependent';

export interface ChainNeighbor {
  symbol: string;
  relation_type: string; // RelationConfidence.relation_type 원문 코드(FE에서 한글 매핑)
  truth_score: number; // 도메인 [0,1] (D-RC-SCALE) — 표시 시 ×100
  role: ChainRole | null; // 방향성 유형(SUPPLIES_TO/DEPENDS_ON)만·나머지 null
}

export interface ChainRelation {
  type: string;
  truth_score: number;
  role: ChainRole | null;
}

// items = 이웃 어닝(EventItem) + relation 확장. 부호 중립 — direction/sentiment 없음.
export interface ChainEventItem extends EventItem {
  relation: ChainRelation | null;
}

export interface ChainSeedNext {
  kind: EventKind;
  event_date_et: string; // YYYY-MM-DD
  d_day: number;
}

export interface ChainFeed {
  seed: string;
  as_of: string;
  seed_events: EventItem[]; // 시드 자신의 다가오는 어닝/배당(위젯 pill)
  seed_next_event: ChainSeedNext | null; // 배너 = 다음 이벤트(유형 무관)
  seed_earnings_event: ChainSeedNext | null; // 시드 행 + 창 종점(다음 어닝)
  window_end: string | null; // YYYY-MM-DD — 창 종점(시드 다음 어닝, 없으면 오늘+90)
  neighbors: ChainNeighbor[];
  items: ChainEventItem[];
  after_count: number;
  params: Record<string, unknown>;
}
