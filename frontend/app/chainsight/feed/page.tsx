import MarketStoryFeed from '@/components/chainsight/story/MarketStoryFeed';

// R2-S2 — "오늘 시장의 이야기" 피드 전용 라우트. 루트(/chainsight)도 동일 컴포넌트를 렌더한다
// (랜딩 교체) — 이 라우트는 명시적 딥링크·재사용 진입점으로 유지.
export default function ChainSightFeedPage() {
  return <MarketStoryFeed />;
}
