// D1-SCOREBOARD — 애널리스트 성적판 TanStack Query 훅.
// 전역 read(비용 없음) → useQuery. BE가 나안 TTL 캐시로 재계산 억제.
import { useQuery } from '@tanstack/react-query'

import { scorecardService } from '@/services/scorecardService'

export const scorecardKeys = {
  all: ['analyst-scorecard'] as const,
  board: (h: number) => [...scorecardKeys.all, h] as const,
}

export function useAnalystScorecard(h = 21) {
  return useQuery({
    queryKey: scorecardKeys.board(h),
    queryFn: () => scorecardService.get(h),
  })
}
