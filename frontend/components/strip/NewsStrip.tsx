// 뉴스 스트립(S1) — 홈 상단 압축 스트립(3~5칩, 캐러셀 위). [D-NEWS-AXIS 표면 S1]
// 실패 격리: API 실패/빈 응답 → 스트립 자체 비표시(null), 홈 나머지 무영향.
'use client';

import { NewsChip } from '@/components/strip/NewsChip';
import { useNewsStrip } from '@/hooks/useNewsStrip';

export function NewsStrip() {
  const { data, isError } = useNewsStrip();

  // 실패 격리: 에러·빈 응답·미도착 → 비표시.
  if (isError || !data || data.items.length === 0) {
    return null;
  }

  return (
    <section aria-label="뉴스 축" className="w-full">
      <div
        role="list"
        className="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-1"
      >
        {data.items.map((item) => (
          <NewsChip key={`${item.tier}-${item.article_url}`} item={item} />
        ))}
      </div>
    </section>
  );
}
