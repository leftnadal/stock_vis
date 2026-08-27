// DSS-QUADRANT 섹터 사분면 타입 (QUAD-IMPL-1 Slice 2)
// 백엔드 계약: GET /api/v1/chainsight/theme-heat/quadrant/

export interface QuadrantSector {
  sector: string;
  heat: number | null; // null = 미산출 → 차트 밖 하단 목록
  heat_date: string | null;
  breadth_curr: number | null;
  breadth_prev: number | null;
  denom_curr: number | null;
  denom_prev: number | null;
  anchor_curr: string | null;
  anchor_prev: string | null;
  arrow_suppressed: boolean;
}

export interface QuadrantResponse {
  heat_date: string | null;
  anchor_curr: string | null;
  anchor_prev: string | null;
  arrow_suppressed: boolean; // 전 섹터 공통(anchor flat_ratio ≥ 90%)
  flat_ratio_curr: number | null;
  flat_ratio_prev: number | null;
  sectors: QuadrantSector[];
}
