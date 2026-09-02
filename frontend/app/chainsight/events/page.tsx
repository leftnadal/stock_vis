import EventBoard from '@/components/chainsight/EventBoard';

// R2-S2 역전(2026-09-02): 루트(/chainsight)가 "오늘 시장의 이야기" 피드로 교체됨에 따라
// 이벤트 보드는 이 라우트로 강등 이동(원클릭 접근 유지). EventGroup 조감은 S2 후속.
export default function ChainSightEventsPage() {
  return <EventBoard />;
}
