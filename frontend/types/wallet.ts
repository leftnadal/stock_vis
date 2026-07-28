// 지갑(보유·현금) 타입 — apps/portfolio/api/wallet.py 봉투 1:1 미러.
// ★ 값 규약: 금액·수량·가격은 전부 string(백엔드 Decimal 직렬화). 통화는 stock 파생.

export type Currency = 'USD' | 'KRW'

export interface Holding {
  id: string
  symbol: string
  name: string
  currency: string
  shares: string
  avg_cost: string
  first_bought_at: string | null
  acquisition_fx_rate: string | null
  investment_thesis: string
  current_price: string
}

export interface HoldingCreateInput {
  symbol: string
  shares: string
  avg_cost: string
  first_bought_at: string
  investment_thesis?: string
  acquisition_fx_rate?: string | null
}

export interface HoldingUpdateInput {
  shares?: string
  avg_cost?: string
  first_bought_at?: string
  investment_thesis?: string
  acquisition_fx_rate?: string | null
}

export interface CashBalance {
  currency: Currency
  amount: string
}

// GET 응답 봉투
export interface HoldingsResponse {
  holdings: Holding[]
}

export interface CashResponse {
  cash: CashBalance[]
}
