'use client';

import { useState } from 'react';
import ThemeHeatBar from '@/components/chainsight/ThemeHeatBar';
import ThemeHeatCard from '@/components/chainsight/ThemeHeatCard';

/** 테마 온도계 v3 (TH-15/16, 결정23B/24C/25③/27/29) — 버튼바 + 선택 카드. */
export default function ThemeHeatPage() {
  const [selected, setSelected] = useState<string | undefined>(undefined);

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-gray-50">테마 온도계</h1>
        <p className="text-xs text-gray-400 mt-1">
          섹터별 과열 온도(0–100). 계산 방식 개선일에는 하루 변화 견인 서사를 보류합니다.
        </p>
      </div>

      <ThemeHeatBar selected={selected} onSelect={setSelected} />

      {selected ? (
        <ThemeHeatCard theme={selected} />
      ) : (
        <p className="text-sm text-gray-400">테마를 선택하면 상세 카드가 표시됩니다.</p>
      )}
    </div>
  );
}
