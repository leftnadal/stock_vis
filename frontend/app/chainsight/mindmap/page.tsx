import { Suspense } from 'react';
import MindmapTreeBoard from '@/components/chainsight/MindmapTreeBoard';

// CS-P5-FE-CARD B3+B4 — 업종 2단(sector→industry) 마인드맵 + 카드 상세.
// 신규 라우트(additive). useSearchParams(?symbol=) 사용 → Suspense 경계 필요.
export default function ChainSightMindmapPage() {
  return (
    <Suspense fallback={null}>
      <MindmapTreeBoard />
    </Suspense>
  );
}
