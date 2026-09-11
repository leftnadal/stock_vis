'use client';

import type { ReactNode } from 'react';

/** 대시보드 상단 탭 (DASH-TAB). 기본 = discover. */
export type DashTab = 'discover' | 'market';

interface DashboardTabsProps {
  activeTab: DashTab;
  onTabChange: (tab: DashTab) => void;
  /** 우측 슬롯 — 현재는 DataFreshnessBadge를 그대로 넣는다(S2 전환은 슬라이스 2). */
  children?: ReactNode;
}

const TABS: { id: DashTab; label: string }[] = [
  { id: 'discover', label: '발견' },
  { id: 'market', label: '시장' },
];

/**
 * [발견][시장] 탭 줄 + 우측 슬롯(children).
 * 섹션 이동/분배는 소비처(app/page.tsx)가 activeTab으로 조건 렌더한다 —
 * 이 컴포넌트는 탭 UI와 슬롯 배치만 담당(무상태·URL 미접촉).
 */
export function DashboardTabs({ activeTab, onTabChange, children }: DashboardTabsProps) {
  return (
    <div
      data-guide="dashboard.tabs"
      className="mb-4 flex items-center justify-between gap-3"
    >
      <div className="flex items-center gap-2" role="tablist" aria-label="대시보드 탭">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => onTabChange(tab.id)}
              className={`
                flex-shrink-0 inline-flex items-center px-4 py-1.5 rounded-full text-sm font-semibold
                transition-all duration-150
                ${isActive
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                }
              `}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {children != null && (
        <div className="min-w-0 flex-shrink">{children}</div>
      )}
    </div>
  );
}
