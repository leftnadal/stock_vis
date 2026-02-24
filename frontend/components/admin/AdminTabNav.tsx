'use client';

import {
  LayoutDashboard,
  BarChart3,
  Filter,
  Activity,
  Newspaper,
  Server,
} from 'lucide-react';
import type { AdminTab } from '@/types/admin';

interface AdminTabNavProps {
  activeTab: AdminTab;
  onTabChange: (tab: AdminTab) => void;
}

const tabs: Array<{ id: AdminTab; label: string; icon: React.ReactNode }> = [
  { id: 'overview', label: '개요', icon: <LayoutDashboard className="h-4 w-4" /> },
  { id: 'stocks', label: '주식', icon: <BarChart3 className="h-4 w-4" /> },
  { id: 'screener', label: '스크리너', icon: <Filter className="h-4 w-4" /> },
  { id: 'market-pulse', label: 'Market Pulse', icon: <Activity className="h-4 w-4" /> },
  { id: 'news', label: '뉴스', icon: <Newspaper className="h-4 w-4" /> },
  { id: 'system', label: '시스템', icon: <Server className="h-4 w-4" /> },
];

export default function AdminTabNav({ activeTab, onTabChange }: AdminTabNavProps) {
  return (
    <div className="border-b border-gray-200 dark:border-gray-700">
      <nav className="flex gap-1 overflow-x-auto" aria-label="Admin Tabs">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                isActive
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
