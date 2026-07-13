// 크레딧 매크로 스트립 — 홈 상단(MarketSummaryBar–NewsStrip 사이). CS-CREDIT-CONSUME + 의미 2층.
// credit_signal_state 6종 = grade 칩 가로 나열 + 헤드라인 한 줄(규칙 자동문장) + 하단 리드아웃(칩 hover/탭).
// NewsStrip 실패 격리 동형: API 실패/빈 응답 → 비표시(null). 리드아웃은 overflow 밖(수평스크롤 클리핑 회피).
'use client';

import { useState } from 'react';

import { GRADE_DOT_HEX } from '@/components/common/colorSemantics';
import { GradeChip } from '@/components/strip/GradeChip';
import { useCreditSignals } from '@/hooks/useCreditSignals';
import {
  GRADE_SEVERITY,
  buildChipInfo,
  deriveHeadline,
} from '@/lib/credit/creditMeaning';
import type { CreditSignal } from '@/services/creditSignalsService';

function zLabel(z: number | null): string {
  if (z === null) return 'z —';
  return `z ${z >= 0 ? '+' : ''}${z.toFixed(2)}`;
}

export function MacroStrip() {
  const { data, isError } = useCreditSignals();
  const [activeKey, setActiveKey] = useState<string | null>(null);

  // 실패 격리: 에러·빈 응답·미도착 → 비표시.
  if (isError || !data || data.signals.length === 0) {
    return null;
  }

  const headline = deriveHeadline(data.signals);
  const headlineDot = GRADE_DOT_HEX[headline.grade] ?? GRADE_DOT_HEX.gray;
  const headlineMuted = headline.grade === 'gray'; // 전부 gray → 저채도 눌림.

  // 심각도 정렬(red>orange>yellow>gray, 동급은 API 순서 유지 = stable sort). 비-gray가
  // 항상 좌측 → 가로 스크롤 밖 잠복 방지. 칩 폭·컨테이너 계약은 무변경(정렬만).
  const sortedSignals = [...data.signals].sort(
    (a, b) => GRADE_SEVERITY[b.grade] - GRADE_SEVERITY[a.grade],
  );
  // 리드아웃 기본 = 최고 심각도 신호(헤드라인 대상), hover/포커스로 갱신.
  const mostSevere = sortedSignals[0];
  const active: CreditSignal =
    data.signals.find((s) => s.key === activeKey) ?? mostSevere;
  const info = buildChipInfo(active);

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

      {/* 칩 (hover/탭 → 하단 리드아웃 갱신) */}
      <div
        role="list"
        className="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-1"
      >
        {sortedSignals.map((s) => (
          <GradeChip
            key={s.key}
            grade={s.grade}
            label={s.name}
            value={s.value.toFixed(2)}
            sub={zLabel(s.z)}
            spark={s.spark.map((p) => p.value)}
            active={active.key === s.key}
            onActivate={() => setActiveKey(s.key)}
          />
        ))}
      </div>

      {/* 의미 2층: 리드아웃 (overflow 밖 — 정의·현재상태·밴드) */}
      <div
        data-testid="macro-readout"
        className="mt-1.5 rounded-md border border-gray-100 bg-gray-50/60 px-2.5 py-1.5 text-[11px] leading-snug dark:border-gray-700 dark:bg-gray-800/40"
      >
        <span className="font-medium text-gray-900 dark:text-gray-100">
          {active.name}
        </span>
        <span className="text-gray-600 dark:text-gray-300"> — {info.def}</span>
        <span className="mt-0.5 block tabular-nums text-gray-800 dark:text-gray-200">
          {info.state}
        </span>
        <span className="mt-0.5 block text-[10px] text-gray-400 dark:text-gray-500">
          밴드 {info.band}
        </span>
      </div>
    </section>
  );
}
