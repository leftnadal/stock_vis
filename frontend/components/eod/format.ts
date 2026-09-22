/**
 * eod 표시 포맷 공용 (DASH-RECO 채번후보 (f) 해소).
 *
 * `StockRow.tsx`와 `RecommendationDetailSheet.tsx`에 **문자 단위로 동일한** 구현이
 * 각각 있었다(S0-7 대조 확인). 단순 이동 — 동작 변경 0.
 */

/** 금액 압축 표기. 0 이하·결측은 null → 소비처가 정칙 ⑴로 생략한다. */
export function formatCompactUSD(value: number | null | undefined): string | null {
  if (value == null || value <= 0) return null;
  if (value >= 1_000_000_000_000) return `$${(value / 1_000_000_000_000).toFixed(1)}T`;
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(0)}M`;
  return `$${(value / 1_000).toFixed(0)}K`;
}
