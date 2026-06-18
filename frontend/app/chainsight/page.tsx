import EventBoard from '@/components/chainsight/EventBoard';

// RD3 첫 화면 정보 구조 역전(2026-06-18): 루트 = 이벤트 보드.
// 기존 마켓 그래프 화면은 /chainsight/market-graph로 강등 이동.
export default function ChainSightPage() {
  return <EventBoard />;
}
