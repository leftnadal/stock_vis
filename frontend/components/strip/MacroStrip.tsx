// 크레딧 매크로 스트립 — 홈 상단(MarketSummaryBar–NewsStrip 사이). CS-CREDIT-CONSUME + 의미 2층.
// credit_signal_state 6종을 grade 칩으로 가로 나열 + 헤드라인 한 줄(규칙 기반 자동 문장) + 칩 툴팁.
// NewsStrip 실패 격리 패턴 동형: API 실패/빈 응답 → 스트립 자체 비표시(null), 홈 나머지 무영향.
'use client';

import { GRADE_DOT_HEX } from '@/components/common/colorSemantics';
import { GradeChip } from '@/components/strip/GradeChip';
import { useCreditSignals } from '@/hooks/useCreditSignals';
import { buildChipInfo, deriveHeadline } from '@/lib/credit/creditMeaning';

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

  const headline = deriveHeadline(data.signals);
  const headlineDot = GRADE_DOT_HEX[headline.grade] ?? GRADE_DOT_HEX.gray;
  // 전부 gray(안정) → 저채도 눌림.
  const headlineMuted = headline.grade === 'gray';

  return (
    <section aria-label="크레딧 매크로" className="w-full">
      {/* 의미 1층: 헤드라인 한 줄 (최악 grade 톤·dot) */}
      <div
        data-testid="macro-headline"
        className={`mb-1.5 flex items-center gap-1.5 text-xs font-medium ${
          headlineMuted
            ? 'text-gray-400 dark:text-gray-500'
            : 'text-gray-700 dark:text-gray-200'
        }`}
      >
        <span
          data-testid="macro-headline-dot"
          className="inline-block h-2 w-2 rounded-full"
          style={{ backgroundColor: headlineDot }}
        />
        <span>{headline.text}</span>
      </div>

      {/* 의미 2층: 칩(hover/탭 툴팁) */}
      <div
        role="list"
        className="flex gap-3 overflow-x-auto overflow-y-visible snap-x snap-mandatory pb-1"
      >
        {data.signals.map((s) => (
          <GradeChip
            key={s.key}
            grade={s.grade}
            label={s.name}
            value={s.value.toFixed(2)}
            sub={zLabel(s.z)}
            spark={s.spark.map((p) => p.value)}
            info={buildChipInfo(s)}
          />
        ))}
      </div>
    </section>
  );
}
