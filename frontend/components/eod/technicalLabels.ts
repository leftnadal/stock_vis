// 기술 축 enum → 표시어 (D-SCAN-B2TECH-CONTRACT · 정칙 ⑵).
// BE는 사실 구간 enum만 방출, FE는 이 정적 맵으로 표시어 변환 — 신규 해석·매매 문구 금지.
import type { RsiState, MaState, TechnicalBlock } from '@/types/eod';

export const RSI_STATE_LABEL: Record<RsiState, string> = {
  oversold: '과매도',
  overbought: '과매수',
  neutral: '중립',
};

export const MA_STATE_LABEL: Record<MaState, string> = {
  golden_cross: '골든크로스',
  dead_cross: '데드크로스',
  above: '정배열',
  below: '역배열',
};

/** rsi_state → tailwind 칩 색(상태 서술만·매매 암시 아님). */
export const RSI_STATE_CHIP: Record<RsiState, string> = {
  overbought: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-800',
  oversold: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-900/20 dark:text-sky-300 dark:border-sky-800',
  neutral: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-700/50 dark:text-gray-300 dark:border-gray-600',
};

/** ma_state → 칩 색. 교차 이벤트(golden/dead)만 강조색, 정/역배열은 중립. */
export const MA_STATE_CHIP: Record<MaState, string> = {
  golden_cross: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-800',
  dead_cross: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-900/20 dark:text-rose-300 dark:border-rose-800',
  above: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-700/50 dark:text-gray-300 dark:border-gray-600',
  below: 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-700/50 dark:text-gray-300 dark:border-gray-600',
};

/**
 * 52주 고점 대비 위치(%) → 표시어.
 * value = close/high×100. 표시 = "52주 고점 −x.x%"(100−value). ≥100(신고가 갱신) = "52주 신고가".
 */
export function formatDist52wHigh(pct: number | undefined): string | null {
  if (pct == null) return null;
  if (pct >= 100) return '52주 신고가';
  const below = 100 - pct;
  return `52주 고점 −${below.toFixed(1)}%`;
}

/** RSI 값+상태어 표시("RSI 72 · 과매수"). 값/상태 결측 시 null(정칙 ⑴). */
export function formatRsi(tech: TechnicalBlock | undefined): string | null {
  if (!tech || tech.rsi == null || !tech.rsi_state) return null;
  return `RSI ${tech.rsi} · ${RSI_STATE_LABEL[tech.rsi_state]}`;
}

/** MA 상태 표시어. 결측 시 null. */
export function formatMaState(tech: TechnicalBlock | undefined): string | null {
  if (!tech || !tech.ma_state) return null;
  return MA_STATE_LABEL[tech.ma_state];
}

/**
 * 기술 칸 전체 요약 부품(4값 전체·정칙 ⑴로 present만).
 * 순서 = RSI · 52주 · MA. 전건 결측이면 빈 배열.
 */
export function buildTechnicalDetail(tech: TechnicalBlock | undefined): string[] {
  if (!tech) return [];
  const parts: string[] = [];
  const rsi = formatRsi(tech);
  if (rsi) parts.push(rsi);
  const dist = formatDist52wHigh(tech.dist_52w_high_pct);
  if (dist) parts.push(dist);
  const ma = formatMaState(tech);
  if (ma) parts.push(ma);
  return parts;
}
