// 크레딧 매크로 스트립 — 홈 상단(MarketSummaryBar–NewsStrip 사이). CS-CREDIT-CONSUME.
// credit_signal_state 6종을 grade 칩으로 가로 나열. NewsStrip 실패 격리 패턴 동형:
// API 실패/빈 응답 → 스트립 자체 비표시(null), 홈 나머지 무영향.
'use client';

import { GradeChip } from '@/components/strip/GradeChip';
import { useCreditSignals } from '@/hooks/useCreditSignals';

function zLabel(z: number | null): string {
  if (z === null) return 'z —';
  return `z ${z >= 0 ? '+' : ''}${z.toFixed(2)}`;
}

export function MacroStrip() {
  const { data, isError } = useCreditSignals();

  // 실패 격리: 에러·빈 응답·미도착 → 비표시.
  if (isError || !data || data.signals.length === 0) {
    return null;
  }

  return (
    <section aria-label="크레딧 매크로" className="w-full">
      <div
        role="list"
        className="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-1"
      >
        {data.signals.map((s) => (
          <GradeChip
            key={s.key}
            grade={s.grade}
            label={s.name}
            value={s.value.toFixed(2)}
            sub={zLabel(s.z)}
            spark={s.spark.map((p) => p.value)}
          />
        ))}
      </div>
    </section>
  );
}
