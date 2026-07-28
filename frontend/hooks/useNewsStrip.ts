// 뉴스 스트립 훅 — staleTime 30분(useNews 관례, 서버 15분 TTL과 짝). [D-NEWSAXIS-CONTRACT ⑷]
import { useQuery } from '@tanstack/react-query';

import { stripService, type NewsStripResponse } from '@/services/stripService';

export function useNewsStrip() {
  return useQuery<NewsStripResponse>({
    queryKey: ['news-strip'],
    queryFn: () => stripService.getNewsStrip(),
    staleTime: 1000 * 60 * 30, // 30분
    retry: 1,
  });
}
