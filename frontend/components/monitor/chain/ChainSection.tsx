// 관계망 섹션 컴포저 (EVT-CHAIN-1). 모니터 상세(scope=stock)에 附加 전용.
// 훅을 이 컴포넌트가 품어 page.tsx 삽입을 최소화(import 1 + 조건부 1줄). 로딩·빈 데이터엔
// 아무것도 그리지 않아 기존 DOM 무변(附加 전용 규율).
'use client';

import { useChainFeed } from '@/hooks/useEventCalendar';

import { ChainTimeline } from './ChainTimeline';
import { UpcomingEventsWidget } from './UpcomingEventsWidget';

interface Props {
  symbol: string;
}

export function ChainSection({ symbol }: Props) {
  const { data, isError } = useChainFeed(symbol, true);

  // 附加 전용: 로딩/실패 시 미표시(기존 화면 무변). 이웃 0이면 ChainTimeline이 null 반환.
  if (isError || !data) return null;

  const hasWidget = data.seed_events.length > 0;
  const hasTimeline = data.neighbors.length > 0;
  if (!hasWidget && !hasTimeline) return null;

  return (
    <section data-testid="chain-section" className="mt-6">
      <UpcomingEventsWidget seedEvents={data.seed_events} />
      <ChainTimeline feed={data} />
    </section>
  );
}
