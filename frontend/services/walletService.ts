// 지갑(보유·현금) CRUD API 클라이언트 (Slice 20b)
// authAxios baseURL에 이미 /api/v1 포함 → 경로 중복 금지 (common-bug #19)
// JWT는 authAxios 인터셉터 단일 소스 — raw fetch 금지 (common-bug #26)
import { authAxios } from '@/lib/api/authAxios'
import type {
  CashBalance,
  CashResponse,
  Holding,
  HoldingCreateInput,
  HoldingsResponse,
  HoldingUpdateInput,
} from '@/types/wallet'

export const walletService = {
  // 보유(WalletHolding)
  listHoldings: async (): Promise<Holding[]> => {
    const { data } = await authAxios.get<HoldingsResponse>('/wallet/holdings/')
    return data.holdings
  },
  createHolding: async (input: HoldingCreateInput): Promise<Holding> => {
    const { data } = await authAxios.post<Holding>('/wallet/holdings/', input)
    return data
  },
  updateHolding: async (id: string, input: HoldingUpdateInput): Promise<Holding> => {
    const { data } = await authAxios.patch<Holding>(`/wallet/holdings/${id}/`, input)
    return data
  },
  deleteHolding: async (id: string): Promise<void> => {
    await authAxios.delete(`/wallet/holdings/${id}/`)
  },

  // 현금(CashBalance)
  listCash: async (): Promise<CashBalance[]> => {
    const { data } = await authAxios.get<CashResponse>('/wallet/cash/')
    return data.cash
  },
  upsertCash: async (input: CashBalance): Promise<CashBalance> => {
    const { data } = await authAxios.put<CashBalance>('/wallet/cash/', input)
    return data
  },
  deleteCash: async (currency: string): Promise<void> => {
    await authAxios.delete(`/wallet/cash/?currency=${currency}`)
  },
}
