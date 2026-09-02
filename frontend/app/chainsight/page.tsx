import MarketStoryFeed from '@/components/chainsight/story/MarketStoryFeed';

// R2-S2 랜딩 역전(2026-09-02): 루트 = "오늘 시장의 이야기" 피드.
// 기존 이벤트 보드는 /chainsight/events로 강등 이동(원클릭 접근 유지, 규칙 7).
// (RD3 2026-06-18 역전의 후속 — 이번엔 이벤트 보드 → 피드로 재교체.)
export default function ChainSightPage() {
  return <MarketStoryFeed />;
}
