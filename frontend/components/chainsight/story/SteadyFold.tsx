'use client';

import type { MarketStoryCard } from '@/types/chainsight';

/**
 * D-S3-7 배경 접기 — weekly_active(steady)의 접힘 줄 + 펼친 줄 목록.
 *
 * 접힘: 줄 1개 "이번 주 꾸준한 흐름 {m}쌍 · 펼치기 ▸"(구분선 대체).
 * 펼침: 카드 반복 금지 → 조밀한 줄 목록 [종목쌍] [언급 수] [마지막 날짜].
 *       한 줄 높이 ≤ 카드의 1/3, 칩·캡션·근거 수 없음(펼쳐도 카드 28장이면 무의미).
 * 펼침 상태는 저장하지 않는다(부모가 useState로 관리·매일 접힌 채 열림).
 */
export default function SteadyFold({
  cards,
  expanded,
  onToggle,
}: {
  cards: MarketStoryCard[];
  expanded: boolean;
  onToggle: () => void;
}) {
  const m = cards.length;
  return (
    <div className="col-span-full" data-testid="steady-fold">
      <button
        type="button"
        onClick={onToggle}
        data-testid="steady-fold-toggle"
        aria-expanded={expanded}
        className="w-full flex items-center gap-3 py-1.5 text-[12px] text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
      >
        <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
        <span className="whitespace-nowrap">
          이번 주 꾸준한 흐름 {m}쌍 · {expanded ? '접기 ▾' : '펼치기 ▸'}
        </span>
        <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
      </button>

      {expanded && (
        <ul
          data-testid="steady-line-list"
          className="mt-1 divide-y divide-gray-100 dark:divide-gray-800"
        >
          {cards.map((c) => (
            <li
              key={c.story_id ?? `${c.symbol_a}-${c.symbol_b}`}
              data-testid="steady-line"
              className="flex items-center gap-3 py-1 text-[12px] text-gray-600 dark:text-gray-300"
            >
              <span className="font-medium min-w-0 flex-1 truncate">
                {c.symbol_a} · {c.symbol_b}
              </span>
              <span className="tabular-nums text-gray-500 dark:text-gray-400">{c.count}회</span>
              <span className="text-gray-400 dark:text-gray-500 tabular-nums">{c.occurred_on}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
