// 관계망 이벤트 피드 타입 (EVT-CHAIN-1). BE build_chain_feed 응답 ⇄ FE 타입 그대로.
// 부호 중립: relation = {type, truth_score}만 — 방향/센티먼트 필드 없음(BE DTO 계약).
import type { EventItem, EventKind } from '@/types/eventCalendar';

export interface ChainNeighbor {
  symbol: string;
  relation_type: string; // RelationConfidence.relation_type 원문 코드(FE에서 한글 매핑)
  truth_score: number; // 도메인 [0,1] (D-RC-SCALE) — 표시 시 ×100
}

export interface ChainRelation {
  type: string;
  truth_score: number;
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
  seed_next_event: ChainSeedNext | null;
  neighbors: ChainNeighbor[];
  items: ChainEventItem[];
  after_count: number;
  params: Record<string, unknown>;
}
