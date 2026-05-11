// API 설정
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

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