/**
 * RC-C-1 backbone 뷰 타입 (활성 해자 부분그래프 중심성 + θ 엣지).
 * BE: GET /api/v1/chainsight/backbone/ (compute-on-read, D-RC-C1-STORAGE 옵션 C).
 */

export interface BackboneSymbol {
  symbol: string;
  pagerank: number;
  degree: number;
}

export interface BackboneEdge {
  symbol_a: string;
  symbol_b: string;
  score: number;          // = max(truth_score, market_score)
  category: string;       // truth | market
  evidence_count: number; // evidence_count_total
  observed_count: number; // evidence_streak (연속 재확인)
  trust: string;          // relation_status (confirmed | probable)
}

export interface BackboneResponse {
  as_of: string;
  computed_at: string;
  graph_size: { nodes: number; edges: number };
  theta: number;          // θ = score_scale.GRADE_CONFIRMED_MIN (0.85)
  top_symbols: BackboneSymbol[];
  edges: BackboneEdge[];
}
