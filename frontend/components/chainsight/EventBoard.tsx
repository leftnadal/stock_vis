'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Tag, Share2 } from 'lucide-react';
import { getLabelForTheme } from '@/constants/eventThemes';
import { fetchEvents } from '@/services/chainsightService';
import type { EventBoardItem } from '@/types/chainsight';
import { CHANGE_TEXT } from '@/components/common/colorSemantics';
import { formatMemberTitle } from './eventBoardTitle';

// Dynamic icon rendering using lucide-react
// We import dynamically to avoid bundling all icons; fallback to Tag on miss
async function loadIcon(iconName: string): Promise<React.ComponentType<{ size?: number; className?: string }> | null> {
  try {
    const mod = await import('lucide-react') as Record<string, unknown>;
    const Icon = mod[iconName];
    if (typeof Icon === 'function') {
      return Icon as React.ComponentType<{ size?: number; className?: string }>;
    }
    return null;
  } catch {
    return null;
  }
}

// Synchronous icon lookup via static import of the full barrel
// lucide-react is already in the bundle; we cast the namespace
import * as LucideIcons from 'lucide-react';

function ThemeIcon({ iconName, className }: { iconName: string; className?: string }) {
  const icons = LucideIcons as unknown as Record<string, React.ComponentType<{ size?: number; className?: string }>>;
  const IconComponent = icons[iconName];
  if (!IconComponent) {
    return <Tag size={20} className={className} />;
  }
  return <IconComponent size={20} className={className} />;
}

// Keep loadIcon defined to avoid lint errors (used internally)
void loadIcon;

function EventCard({ item, onClick }: { item: EventBoardItem; onClick: () => void }) {
  // ON(event_group): item.name(n3)을 라벨로, 아이콘은 폴백(Tag) 유지.
  // OFF(theme_tags): name 없음 → getLabelForTheme(섹터명) 그대로(IDENTICAL).
  const base = getLabelForTheme(item.theme);
  const label = item.name ? { ...base, ko: item.name } : base;
  const isPositive = item.avg_return >= 0;
  // ⑳-2 S4: 구성 티커 대문자 병기를 주표기로, 기존 키워드 라벨은 부제로 강등.
  const tickerTitle = formatMemberTitle(item.members);

  return (
    <button
      onClick={onClick}
      className="flex flex-col gap-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-left hover:shadow-md transition-shadow cursor-pointer w-full"
      aria-label={`${label.ko} 이벤트 보드`}
    >
      <div className="flex items-center gap-2">
        <ThemeIcon iconName={label.icon} className="text-blue-500 shrink-0" />
        <div className="min-w-0">
          {/* ⑳-G S4 주표기: 구성 티커 병기(있을 때) — 주표기 강조 강화(bold·base). */}
          <span className="block font-bold text-base text-gray-900 dark:text-gray-50 truncate">
            {tickerTitle || label.ko}
          </span>
          {/* 부제: 기존 키워드 라벨(티커 병기가 있을 때만 강등 표기) — 대비 강화(약화). */}
          {tickerTitle && (
            <span className="block text-[11px] text-gray-400 dark:text-gray-500 truncate">
              {label.ko}
            </span>
          )}
        </div>
      </div>
      {/* ⑳-G S4: 등락률 = 카드 최상위 강조(크기·굵기 상향). */}
      <div className={`text-2xl font-extrabold tabular-nums ${isPositive ? CHANGE_TEXT.up : CHANGE_TEXT.down}`}>
        {isPositive ? '▲' : '▼'} {Math.abs(item.avg_return * 100).toFixed(2)}%
      </div>
      {/* ⑳-G S4: 관심도·종목수 = 보조 정보로 시각 강등(크기·명도 하향). */}
      <div className="text-[11px] text-gray-400 dark:text-gray-500">관심도 {item.avg_score.toFixed(1)}</div>
      <div className="flex flex-wrap gap-2 text-[11px]">
        <span className="text-gray-400 dark:text-gray-500">{item.member_count}개 종목</span>
        <span
          className="text-blue-500/80 font-medium cursor-help"
          title={`관심 집중 종목 ${item.high_attention_count}개 — 그룹에서 관심도 70점 이상 (전체 ${item.member_count}개 중)`}
        >
          관심↑ {item.high_attention_count}
        </span>
        {/* ⓐ 저신뢰 표식: 멤버<3(=quorum 미달)이면 그룹 상대지표 통계 근거 약함 → 숨기지 않고 신호 */}
        {item.member_count < 3 && (
          <span
            className="text-amber-600 dark:text-amber-400 font-medium cursor-help"
            title={`표본 작음 — 멤버 ${item.member_count}개(3개 미만). 그룹 상대지표(민감도·주도우위)는 통계 근거가 약해 상세에서 "—"로 표시됩니다`}
          >
            표본 작음
          </span>
        )}
      </div>
    </button>
  );
}

export default function EventBoard() {
  const router = useRouter();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['chainsight', 'events'],
    queryFn: fetchEvents,
    staleTime: 1000 * 60 * 5,
  });

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">로딩 중...</div>;
  }

  if (isError || !data) {
    return <div className="p-8 text-center text-red-500">데이터를 불러올 수 없습니다</div>;
  }

  if (data.length === 0) {
    return <div className="p-8 text-center text-gray-500">이벤트 데이터가 없습니다</div>;
  }

  const sorted = [...data].sort((a, b) => b.avg_score - a.avg_score);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">이벤트 보드</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">관심 종목 그룹 동향</p>
        </div>
        {/* A-1: 강등 이동된 관계 그래프 진입점 (보드 = Chain Sight 홈) */}
        <Link
          href="/chainsight/market-graph"
          className="shrink-0 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          <Share2 size={16} />
          전체 관계 그래프 보기
        </Link>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {sorted.map((item) => (
          <EventCard
            key={item.theme}
            item={item}
            onClick={() => router.push(`/chainsight/events/${encodeURIComponent(item.theme)}`)}
          />
        ))}
      </div>
    </div>
  );
}
