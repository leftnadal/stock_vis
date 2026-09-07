// 관계망 타임라인 섹션 (EVT-CHAIN-1 / 1B). 모니터 상세(scope=stock) 하단 附加 전용.
// EVT-CHAIN-1B(P1): 위젯은 상단 밴드(UpcomingEventsBand)로 이동 — 여기는 타임라인만 남긴다.
// 앵커 id(CHAIN_TIMELINE_ANCHOR)로 밴드의 "관계망 ↓" 스크롤 타깃. 이웃 0이면 섹션 비표시.
'use client';

import { useChainFeed } from '@/hooks/useEventCalendar';

import { ChainTimeline } from './ChainTimeline';

export const CHAIN_TIMELINE_ANCHOR = 'chain-timeline';

interface Props {
  symbol: string;
}

export function ChainSection({ symbol }: Props) {
  const { data, isError } = useChainFeed(symbol, true);

  // 附加 전용: 로딩/실패·이웃 0이면 미표시(기존 화면 무변). 위젯은 상단 밴드가 담당.
  if (isError || !data) return null;
  if (data.neighbors.length === 0) return null;

  return (
    <section id={CHAIN_TIMELINE_ANCHOR} data-testid="chain-section" className="mt-6 scroll-mt-4">
      <ChainTimeline feed={data} />
    </section>
  );
}
