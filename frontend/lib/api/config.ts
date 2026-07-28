// API 설정 — 앱 API base 단일 소스 (#55, FE-DEAD-8000-SWEEP)
//
// 절대 base 규약: 모든 앱 API 호출은 NEXT_PUBLIC_API_URL(절대 URL, /api/v1 포함)을 base로 쓴다.
// 죽은 포트 하드코딩 폴백은 금지 — env 미설정은 조용히 잘못된 곳으로 보내는 대신
// 즉시 fail-fast로 드러낸다(빌드/기동 시점).
export function resolveApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    throw new Error(
      'NEXT_PUBLIC_API_URL 미설정 — 앱 API base(절대 URL)는 필수입니다(#55, FE-DEAD-8000-SWEEP). ' +
        '.env(.local)에 NEXT_PUBLIC_API_URL(예: http://localhost:18765/api/v1)을 설정하세요. ' +
        '죽은 포트 하드코딩 폴백은 제거되었습니다.'
    );
  }
  return base.replace(/\/+$/, '');
}

export const API_BASE_URL: string = resolveApiBase();

export const API_ENDPOINTS = {
  // 주식 목록 및 검색
  stocks: {
    list: '/stocks/api/mvp/stocks/',
    search: '/stocks/search/',
    sectors: '/stocks/api/mvp/sectors/',
  },

  // 개별 주식 데이터
  stock: (symbol: string) => ({
    overview: `/stocks/api/overview/${symbol}/`,
    chart: `/stocks/api/chart/${symbol}/`,
    balanceSheet: `/stocks/api/balance-sheet/${symbol}/`,
    incomeStatement: `/stocks/api/income-statement/${symbol}/`,
    cashFlow: `/stocks/api/cashflow/${symbol}/`,
    mvpDetail: `/stocks/api/mvp/stock/${symbol}/`,
    ragContext: `/stocks/api/mvp/rag/${symbol}/`,
  }),
};

// 차트 기간 옵션
export const CHART_PERIODS = {
  '1D': '1d',
  '5D': '5d',
  '1M': '1m',
  '3M': '3m',
  '6M': '6m',
  '1Y': '1y',
  '2Y': '2y',
  '5Y': '5y',
  'MAX': 'max',
} as const;

export const CHART_TYPES = {
  DAILY: 'daily',
  WEEKLY: 'weekly',
} as const;