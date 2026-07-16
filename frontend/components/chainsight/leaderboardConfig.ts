/**
 * 중심성 리더보드 설정 상수 (⑳-1)
 *
 * 컬럼 정의·표시 지표·limit을 코드 수정 없이 튜닝 가능하도록 분리(디렉터 지정).
 * UI 용어 규약: "테마" 금지 — "관계망 / 중심성 / 관련 종목" 계열 사용.
 */

import type { CentralityLeaderboardItem } from '@/types/chainsight';

/** 상위 몇 종목을 보일지 */
export const LEADERBOARD_LIMIT = 20;

export interface MetricOption {
  /** API metric 파라미터 값 */
  key: string;
  /** 드롭다운·컬럼 헤더 라벨 */
  label: string;
  /** 지표값 셀 포매터 */
  format: (item: CentralityLeaderboardItem) => string;
}

/** 표시 지표 목록(드롭다운). 실측 API 지표 = pagerank / betweenness */
export const LEADERBOARD_METRICS: MetricOption[] = [
  {
    key: 'pagerank',
    label: '영향력 (PageRank)',
    format: (i) => i.pagerank.toFixed(4),
  },
  {
    key: 'betweenness',
    label: '매개 (Betweenness)',
    format: (i) => i.betweenness.toFixed(4),
  },
];

export interface ColumnDef {
  key: 'rank' | 'stock' | 'value' | 'delta' | 'link';
  label: string;
  align: 'left' | 'right' | 'center';
}

/** 리더보드 컬럼 정의 */
export const LEADERBOARD_COLUMNS: ColumnDef[] = [
  { key: 'rank', label: '순위', align: 'right' },
  { key: 'stock', label: '종목', align: 'left' },
  { key: 'value', label: '중심성', align: 'right' },
  { key: 'delta', label: '전일 대비', align: 'center' },
  { key: 'link', label: '관계망', align: 'center' },
];

/**
 * ego(관계망) 화면 진입 URL 생성 공식.
 * ego 화면 = market-graph(PG 네이티브 Neighbor 모드), `?focus=` 로 중심 종목 지정.
 * (Deep Dive `/chainsight/[symbol]` 는 D-A2-DEEPDIVE로 폐기 대상 → 미사용.)
 */
export const egoUrlForSymbol = (symbol: string): string =>
  `/chainsight/market-graph?focus=${encodeURIComponent(symbol.toUpperCase())}`;

export const metricByKey = (key: string): MetricOption =>
  LEADERBOARD_METRICS.find((m) => m.key === key) ?? LEADERBOARD_METRICS[0];
