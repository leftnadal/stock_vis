// Advisory(권유) 읽기 화면 API 클라이언트 (Slice 20a)
// authAxios baseURL에 이미 /api/v1 포함 → 경로에 중복 금지 (common-bug #19)
import { authAxios } from '@/lib/api/authAxios'
import type {
  AssetSummary,
  GoalCreateInput,
  KnobsRead,
  KnobsUpdateInput,
  LatestAdvisory,
} from '@/types/advisory'

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
  // 목표 생성(SLICE20BF2, POST). 이미 있으면 서버 409(생성 단일 경로, D-f2-1).
  createGoal: async (input: GoalCreateInput): Promise<KnobsRead> => {
    const { data } = await authAxios.post('/advisory/knobs/', input)
    return data
  },
  // 손잡이 5종 + 목표 수익률 저장(SLICE20B). 저장 ≠ 진단 실행(D2) — 진단은 run() 별도.
  updateKnobs: async (input: KnobsUpdateInput): Promise<KnobsRead> => {
    const { data } = await authAxios.patch('/advisory/knobs/', input)
    return data
  },
  run: async (): Promise<LatestAdvisory> => {
    const { data } = await authAxios.post('/advisory/run/')
    return data
  },
}
