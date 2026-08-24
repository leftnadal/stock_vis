/**
 * Chain Sight 마인드맵 카테고리 한글 매핑 (R1 Phase C-3)
 *
 * - sector: 13개 정적 표(검수 완료) + "미분류". 매핑 없는 값은 영문 원문 fallback(빈 값 금지).
 * - industry: ~130개 규모 — 자동 번역 금지. 골격(빈 dict)만 두고 사용자 검수 후 채운다.
 *   (화면엔 industry 영문 원문 그대로 표시. 정렬/그룹핑 키는 항상 영문 원본 유지 — 표시만 한글.)
 */

export const SECTOR_LABELS: Record<string, string> = {
  'Basic Materials': '기초소재',
  'Communication Services': '통신서비스',
  'Consumer Cyclical': '경기소비재',
  'Consumer Defensive': '필수소비재',
  'E-Commerce': '이커머스',
  ETF: 'ETF',
  Energy: '에너지',
  'Financial Services': '금융',
  Healthcare: '헬스케어',
  Industrials: '산업재',
  'Real Estate': '부동산',
  Technology: '기술',
  Utilities: '유틸리티',
  미분류: '미분류',
};

/**
 * industry 한글 매핑 골격 — 사용자 검수 후 채움(현재 빈 dict, 자동 번역 금지).
 * 채워지기 전까지 getLabelForIndustry()는 항상 영문 원문 fallback.
 */
export const INDUSTRY_LABELS: Record<string, string> = {};

/** sector 문자열 → 한글 라벨. 미매핑 시 영문 원문 fallback(빈 값 표시 금지). */
export function getLabelForSector(sector: string): string {
  return SECTOR_LABELS[sector] ?? sector;
}

/** industry 문자열 → 한글 라벨(현재 골격 단계 — 항상 영문 원문 fallback). */
export function getLabelForIndustry(industry: string): string {
  return INDUSTRY_LABELS[industry] ?? industry;
}
