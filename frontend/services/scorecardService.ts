// D1-SCOREBOARD — 애널리스트 성적판 API 클라이언트 (전역 read).
// authAxios baseURL에 이미 /api/v1 포함 → 경로 중복 금지 (common-bug #19).
import { authAxios } from '@/lib/api/authAxios'
import type { AnalystScorecard } from '@/types/scorecard'

export const scorecardService = {
  // GET /api/v1/coach/analyst-scorecard/?h= (기본 21거래일 지평).
  get: async (h = 21): Promise<AnalystScorecard> => {
    const { data } = await authAxios.get('/coach/analyst-scorecard/', { params: { h } })
    return data
  },
}
