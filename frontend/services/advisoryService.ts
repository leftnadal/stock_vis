// Advisory(권유) 읽기 화면 API 클라이언트 (Slice 20a)
// authAxios baseURL에 이미 /api/v1 포함 → 경로에 중복 금지 (common-bug #19)
import { authAxios } from '@/lib/api/authAxios'
import type { AssetSummary, KnobsRead, LatestAdvisory } from '@/types/advisory'

export const advisoryService = {
  getLatest: async (): Promise<LatestAdvisory> => {
    const { data } = await authAxios.get('/advisory/latest/')
    return data
  },
  getSummary: async (): Promise<AssetSummary> => {
    const { data } = await authAxios.get('/advisory/summary/')
    return data
  },
  getKnobs: async (): Promise<KnobsRead> => {
    const { data } = await authAxios.get('/advisory/knobs/')
    return data
  },
  run: async (): Promise<LatestAdvisory> => {
    const { data } = await authAxios.post('/advisory/run/')
    return data
  },
}
