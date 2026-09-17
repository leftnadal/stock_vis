import { useQueries } from '@tanstack/react-query';
import { useMemo } from 'react';
import { eodService } from '@/services/eodService';
import type { SignalCardDetail } from '@/types/eod';
import { buildConfluenceMap, buildStockIndex, type ConfluenceMap, type StockIndex } from './confluence';

/**
 * 전 카드 JSON을 로드해 합류 지도를 만든다 (SCAN-B1-FE).
 * - queryKey = useSignalDetail과 **동일**(['eod-signal-detail', id]) → 캐시 공유:
 *   시트가 이미 연 카드는 재요청 없음, 지도 로드분이 시트 프리캐시로 이중 역할.
 * - staleTime Infinity(정적 파일) · 비차단: 로딩 중 map=undefined → 소비처가 정칙 ⑴로 칩 생략.
 * - 비용(STEP 0.5 실측): 13카드 raw 1.6MB / gzip ≈ 269KB, 세션 1회 캐시.
 */
export function useConfluenceMap(cardIds: string[], enabled = true) {
  const results = useQueries({
    queries: cardIds.map((id) => ({
      queryKey: ['eod-signal-detail', id] as const,
      queryFn: () => eodService.getSignalDetail(id),
      staleTime: Infinity,
      enabled: enabled && !!id,
    })),
  });

  const allSuccess = results.length > 0 && results.every((r) => r.isSuccess);
  // 안정 dep: 로드 완료 여부 + 각 카드 갱신 스탬프
  const stamp = results.map((r) => r.dataUpdatedAt).join(',');

  const built = useMemo((): { map: ConfluenceMap; stockIndex: StockIndex } | undefined => {
    if (!allSuccess) return undefined;
    const cards = results
      .map((r) => r.data as SignalCardDetail | undefined)
      .filter((c): c is SignalCardDetail => !!c);
    return { map: buildConfluenceMap(cards), stockIndex: buildStockIndex(cards) };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allSuccess, stamp]);

  // stockIndex = 같은 카드 JSON의 symbol→행 사전(추천 체급·섹터·기술 조인용, 추가 요청 0).
  return { map: built?.map, stockIndex: built?.stockIndex, isLoading: results.some((r) => r.isLoading) };
}
